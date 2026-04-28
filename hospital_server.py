import socket
import sys
from utils import *

# Hospital Server is the central router.
# Clients talk to it over TCP; it talks to backend servers over UDP.
# This keeps the client-facing protocol separate from the backend services.


HOSPITAL_FILE = "hospital.txt"


def load_doctor_hashes(filepath: str):
    # Reads doctor hashes from hospital.txt to know which users are doctors.
    doctor_hashes = set()
    lines = read_file_lines(filepath)

    in_doctors_section = False

    for line in lines:
        if not line:
            continue

        if line == "[Doctors]":
            # Only the [Doctors] section is used to decide doctor vs patient access.
            in_doctors_section = True
            continue

        if line == "[Treatments]":
            in_doctors_section = False
            continue

        if in_doctors_section:
            parts = line.split()
            if len(parts) == 2:
                _, doctor_hash = parts
                doctor_hashes.add(doctor_hash)

    return doctor_hashes

def get_doctor_list(filepath: str):
    # Reads doctor names from hospital.txt for the patient lookup command.
    doctors = []
    lines = read_file_lines(filepath)

    in_doctors_section = False

    for line in lines:
        if not line:
            continue

        if line == "[Doctors]":
            in_doctors_section = True
            continue

        if line == "[Treatments]":
            break

        if in_doctors_section:
            parts = line.split()
            if len(parts) == 2:
                doctor_name = parts[0]
                doctors.append(doctor_name)

    return doctors

def determine_role(username_hash: str, doctor_hashes) -> str:
    # Decides if a logged-in user should be treated as a doctor or patient.
    if username_hash in doctor_hashes:
        return "doctor"
    return "patient"

def handle_auth_request(client_message: str, udp_socket: socket.socket):
    # Authentication flow: Client -> Hospital -> Authentication Server -> Hospital -> Client.
    parts = parse_message(client_message)

    if len(parts) != 3 or parts[0] != "AUTH":
        return "AUTH_FAIL"

    username_hash = parts[1]
    password_hash = parts[2]
    hash_suffix = get_hash_suffix(username_hash)

    print(f"Hospital Server received an authentication request from a user with hash suffix {hash_suffix}.")

    # Forward the hashed credentials to Authentication Server over UDP.
    auth_message = create_message("AUTH", username_hash, password_hash)
    send_udp(udp_socket, auth_message, LOCALHOST, AUTH_PORT)

    print("Hospital Server has sent an authentication request to the Authentication Server.")

    auth_response, _ = receive_udp(udp_socket)

    print(f"Hospital server has received the response from the authentication server using UDP over port {HOSPITAL_UDP_PORT}.")

    if auth_response == "AUTH_OK":
        print(f"User with a hash suffix {hash_suffix} has been granted access to the system. Determining the access of the user.")

        # After authentication succeeds, hospital.txt determines the user role.
        doctor_hashes = load_doctor_hashes(HOSPITAL_FILE)
        role = determine_role(username_hash, doctor_hashes)

        if role == "doctor":
            print(f"User with hash suffix {hash_suffix} will be granted doctor access.")
        else:
            print(f"User with hash {hash_suffix} will be granted patient access.")

        return create_message("AUTH_OK", role)

    return "AUTH_FAIL"

def handle_lookup_request(client_message: str, udp_socket: socket.socket):
    # Plain lookup also goes through Appointment Server so the lookup flow stays together there.
    parts = parse_message(client_message)

    if len(parts) != 2 or parts[0] != "LOOKUP":
        return create_message("LOOKUP_RESP", "ERROR")

    user_hash = parts[1]
    hash_suffix = get_hash_suffix(user_hash)

    print(f"Hospital Server received a lookup request from a user with a hash suffix {hash_suffix} over port {HOSPITAL_TCP_PORT}.")

    print("Hospital Server sent the doctor lookup request to the Appointment server.")

    request = create_message("LOOKUP", user_hash)
    send_udp(udp_socket, request, LOCALHOST, APPOINTMENT_PORT)

    response, _ = receive_udp(udp_socket)

    print(f"Hospital Server has received the response from Appointment Server using UDP over port {HOSPITAL_UDP_PORT}.")

    print("Hospital Server has sent the doctor lookup to the client.")

    return response

def handle_lookup_doctor_request(client_message: str, udp_socket: socket.socket):
    # Doctor-specific lookup flow goes through Appointment Server because it owns availability.
    parts = parse_message(client_message)

    if len(parts) != 3 or parts[0] != "LOOKUP_DOCTOR":
        return create_message("LOOKUP_DOCTOR_RESP", "ERROR")

    user_hash = parts[1]
    doctor_name = parts[2]
    hash_suffix = get_hash_suffix(user_hash)

    print(f"Hospital Server has received a lookup request from a user with hash suffix {hash_suffix} to lookup {doctor_name} availability using TCP over port {HOSPITAL_TCP_PORT}.")

    # Specific doctor availability is owned by the Appointment Server.
    request = create_message("LOOKUP_DOCTOR", doctor_name)
    send_udp(udp_socket, request, LOCALHOST, APPOINTMENT_PORT)

    print("Hospital Server sent the doctor lookup request to the Appointment server.")

    response, _ = receive_udp(udp_socket)

    print(f"Hospital Server has received the response from Appointment Server using UDP over port {HOSPITAL_UDP_PORT}.")

    print("The Hospital Server has sent the response to the client.")

    return response

def handle_schedule_request(client_message: str, udp_socket: socket.socket):
    # Schedule flow keeps Hospital as a relay; Appointment Server updates the file.
    parts = parse_message(client_message)

    if len(parts) != 5 or parts[0] != "SCHEDULE":
        return create_message("SCHEDULE_RESP", "ERROR")

    patient_hash = parts[1]
    doctor_name = parts[2]
    time_slot = parts[3]
    illness = parts[4]
    hash_suffix = get_hash_suffix(patient_hash)

    print(f"Hospital Server has received a schedule request from a user with hash suffix: {hash_suffix} to book an appointment using TCP over port {HOSPITAL_TCP_PORT}.")

    # The Appointment Server validates the time slot and updates appointments.txt.
    request = create_message("SCHEDULE", patient_hash, doctor_name, time_slot, illness)
    send_udp(udp_socket, request, LOCALHOST, APPOINTMENT_PORT)

    print("Hospital Server has sent the schedule request to the appointment server.")

    response, _ = receive_udp(udp_socket)

    print(f"Hospital Server has received the response from Appointment Server using UDP over {HOSPITAL_UDP_PORT}.")

    print("The hospital server has sent the response to the client.")

    return response

def handle_view_appointment_request(client_message: str, udp_socket: socket.socket):
    # Forwards a patient's view appointment request to Appointment Server.
    parts = parse_message(client_message)

    if len(parts) != 2 or parts[0] != "VIEW_APPOINTMENT":
        return create_message("VIEW_APPOINTMENT_RESP", "ERROR")

    user_hash = parts[1]
    hash_suffix = get_hash_suffix(user_hash)

    print(f"Hospital server has received a view appointment request from a user with hash suffix {hash_suffix} to view their appointment details using TCP over port {HOSPITAL_TCP_PORT}.")

    request = create_message("VIEW_APPOINTMENT", user_hash)
    send_udp(udp_socket, request, LOCALHOST, APPOINTMENT_PORT)

    print("Hospital Server has sent the view appointments request to the Appointment Server.")

    response, _ = receive_udp(udp_socket)

    print(f"Hospital Server has received the response from the appointment server using UDP over port {HOSPITAL_UDP_PORT}.")

    print("The hospital server has sent the response to the client.")
    return response

def handle_cancel_request(client_message: str, udp_socket: socket.socket):
    # Forwards a patient's cancel request to Appointment Server.
    parts = parse_message(client_message)

    if len(parts) != 2 or parts[0] != "CANCEL":
        return create_message("CANCEL_RESP", "ERROR")

    user_hash = parts[1]
    hash_suffix = get_hash_suffix(user_hash)

    print(f"Hospital Server has received a cancel request from user with hash suffix: {hash_suffix} to cancel their appointment using TCP over port {HOSPITAL_TCP_PORT}.")

    request = create_message("CANCEL", user_hash)
    send_udp(udp_socket, request, LOCALHOST, APPOINTMENT_PORT)

    print("The hospital server has sent the cancel request to the appointment server.")

    response, _ = receive_udp(udp_socket)

    print(f"Hospital Server has received the response from Appointment Server using UDP over port {HOSPITAL_UDP_PORT}.")

    print("The hospital server has sent the response to the client.")
    return response

def handle_view_doctor_appointments_request(client_message: str, udp_socket: socket.socket):
    # Forwards a doctor's schedule view request to Appointment Server.
    parts = parse_message(client_message)

    if len(parts) != 2 or parts[0] != "VIEW_DOCTOR_APPOINTMENTS":
        return create_message("VIEW_DOCTOR_APPOINTMENTS_RESP", "ERROR")

    doctor_name = parts[1]

    print(f"Hospital Server has received a view appointments request from {doctor_name} to view their schedule details using TCP over port {HOSPITAL_TCP_PORT}.")

    request = create_message("VIEW_DOCTOR_APPOINTMENTS", doctor_name)
    send_udp(udp_socket, request, LOCALHOST, APPOINTMENT_PORT)

    print("The hospital server has sent the view appointments request to the Appointment Server.")

    response, _ = receive_udp(udp_socket)

    print(f"Hospital server has received the response from the Appointment server using UDP over port {HOSPITAL_UDP_PORT}.")

    print("The hospital server has sent the response to the client.")
    return response

def get_treatment_for_illness(filepath: str, illness: str):
    # Looks up the treatment for an illness in the [Treatments] section of hospital.txt.
    lines = read_file_lines(filepath)

    in_treatments_section = False

    for line in lines:
        if not line:
            continue

        if line == "[Treatments]":
            # Treatment lookup starts only after the [Treatments] marker.
            in_treatments_section = True
            continue

        if in_treatments_section:
            parts = line.split()
            if len(parts) >= 2:
                illness_name = parts[0]
                treatment = " ".join(parts[1:])
                if illness_name == illness:
                    return treatment

    return None

def handle_prescribe_request(client_message: str, udp_socket: socket.socket):
    # Prescribing needs two backend steps: get illness, then save treatment/frequency.
    parts = parse_message(client_message)

    if len(parts) != 4 or parts[0] != "PRESCRIBE":
        return create_message("PRESCRIBE_RESP", "ERROR")

    doctor_name = parts[1]
    patient_username = parts[2]
    frequency = parts[3]

    patient_hash = sha256_hash(patient_username)
    hash_suffix = get_hash_suffix(patient_hash)

    print(f"Hospital Server has received a prescription request from {doctor_name} for a user with hash suffix {hash_suffix} using TCP over port {HOSPITAL_TCP_PORT}.")

    # First confirm this doctor has an appointment/illness record for the patient.
    fetch_request = create_message("PRESCRIBE_FETCH", doctor_name, patient_hash)
    send_udp(udp_socket, fetch_request, LOCALHOST, APPOINTMENT_PORT)

    print(f"Hospital Server has sent a request to fetch patients with hash suffix {hash_suffix} illness information to the Appointment Server.")

    fetch_response, _ = receive_udp(udp_socket)

    print(f"Hospital Server has received the illness response from the Appointment server using UDP over port {HOSPITAL_UDP_PORT}.")

    fetch_parts = parse_message(fetch_response)
    if len(fetch_parts) < 2 or fetch_parts[1] != "FOUND":
        return create_message("PRESCRIBE_RESP", "NOT_FOUND")

    illness = fetch_parts[2]

    print(f"Acquiring treatment for {illness} from the database.")

    treatment = get_treatment_for_illness(HOSPITAL_FILE, illness)
    if treatment is None:
        return create_message("PRESCRIBE_RESP", "NOT_FOUND")

    # Once the treatment is known, persist the prescription through Prescription Server.
    save_request = create_message(
        "SAVE_PRESCRIPTION",
        doctor_name,
        patient_hash,
        treatment,
        frequency
    )
    send_udp(udp_socket, save_request, LOCALHOST, PRESCRIPTION_PORT)

    print(f"Hospital server has sent the prescription request to the prescription server to prescribe {treatment}.")

    save_response, _ = receive_udp(udp_socket)

    print(f"Hospital server has received the response from the prescription server using UDP over port {HOSPITAL_UDP_PORT}")

    print("The hospital server has sent the response to the client.")

    return create_message("PRESCRIBE_RESP", "SUCCESS", patient_username, treatment, frequency)

def handle_view_prescription_request(client_message: str, udp_socket: socket.socket):
    # Both doctors and patients read prescriptions from the same Prescription Server endpoint.
    parts = parse_message(client_message)

    if len(parts) < 2:
        return create_message("VIEW_PRESCRIPTION_RESP", "ERROR")

    if parts[0] == "VIEW_PRESCRIPTION_PATIENT" and len(parts) == 2:
        patient_hash = parts[1]
        hash_suffix = get_hash_suffix(patient_hash)

        print(f"Hospital Server has received a prescription request from a patient with hash suffix {hash_suffix} to view their prescription details using TCP over port {HOSPITAL_TCP_PORT}.")

        request = create_message("VIEW_PRESCRIPTION", patient_hash)
        # Hospital sends a simple patient-hash request to the prescription backend.
        send_udp(udp_socket, request, LOCALHOST, PRESCRIPTION_PORT)

        print("Hospital Server has sent the prescription request to the Prescription Server.")

        response, _ = receive_udp(udp_socket)

        print(f"Hospital server has received the response from the prescription server using UDP over port {HOSPITAL_UDP_PORT}.")
        print("Hospital server has sent the response to the client.")
        return response

    if parts[0] == "VIEW_PRESCRIPTION_DOCTOR" and len(parts) == 3:
        doctor_name = parts[1]
        patient_username = parts[2]
        # Doctors type a patient username, so Hospital converts it to the stored hash.
        patient_hash = sha256_hash(patient_username)
        hash_suffix = get_hash_suffix(patient_hash)

        print(f"Hospital Server has received a prescription request from {doctor_name} to view a patient with hash suffix {hash_suffix} prescription details using TCP over port {HOSPITAL_TCP_PORT}.")

        request = create_message("VIEW_PRESCRIPTION", patient_hash)
        send_udp(udp_socket, request, LOCALHOST, PRESCRIPTION_PORT)

        print("Hospital Server has sent the prescription request to the Prescription Server.")

        response, _ = receive_udp(udp_socket)

        print(f"Hospital server has received the response from the prescription server using UDP over port {HOSPITAL_UDP_PORT}.")
        print("Hospital server has sent the response to the client.")
        return response

    return create_message("VIEW_PRESCRIPTION_RESP", "ERROR")

def main():
    # Hospital Server bridges client TCP requests to backend UDP services.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        # One UDP socket is reused for backend requests and replies.
        udp_socket.bind((LOCALHOST, HOSPITAL_UDP_PORT))

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            # TCP is used here because clients need a reliable request/response channel.
            tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            tcp_socket.bind((LOCALHOST, HOSPITAL_TCP_PORT))
            # Allow up to 5 queued connections
            tcp_socket.listen(5)

            print(f"Hospital Server is up and running using UDP on port {HOSPITAL_UDP_PORT}.")

            try:
                while True:
                    conn, addr = tcp_socket.accept()

                    try:
                        # One TCP connection handles one client command, then closes.
                        message = receive_tcp(conn)
                        if not message:
                            conn.close()
                            continue

                        parts = parse_message(message)
                        if not parts:
                            conn.close()
                            continue

                        command = parts[0]

                        # Route each client command to the backend workflow that owns the data.
                        if command == "AUTH":
                            response = handle_auth_request(message, udp_socket)
                            send_tcp(conn, response)
                            print(f"Hospital Server has sent the response from Authentication Server to the client using TCP over port {HOSPITAL_TCP_PORT}.")

                        elif command == "LOOKUP":
                            response = handle_lookup_request(message, udp_socket)
                            send_tcp(conn, response)

                        elif command == "LOOKUP_DOCTOR":
                            response = handle_lookup_doctor_request(message, udp_socket)
                            send_tcp(conn, response)

                        elif command == "SCHEDULE":
                            response = handle_schedule_request(message, udp_socket)
                            send_tcp(conn, response)

                        elif command == "VIEW_APPOINTMENT":
                            response = handle_view_appointment_request(message, udp_socket)
                            send_tcp(conn, response)

                        elif command == "CANCEL":
                            response = handle_cancel_request(message, udp_socket)
                            send_tcp(conn, response)

                        elif command == "VIEW_DOCTOR_APPOINTMENTS":
                            response = handle_view_doctor_appointments_request(message, udp_socket)
                            send_tcp(conn, response)

                        elif command == "PRESCRIBE":
                            response = handle_prescribe_request(message, udp_socket)
                            send_tcp(conn, response)

                        elif command == "VIEW_PRESCRIPTION_PATIENT" or command == "VIEW_PRESCRIPTION_DOCTOR":
                            response = handle_view_prescription_request(message, udp_socket)
                            send_tcp(conn, response)

                        else:
                            send_tcp(conn, "UNSUPPORTED")

                    finally:
                        conn.close()
            except KeyboardInterrupt:
                print("\nHospital Server shutting down.")
            except OSError as e:
                print(f"Hospital Server error: {e}")
                sys.exit(1)


if __name__ == "__main__":
    main()
