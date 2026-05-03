import sys
import socket
from utils import (
    APPOINTMENT_PORT,
    LOCALHOST,
    create_message,
    data_path,
    get_hash_suffix,
    is_valid_time_slot,
    normalize_time_slot,
    parse_message,
    read_file_lines,
    receive_udp,
    send_udp,
    write_file_lines,
)

# Appointment Server owns appointment state.
# It reads/writes appointments.txt and responds to Hospital Server over UDP.
# Hospital Server validates the client-facing command, then this server updates the schedule.


APPOINTMENTS_FILE = data_path("appointments.txt")
HOSPITAL_FILE = data_path("hospital.txt")


def load_appointments(filepath: str) -> dict:
    # Read the appointments file and return a dictionary mapping doctor names to their appointment lines.
    appointments = {}
    lines = read_file_lines(filepath)

    current_doctor = None

    for line in lines:
        if not line:
            continue

        parts = line.split()

        if len(parts) == 1 and ":" not in parts[0]:
            # A doctor name starts a new group of time slots.
            current_doctor = parts[0]
            appointments[current_doctor] = []
        else:
            if current_doctor is not None:
                # Keep the original slot line so booked slots keep patient/illness data.
                appointments[current_doctor].append(line)

    return appointments

def write_appointments(filepath: str, appointments: dict) -> None:
    # Writes the appointments dictionary back into appointments.txt.
    lines = []

    for doctor, slots in appointments.items():
        # Keep the same grouped format as the original appointments.txt file.
        lines.append(doctor)
        for slot in slots:
            lines.append(slot)

    write_file_lines(filepath, lines)

def get_available_slots(appointments: dict, doctor_name: str) -> list:
    # Finds the free time slots for one doctor.
    if doctor_name not in appointments:
        return None

    available = []

    for entry in appointments[doctor_name]:
        parts = entry.split()
        if len(parts) == 1:
            # A line with only a time means the slot has not been booked.
            available.append(parts[0])

    return available

def get_doctor_list(filepath: str) -> list:
    # Read doctor names from hospital.txt for the plain lookup command.
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
                doctors.append(parts[0])

    return doctors

def schedule_appointment(
    appointments: dict,
    doctor_name: str,
    time_slot: str,
    patient_hash: str,
    illness: str,
) -> tuple:
    # Tries to reserve a time slot for a patient.
    if doctor_name not in appointments:
        return "DOCTOR_NOT_FOUND", None

    # Normalize so "9:00", "09:00", and "9:00am" refer to the same slot.
    requested_time = normalize_time_slot(time_slot)
    available_slots = get_available_slots(appointments, doctor_name)

    if not is_valid_time_slot(requested_time):
        return "INVALID_TIME", available_slots

    doctor_slots = appointments[doctor_name]

    for i, entry in enumerate(doctor_slots):
        parts = entry.split()
        current_time = parts[0]

        if normalize_time_slot(current_time) == requested_time:
            if len(parts) == 1:
                # Save patient hash and illness on the slot when it is still free.
                doctor_slots[i] = f"{current_time} {patient_hash} {illness}"
                return "SUCCESS", None
            # If there is already patient data, the slot is taken.
            return "TIME_NOT_AVAILABLE", available_slots

    return "INVALID_TIME", available_slots

def handle_lookup_doctor(doctor_name: str) -> str:
    # Lookup does not change the file; it only reports availability.
    appointments = load_appointments(APPOINTMENTS_FILE)
    available_slots = get_available_slots(appointments, doctor_name)

    if available_slots is None:
        return create_message("LOOKUP_DOCTOR_RESP", "NOT_FOUND", doctor_name)

    if len(available_slots) == 8:
        print(f"All time blocks are available for {doctor_name}.")
        return create_message("LOOKUP_DOCTOR_RESP", "ALL_AVAILABLE", doctor_name)

    if len(available_slots) == 0:
        print(f"{doctor_name} has no time slots available.")
        return create_message("LOOKUP_DOCTOR_RESP", "NONE_AVAILABLE", doctor_name)

    print(f"{doctor_name} has some time slots available.")
    return create_message(
        "LOOKUP_DOCTOR_RESP",
        "SOME_AVAILABLE",
        doctor_name,
        *available_slots
    )

def handle_lookup() -> str:
    # Plain lookup returns the full doctor list.
    doctors = get_doctor_list(HOSPITAL_FILE)
    return create_message("LOOKUP_RESP", *doctors)

def handle_schedule(doctor_name: str, time_slot: str, patient_hash: str, illness: str) -> str:
    # This wrapper loads the latest file state, schedules, then saves only on success.
    appointments = load_appointments(APPOINTMENTS_FILE)

    status, available_slots = schedule_appointment(
        appointments,
        doctor_name,
        time_slot,
        patient_hash,
        illness,
    )

    hash_suffix = get_hash_suffix(patient_hash)

    print(f"Appointment scheduling request received (time: {time_slot}, doctor: {doctor_name}, patient hash suffix: {hash_suffix}, illness: {illness}).")

    if status == "SUCCESS":
        write_appointments(APPOINTMENTS_FILE, appointments)
        print(f"Appointment has been scheduled successfully for user {hash_suffix} with {doctor_name}.")
        return create_message("SCHEDULE_RESP", "SUCCESS", doctor_name, time_slot)

    if status == "TIME_NOT_AVAILABLE":
        print("The requested appointment time is not available.")
        return create_message(
            "SCHEDULE_RESP",
            "TIME_NOT_AVAILABLE",
            doctor_name,
            time_slot,
            *(available_slots or [])
        )

    if status == "INVALID_TIME":
        print("The requested appointment time is not available.")
        return create_message(
            "SCHEDULE_RESP",
            "INVALID_TIME",
            doctor_name,
            time_slot,
            *(available_slots or [])
        )

    return create_message("SCHEDULE_RESP", "DOCTOR_NOT_FOUND", doctor_name, time_slot)

def find_patient_appointment(appointments: dict, patient_hash: str):
    # Finds the appointment that belongs to one patient hash.
    for doctor_name, slots in appointments.items():
        for entry in slots:
            parts = entry.split()
            if len(parts) >= 2:
                time_slot = parts[0]
                stored_patient_hash = parts[1]
                if stored_patient_hash == patient_hash:
                    return doctor_name, time_slot
    return None, None

def cancel_appointment(appointments: dict, patient_hash: str):
    # Finds a patient's appointment and clears that slot.
    for doctor_name, slots in appointments.items():
        for i, entry in enumerate(slots):
            parts = entry.split()
            if len(parts) >= 2:
                time_slot = parts[0]
                stored_patient_hash = parts[1]
                if stored_patient_hash == patient_hash:
                    # Reset the line back to only the time, making the slot available again.
                    slots[i] = time_slot
                    return True, doctor_name, time_slot
    return False, None, None

def get_doctor_scheduled_slots(appointments: dict, doctor_name: str):
    # Returns the booked time slots for a doctor.
    if doctor_name not in appointments:
        return None

    scheduled = []
    for entry in appointments[doctor_name]:
        parts = entry.split()
        if len(parts) >= 2:
            scheduled.append(parts[0])

    return scheduled

def handle_view_appointment(patient_hash: str):
    # View searches by patient hash because usernames are never stored in appointments.txt.
    appointments = load_appointments(APPOINTMENTS_FILE)
    hash_suffix = get_hash_suffix(patient_hash)

    print(f"Appointment Server has received a view appointment command for the user with hash suffix {hash_suffix}.")

    doctor_name, time_slot = find_patient_appointment(appointments, patient_hash)

    if doctor_name is None:
        print(f"The user with hash suffix {hash_suffix} has no appointment in the system.")
        return create_message("VIEW_APPOINTMENT_RESP", "NOT_FOUND")

    print(f"Returning details regarding the appointment for the user with hash suffix {hash_suffix}.")
    return create_message("VIEW_APPOINTMENT_RESP", "FOUND", doctor_name, time_slot)

def handle_cancel(patient_hash: str):
    # Cancelling is the opposite of scheduling: replace the full record with just the time.
    appointments = load_appointments(APPOINTMENTS_FILE)
    hash_suffix = get_hash_suffix(patient_hash)

    print(f"Appointment Server has received a cancel appointment command for the user with hash suffix: {hash_suffix}.")

    success, doctor_name, time_slot = cancel_appointment(appointments, patient_hash)

    if not success:
        print("Error: Failed to find appointment.")
        return create_message("CANCEL_RESP", "NOT_FOUND")

    write_appointments(APPOINTMENTS_FILE, appointments)
    print("Successfully cancelled appointment.")
    return create_message("CANCEL_RESP", "SUCCESS", doctor_name, time_slot)

def handle_view_doctor_appointments(doctor_name: str):
    # Returns the booked slots for a doctor.
    appointments = load_appointments(APPOINTMENTS_FILE)

    print(f"Appointment Server has received a request to view appointments scheduled for {doctor_name}.")

    scheduled_slots = get_doctor_scheduled_slots(appointments, doctor_name)

    if scheduled_slots is None or len(scheduled_slots) == 0:
        print(f"No appointments have been made for {doctor_name}.")
        return create_message("VIEW_DOCTOR_APPOINTMENTS_RESP", "NONE", doctor_name)

    print(f"Returning the scheduled appointments for {doctor_name}.")
    return create_message(
        "VIEW_DOCTOR_APPOINTMENTS_RESP",
        "FOUND",
        doctor_name,
        *scheduled_slots
    )

def fetch_illness_and_clear_slot(appointments: dict, doctor_name: str, patient_hash: str):
    # Finds the patient's illness for a doctor and clears the appointment after prescribing.
    if doctor_name not in appointments:
        return False, None, None

    slots = appointments[doctor_name]

    for i, entry in enumerate(slots):
        parts = entry.split()
        if len(parts) >= 3:
            time_slot = parts[0]
            stored_patient_hash = parts[1]
            illness = " ".join(parts[2:])

            if stored_patient_hash == patient_hash:
                # Prescribing finishes the appointment, so the slot becomes free again.
                slots[i] = time_slot
                return True, illness, time_slot

    return False, None, None

def handle_prescribe_fetch(doctor_name: str, patient_hash: str):
    # Prescription flow consumes the appointment illness, then clears the appointment slot.
    appointments = load_appointments(APPOINTMENTS_FILE)
    hash_suffix = get_hash_suffix(patient_hash)

    print(f"Appointment Server has received a request from Hospital Server regarding information about a user with hash suffix {hash_suffix} from {doctor_name}.")

    success, illness, time_slot = fetch_illness_and_clear_slot(
        appointments,
        doctor_name,
        patient_hash
    )

    if not success:
        return create_message("PRESCRIBE_FETCH_RESP", "NOT_FOUND")

    print("Sending back the requested information to the Hospital server.")

    write_appointments(APPOINTMENTS_FILE, appointments)

    print(f"Successfully removed {hash_suffix} appointment slot, {time_slot} is now free to be scheduled for tomorrow.")

    return create_message("PRESCRIBE_FETCH_RESP", "FOUND", illness)

def main():
    # Starts the UDP Appointment Server and waits for commands from Hospital Server.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        # Appointment Server is backend-only, so it receives UDP from Hospital.
        server_socket.bind((LOCALHOST, APPOINTMENT_PORT))

        print(f"Appointment Server is up and running using UDP on port {APPOINTMENT_PORT}.")

        try:
            while True:
                message, addr = receive_udp(server_socket)
                # Every UDP request starts with a command, then the values needed for it.
                parts = parse_message(message)

                if not parts:
                    continue

                command = parts[0]

                # Dispatch based on the command sent by Hospital Server.
                if command == "LOOKUP" and len(parts) == 2:
                    print("The Appointment Server has received a doctor availability request.")
                    response = handle_lookup()
                    send_udp(server_socket, response, addr[0], addr[1])
                    print("The Appointment Server has sent the lookup result to the Hospital Server.")

                elif command == "LOOKUP_DOCTOR" and len(parts) == 2:
                    doctor_name = parts[1]

                    print("The Appointment Server has received a doctor availability request.")
                    response = handle_lookup_doctor(doctor_name)
                    # Reply to the same Hospital Server UDP port that sent this request.
                    send_udp(server_socket, response, addr[0], addr[1])
                    print("The Appointment Server has sent the lookup result to the Hospital Server.")

                elif command == "SCHEDULE" and len(parts) == 5:
                    patient_hash = parts[1]
                    doctor_name = parts[2]
                    time_slot = parts[3]
                    illness = parts[4]

                    response = handle_schedule(doctor_name, time_slot, patient_hash, illness)
                    send_udp(server_socket, response, addr[0], addr[1])

                elif command == "VIEW_APPOINTMENT" and len(parts) == 2:
                    patient_hash = parts[1]
                    response = handle_view_appointment(patient_hash)
                    send_udp(server_socket, response, addr[0], addr[1])

                elif command == "CANCEL" and len(parts) == 2:
                    patient_hash = parts[1]
                    response = handle_cancel(patient_hash)
                    send_udp(server_socket, response, addr[0], addr[1])

                elif command == "PRESCRIBE_FETCH" and len(parts) == 3:
                    doctor_name = parts[1]
                    patient_hash = parts[2]

                    response = handle_prescribe_fetch(doctor_name, patient_hash)
                    send_udp(server_socket, response, addr[0], addr[1])

                elif command == "VIEW_DOCTOR_APPOINTMENTS" and len(parts) == 2:
                    doctor_name = parts[1]
                    response = handle_view_doctor_appointments(doctor_name)
                    send_udp(server_socket, response, addr[0], addr[1])

        except KeyboardInterrupt:
            print("\nAppointment Server shutting down.")
        except OSError as e:
            print(f"Appointment Server error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
