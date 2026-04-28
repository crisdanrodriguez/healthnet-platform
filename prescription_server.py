import socket
import sys
from utils import *

# Approach: Prescription Server is responsible only for prescription storage.
# Hospital Server decides when to save or view a prescription, then sends UDP requests here.


PRESCRIPTIONS_FILE = "prescriptions.txt"


def load_prescriptions(filepath: str):
    # Reads prescription records from prescriptions.txt.
    prescriptions = []
    lines = read_file_lines(filepath)

    for line in lines:
        if not line:
            continue

        parts = line.split()
        if len(parts) >= 4:
            # Frequency may contain spaces, so keep everything after treatment together.
            doctor_name = parts[0]
            patient_hash = parts[1]
            treatment = parts[2]
            frequency = " ".join(parts[3:])
            prescriptions.append((doctor_name, patient_hash, treatment, frequency))

    return prescriptions

def find_prescription(filepath: str, patient_hash: str):
    # Finds the prescription for one patient hash.
    prescriptions = load_prescriptions(filepath)

    for doctor_name, stored_patient_hash, treatment, frequency in prescriptions:
        # Patient hash is used as the lookup key instead of plain username.
        if stored_patient_hash == patient_hash:
            return doctor_name, treatment, frequency

    return None, None, None

def handle_save_prescription(doctor_name: str, patient_hash: str, treatment: str, frequency: str):
    # Saves a new prescription line to prescriptions.txt.
    hash_suffix = get_hash_suffix(patient_hash)

    print(f"Prescription Server has received a request from {doctor_name} to prescribe the user with hash suffix {hash_suffix}.")

    # I append instead of rewriting because prescriptions work like records/history.
    line = f"{doctor_name} {patient_hash} {treatment} {frequency}"
    append_file_line(PRESCRIPTIONS_FILE, line)

    print(f"Successfully saved the prescription details for user with hash suffix: {hash_suffix}.")
    return "SAVE_PRESCRIPTION_RESP::SUCCESS"

def handle_view_prescription(patient_hash: str):
    # Returns the prescription for a patient if one exists.
    hash_suffix = get_hash_suffix(patient_hash)

    print(f"The prescription server has received a request to view the prescription for the user with hash suffix: {hash_suffix}.")

    # The patient hash is the shared key between appointments and prescriptions.
    doctor_name, treatment, frequency = find_prescription(PRESCRIPTIONS_FILE, patient_hash)

    if doctor_name is None:
        print("There are no current prescriptions for this user.")
        return create_message("VIEW_PRESCRIPTION_RESP", "NOT_FOUND")

    print("A prescription exists for this user.")
    return create_message(
        "VIEW_PRESCRIPTION_RESP",
        "FOUND",
        doctor_name,
        treatment,
        frequency
    )


def main():
    # Starts the UDP Prescription Server and waits for Hospital Server requests.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        # Prescription Server listens for backend UDP requests from Hospital.
        server_socket.bind((LOCALHOST, PRESCRIPTION_PORT))

        print(f"Prescription Server is up and running using UDP on port {PRESCRIPTION_PORT}.")

        try:
            while True:
                message, addr = receive_udp(server_socket)
                # Parse the UDP message so I can choose save or view behavior.
                parts = parse_message(message)

                if not parts:
                    continue

                command = parts[0]

                # SAVE writes a prescription; VIEW reads the latest matching patient record.
                if command == "SAVE_PRESCRIPTION" and len(parts) >= 5:
                    doctor_name = parts[1]
                    patient_hash = parts[2]
                    treatment = parts[3]
                    frequency = " ".join(parts[4:])

                    response = handle_save_prescription(
                        doctor_name,
                        patient_hash,
                        treatment,
                        frequency,
                    )
                    # Send the result back to Hospital Server, not directly to the client.
                    send_udp(server_socket, response, addr[0], addr[1])

                elif command == "VIEW_PRESCRIPTION" and len(parts) == 2:
                    patient_hash = parts[1]
                    response = handle_view_prescription(patient_hash)
                    send_udp(server_socket, response, addr[0], addr[1])
        except KeyboardInterrupt:
            print("\nPrescription Server shutting down.")
        except OSError as e:
            print(f"Prescription Server error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
