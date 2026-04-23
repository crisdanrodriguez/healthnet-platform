import sys
import socket
from utils import *

# Approach: the client never contacts backend servers directly.
# Every user command goes to the Hospital Server, which keeps the client simple.


def authenticate_user(username: str, password: str):
    # The client hashes credentials before sending them through the system.
    username_hash = sha256_hash(username)
    password_hash = sha256_hash(password)

    # Build the same AUTH format that Hospital Server expects.
    message = create_message("AUTH", username_hash, password_hash)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((LOCALHOST, HOSPITAL_TCP_PORT))

        print("The client is up and running.")
        print(f"{username} sent an authentication request to the hospital server.")

        # The client sends the hashed credentials to the Hospital Server
        send_tcp(client_socket, message)

        # Receives the authentication result and parse to determine the user's role if successful.
        response = receive_tcp(client_socket)
        parts = parse_message(response)

        if not parts:
            print("The credentials are incorrect. Please try again.")
            return None

        # Failed case
        if parts[0] == "AUTH_FAIL":
            print("The credentials are incorrect. Please try again.")
            return None

        # Successful case with role information
        if parts[0] == "AUTH_OK" and len(parts) == 2:
            role = parts[1]

            if role == "patient":
                print(f"{username} received the authentication result. Authentication successful. You have been granted patient access.")
                return {
                    "username": username,
                    "username_hash": username_hash,
                    "role": "patient",
                }

            if role == "doctor":
                print(f"{username} received the authentication result. Authentication successful. You have been granted doctor access.")
                return {
                    "username": username,
                    "username_hash": username_hash,
                    "role": "doctor",
                }

        print("The credentials are incorrect. Please try again.")
        return None

def send_request(message: str) -> str:
    # Each command opens a short TCP connection to the Hospital Server.
    # This matches the project flow where the Hospital Server is the client-facing process.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((LOCALHOST, HOSPITAL_TCP_PORT))
        send_tcp(sock, message)
        return receive_tcp(sock)

def print_help(role: str):
    # Help command lists the available commands for the user based on their role.
    if role == "patient":
        print("Please enter the command:")
        print("<lookup>,")
        print("<lookup <doctor>>,")
        print("<schedule <doctor> <start_time> <illness>>,")
        print("<cancel>,")
        print("<view_appointment>,")
        print("<view_prescription>,")
        print("<quit>")
    elif role == "doctor":
        print("Please enter the command:")
        print("<view_appointments>,")
        print("<prescribe <patient> <frequency>>,")
        print("<view_prescription <patient>>,")
        print("<quit>")

def handle_lookup(user_info):
    # Patient lookup without a doctor name returns the list of doctors in the system.
    username = user_info["username"]
    username_hash = user_info["username_hash"]

    print(f"{username} sent a lookup request to the hospital server.")

    message = create_message("LOOKUP", username_hash)
    response = send_request(message)
    # Responses also use the delimiter, so I parse before checking status.
    parts = parse_message(response)

    if parts[0] != "LOOKUP_RESP":
        return

    print(f"The client received the response from the hospital server using TCP over port {HOSPITAL_TCP_PORT}.")
    print("The following doctors are available:")
    for doctor in parts[1:]:
        print(doctor)

def handle_lookup_doctor(user_info, doctor_name: str):
    # Patient lookup with a doctor name asks for that doctor's available slots.
    username = user_info["username"]
    username_hash = user_info["username_hash"]

    print(f"Patient {username} sent a lookup request to the hospital server for {doctor_name}.")

    message = create_message("LOOKUP_DOCTOR", username_hash, doctor_name)
    response = send_request(message)
    # The response tells if this doctor has all, none, or some slots free.
    parts = parse_message(response)

    if len(parts) < 3 or parts[0] != "LOOKUP_DOCTOR_RESP":
        return

    status = parts[1]

    if status == "ALL_AVAILABLE":
        print(f"The client received the response from the hospital server using TCP over port {HOSPITAL_TCP_PORT}.")
        print(f"All time blocks are available for {doctor_name}.")
    elif status == "NONE_AVAILABLE":
        print(f"The client received the response from the Hospital Server using TCP over port {HOSPITAL_TCP_PORT}.")
        print(f"{doctor_name} has no time slots available.")
    elif status == "SOME_AVAILABLE":
        print(f"The client received the response from the Hospital Server using TCP over port {HOSPITAL_TCP_PORT}.")
        print(f"{doctor_name} is available at times:")
        for slot in parts[3:]:
            print(slot)

def handle_schedule(user_info, doctor_name: str, time_slot: str, illness: str):
    # Scheduling starts at the client, but Appointment Server owns the final decision.
    username = user_info["username"]
    username_hash = user_info["username_hash"]

    print(f"{username} sent an appointment schedule request to the hospital server.")

    # Illness stays as one message field so multi-word illnesses are preserved.
    message = create_message("SCHEDULE", username_hash, doctor_name, time_slot, illness)
    response = send_request(message)
    parts = parse_message(response)

    if len(parts) < 4 or parts[0] != "SCHEDULE_RESP":
        return

    status = parts[1]

    if status == "SUCCESS":
        print(f"The client received the response from the Hospital Server using TCP over port {HOSPITAL_TCP_PORT}")
        print(f"An appointment has been successfully scheduled for patient {username} with {doctor_name} at {time_slot}.")

    elif status == "TIME_NOT_AVAILABLE":
        print(f"The client received the response from the hospital server using TCP over port {HOSPITAL_TCP_PORT}")
        if len(parts) > 4:
            print(f"Unable to schedule an appointment with {doctor_name} at {time_slot}. Other available time blocks are")
            for slot in parts[4:]:
                print(slot)
        else:
            print(f"Unable to schedule an appointment with {doctor_name} at this time, as all time blocks have been taken up.")

    elif status == "INVALID_TIME":
        print(f"The client received the response from the hospital server using TCP over port {HOSPITAL_TCP_PORT}")
        if len(parts) > 4:
            print(f"Unable to schedule an appointment with {doctor_name} at {time_slot}. Other available time blocks are")
            for slot in parts[4:]:
                print(slot)
        else:
            print(f"Unable to schedule an appointment with {doctor_name} at this time, as all time blocks have been taken up.")

def command_loop(user_info):
    # After login, role decides which commands the user is allowed to run.
    role = user_info["role"]

    while True:
        try:
            command = input().strip()
        except EOFError:
            break

        if not command:
            continue

        if command == "help":
            print_help(role)

        elif command == "quit":
            print("You have successfully been logged out.")
            break

        # Patient commands manage appointments and patient-side prescription lookup.
        elif role == "patient" and command == "lookup":
            handle_lookup(user_info)

        # Doctor lookup with a doctor name asks for that doctor's available slots.
        elif role == "patient" and command.startswith("lookup "):
            parts = command.split()
            if len(parts) == 2:
                handle_lookup_doctor(user_info, parts[1])

        # Schedule command includes doctor name, time slot, and illness description.
        elif role == "patient" and command.startswith("schedule "):
            parts = command.split()
            if len(parts) >= 4:
                doctor_name = parts[1]
                time_slot = parts[2]
                # Everything after the time is treated as the illness description.
                illness = " ".join(parts[3:])
                handle_schedule(user_info, doctor_name, time_slot, illness)

        # View appointment and cancel commands only require the patient's username hash, which is stored in the client.
        elif role == "patient" and command == "view_appointment":
            handle_view_appointment(user_info)

        elif role == "patient" and command == "cancel":
            handle_cancel(user_info)

        # Doctor commands manage schedules and prescription actions.
        elif role == "doctor" and command == "view_appointments":
            handle_view_doctor_appointments(user_info)

        elif role == "patient" and command == "view_prescription":
            handle_view_prescription_patient(user_info)

        elif role == "doctor" and command.startswith("prescribe "):
            parts = command.split()
            if len(parts) == 3:
                handle_prescribe(user_info, parts[1], parts[2])

        elif role == "doctor" and command.startswith("view_prescription "):
            parts = command.split()
            if len(parts) == 2:
                handle_view_prescription_doctor(user_info, parts[1])

        else:
            print_help(role)

def handle_view_appointment(user_info):
    # Patients can only view their own appointment, identified by their username hash.
    username = user_info["username"]
    username_hash = user_info["username_hash"]

    print(f"{username} sent a request to view their appointment to the Hospital Server.")

    message = create_message("VIEW_APPOINTMENT", username_hash)
    response = send_request(message)
    parts = parse_message(response)

    if len(parts) < 2 or parts[0] != "VIEW_APPOINTMENT_RESP":
        return

    status = parts[1]

    if status == "FOUND":
        doctor_name = parts[2]
        time_slot = parts[3]
        print(f"The client received the response from the hospital server using TCP over port {HOSPITAL_TCP_PORT}")
        print(f"You have an appointment scheduled with {doctor_name} at {time_slot}.")
    elif status == "NOT_FOUND":
        print(f"The client received the response from the hospital server using TCP over client port {HOSPITAL_TCP_PORT}")
        print("You do not have an appointment today.")

def handle_cancel(user_info):
    # Patients can only cancel their own appointment, identified by their username hash.
    username = user_info["username"]
    username_hash = user_info["username_hash"]

    print(f"{username} sent a cancellation request to the Hospital Server.")

    message = create_message("CANCEL", username_hash)
    response = send_request(message)
    parts = parse_message(response)

    if len(parts) < 2 or parts[0] != "CANCEL_RESP":
        return

    status = parts[1]

    if status == "SUCCESS":
        doctor_name = parts[2]
        time_slot = parts[3]
        print(f"The client received the response from the Hospital Server using TCP over port {HOSPITAL_TCP_PORT}")
        print(f"You have successfully cancelled your appointment with {doctor_name} at {time_slot}.")
    elif status == "NOT_FOUND":
        print(f"The client received the response from the Hospital Server using TCP over port {HOSPITAL_TCP_PORT}")
        print("You have no appointments available to cancel.")

def handle_view_doctor_appointments(user_info):
    # Doctors view appointments by their doctor name, not by username hash.
    doctor_name = user_info["username"]

    print(f"{doctor_name} sent a request to view their scheduled appointments to the Hospital Server.")

    message = create_message("VIEW_DOCTOR_APPOINTMENTS", doctor_name)
    response = send_request(message)
    parts = parse_message(response)

    if len(parts) < 3 or parts[0] != "VIEW_DOCTOR_APPOINTMENTS_RESP":
        return

    status = parts[1]

    if status == "NONE":
        print(f"The client received the response from the hospital server using TCP over port {HOSPITAL_TCP_PORT}")
        print("You do not have any appointments scheduled.")
    elif status == "FOUND":
        print(f"The client received the response from the hospital server using TCP over port {HOSPITAL_TCP_PORT}")
        print(f"{doctor_name} is scheduled at times:")
        for slot in parts[3:]:
            print(slot)

def handle_prescribe(user_info, patient_username: str, frequency: str):
    # Doctors prescribe by patient username; the Hospital Server converts it to a hash.
    doctor_name = user_info["username"]

    print(f"{doctor_name} sent a request to the Hospital Server to prescribe {patient_username} following their diagnosis.")

    message = create_message("PRESCRIBE", doctor_name, patient_username, frequency)
    response = send_request(message)
    parts = parse_message(response)

    if len(parts) < 2 or parts[0] != "PRESCRIBE_RESP":
        return

    if parts[1] == "SUCCESS":
        treatment = parts[3]
        print(f"The client received the response from the hospital server using TCP over port {HOSPITAL_TCP_PORT}")
        print(f"You have successfully prescribed {patient_username} with {treatment}, to be taken {frequency}.")

def handle_view_prescription_patient(user_info):
    # Patients request prescriptions using their own stored username hash.
    username = user_info["username"]
    patient_hash = user_info["username_hash"]

    print(f"{username} sent a request to view their prescription to the Hospital Server.")

    message = create_message("VIEW_PRESCRIPTION_PATIENT", patient_hash)
    response = send_request(message)
    parts = parse_message(response)

    if len(parts) < 2 or parts[0] != "VIEW_PRESCRIPTION_RESP":
        return

    if parts[1] == "NOT_FOUND":
        print(f"The client received the response from the hospital server using TCP over port {HOSPITAL_TCP_PORT}")
        print("You do not have a prescription to look up.")
    elif parts[1] == "FOUND":
        doctor_name = parts[2]
        treatment = parts[3]
        frequency = parts[4]
        print(f"The client received the response from the hospital server using TCP over port {HOSPITAL_TCP_PORT}")
        print(f"You have been prescribed {treatment}, to be taken {frequency}, by {doctor_name}.")

def handle_view_prescription_doctor(user_info, patient_username: str):
    # Doctors request prescriptions by patient name; the Hospital Server converts it to a hash and
    # checks if the doctor is the one who prescribed it.
    doctor_name = user_info["username"]

    print(f"{doctor_name} sent a request to view {patient_username} prescription to the Hospital Server.")

    message = create_message("VIEW_PRESCRIPTION_DOCTOR", doctor_name, patient_username)
    response = send_request(message)
    parts = parse_message(response)

    if len(parts) < 2 or parts[0] != "VIEW_PRESCRIPTION_RESP":
        return

    if parts[1] == "NOT_FOUND":
        print(f"The client received the response from the hospital server using TCP over port {HOSPITAL_TCP_PORT}")
        print(f"{patient_username} does not have a prescription.")
    elif parts[1] == "FOUND":
        doctor_name_from_entry = parts[2]
        treatment = parts[3]
        frequency = parts[4]
        print(f"The client received the response from the hospital server using TCP over port {HOSPITAL_TCP_PORT}")
        print(f"{patient_username} has been prescribed {treatment}, to be taken {frequency}, by {doctor_name_from_entry}.")


def main():
    # Reads username/password from the command line and starts the client session.
    if len(sys.argv) != 3:
        print("Usage: python3 client.py <username> <password>")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]

    user_info = authenticate_user(username, password)

    if user_info is None:
        sys.exit(0)

    command_loop(user_info)


if __name__ == "__main__":
    main()
