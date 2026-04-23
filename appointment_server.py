import socket
from utils import *


APPOINTMENTS_FILE = "appointments.txt"


def load_appointments(filepath: str) -> dict:
    """
    Loads appointment data from the file and groups it by doctor.
    Expected format:
    <Doctor Name>
    <time> <patient_hash> <illness>
    ...
    <Doctor Name>
    <time>
    ...
    Args:
        filepath: The path to the appointments file.
    Returns:
        A dictionary mapping doctor names to lists of their appointment lines.
    """
    appointments = {}
    lines = read_file_lines(filepath)

    current_doctor = None

    for line in lines:
        if not line:
            continue

        parts = line.split()

        if len(parts) == 1 and ":" not in parts[0]:
            current_doctor = parts[0]
            appointments[current_doctor] = []
        else:
            if current_doctor is not None:
                appointments[current_doctor].append(line)

    return appointments


def write_appointments(filepath: str, appointments: dict) -> None:
    """
    Writes the appointment data back to the file in the expected format. 
    Args:
        filepath: The path to the appointments file.
        appointments: A dictionary mapping doctor names to lists of their appointment lines.
    """
    lines = []

    for doctor, slots in appointments.items():
        lines.append(doctor)
        for slot in slots:
            lines.append(slot)

    write_file_lines(filepath, lines)


def get_available_slots(appointments: dict, doctor_name: str) -> list:
    """
    Returns a list of available time slots for the given doctor.
    Args:
        appointments: A dictionary mapping doctor names to lists of their appointment lines.
        doctor_name: The name of the doctor to check availability for.
    Returns:
        A list of available time slots for the doctor, or None if the doctor is not found
    """
    if doctor_name not in appointments:
        return None

    available = []

    for entry in appointments[doctor_name]:
        parts = entry.split()
        if len(parts) == 1:
            available.append(parts[0])

    return available


def schedule_appointment(
    appointments: dict,
    doctor_name: str,
    time_slot: str,
    patient_hash: str,
    illness: str,
) -> tuple:
    """
    Attempts to schedule an appointment for a patient with a doctor at a specific time slot.
    Args:
        appointments: A dictionary mapping doctor names to lists of their appointment lines.
        doctor_name: The name of the doctor to schedule with.
        time_slot: The desired time slot for the appointment.
        patient_hash: The hash of the patient's username.
        illness: The illness the patient is seeking treatment for.
    Returns:
        A tuple containing a status string and a list of available slots (if applicable).
    Status can be:
        "SUCCESS" - appointment was successfully scheduled
        "DOCTOR_NOT_FOUND" - the specified doctor does not exist
        "TIME_NOT_AVAILABLE" - the specified time slot is already booked
        "INVALID_TIME" - the specified time slot is not valid (e.g., not in the doctor's schedule)
    """
    if doctor_name not in appointments:
        return "DOCTOR_NOT_FOUND", None

    available_slots = get_available_slots(appointments, doctor_name)

    if not is_valid_time_slot(time_slot):
        return "INVALID_TIME", available_slots

    doctor_slots = appointments[doctor_name]

    for i, entry in enumerate(doctor_slots):
        parts = entry.split()
        current_time = parts[0]

        if current_time == time_slot:
            # free slot
            if len(parts) == 1:
                doctor_slots[i] = f"{time_slot} {patient_hash} {illness}"
                return "SUCCESS", None
            # occupied slot
            return "TIME_NOT_AVAILABLE", available_slots

    return "INVALID_TIME", available_slots


def handle_lookup_doctor(doctor_name: str) -> str:
    """
    Handles a doctor availability lookup request.
    Args:
        doctor_name: The name of the doctor to look up.
    Returns:
        A response message indicating the availability of the doctor.
    Status can be:
        "NOT_FOUND": The specified doctor does not exist.
        "ALL_AVAILABLE": All time slots for the doctor are available.
        "NONE_AVAILABLE": No time slots for the doctor are available.
        "SOME_AVAILABLE": Some time slots for the doctor are available, followed by the
        list of available time slots.
    """
    appointments = load_appointments(APPOINTMENTS_FILE)
    available_slots = get_available_slots(appointments, doctor_name)

    if available_slots is None:
        return build_message("LOOKUP_DOCTOR_RESP", "NOT_FOUND", doctor_name)

    if len(available_slots) == 8:
        print(f"All time blocks are available for {doctor_name}.")
        return build_message("LOOKUP_DOCTOR_RESP", "ALL_AVAILABLE", doctor_name)

    if len(available_slots) == 0:
        print(f"{doctor_name} has no time slots available.")
        return build_message("LOOKUP_DOCTOR_RESP", "NONE_AVAILABLE", doctor_name)

    print(f"{doctor_name} has some time slots available.")
    return build_message(
        "LOOKUP_DOCTOR_RESP",
        "SOME_AVAILABLE",
        doctor_name,
        *available_slots
    )


def handle_schedule(doctor_name: str, time_slot: str, patient_hash: str, illness: str) -> str:
    """Handles an appointment scheduling request.
    Args:        
        doctor_name: The name of the doctor to schedule with.
        time_slot: The desired time slot for the appointment.
        patient_hash: The hash of the patient's username.
        illness: The illness the patient is seeking treatment for.
    Returns:
        A response message indicating the result of the scheduling attempt.
    Status can be:
        "SUCCESS" - appointment was successfully scheduled
        "DOCTOR_NOT_FOUND" - the specified doctor does not exist
        "TIME_NOT_AVAILABLE" - the specified time slot is already booked
        "INVALID_TIME" - the specified time slot is not valid (e.g., not in the doctor's schedule)
    """
    appointments = load_appointments(APPOINTMENTS_FILE)

    status, available_slots = schedule_appointment(
        appointments,
        doctor_name,
        time_slot,
        patient_hash,
        illness,
    )

    hash_suffix = get_hash_suffix(patient_hash)

    print(
        f"Appointment scheduling request received (time: {time_slot}, doctor: {doctor_name}, patient hash suffix: {hash_suffix}, illness: {illness})."
    )

    if status == "SUCCESS":
        write_appointments(APPOINTMENTS_FILE, appointments)
        print(
            f"Appointment has been scheduled successfully for user {hash_suffix} with {doctor_name}."
        )
        return build_message("SCHEDULE_RESP", "SUCCESS", doctor_name, time_slot)

    if status == "TIME_NOT_AVAILABLE":
        print("The requested appointment time is not available.")
        return build_message(
            "SCHEDULE_RESP",
            "TIME_NOT_AVAILABLE",
            doctor_name,
            time_slot,
            *(available_slots or [])
        )

    if status == "INVALID_TIME":
        print("The requested appointment time is not available.")
        return build_message(
            "SCHEDULE_RESP",
            "INVALID_TIME",
            doctor_name,
            time_slot,
            *(available_slots or [])
        )

    return build_message("SCHEDULE_RESP", "DOCTOR_NOT_FOUND", doctor_name, time_slot)


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((LOCALHOST, APPOINTMENT_PORT))

    print(f"Appointment Server is up and running using UDP on port {APPOINTMENT_PORT}.")

    while True:
        message, addr = receive_udp(server_socket)
        parts = parse_message(message)

        if not parts:
            continue

        command = parts[0]

        if command == "LOOKUP_DOCTOR" and len(parts) == 2:
            doctor_name = parts[1]

            print("The Appointment Server has received a doctor availability request.")
            response = handle_lookup_doctor(doctor_name)
            send_udp(server_socket, response, addr[0], addr[1])
            print("The Appointment Server has sent the lookup result to the Hospital Server.")

        elif command == "SCHEDULE" and len(parts) == 5:
            patient_hash = parts[1]
            doctor_name = parts[2]
            time_slot = parts[3]
            illness = parts[4]

            response = handle_schedule(doctor_name, time_slot, patient_hash, illness)
            send_udp(server_socket, response, addr[0], addr[1])