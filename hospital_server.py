import socket
from utils import *


HOSPITAL_FILE = "hospital.txt"
BACKLOG = 5


def load_doctor_hashes(filepath: str) -> set:
    """
    Reads hospital.txt and returns a set with all doctor username hashes
    from the [Doctors] section.
    Expected format:
    [Doctors]
    <doctor_name> <hashed_doctor_name>
    ...
    [Treatments]
    ...
    Args:
        filepath: The path to the hospital file.
    Returns:
        A set of doctor username hashes.
    """
    doctor_hashes = set()
    lines = read_file_lines(filepath)

    in_doctors_section = False

    for line in lines:
        if not line:
            continue

        if line == "[Doctors]":
            in_doctors_section = True
            continue

        if line == "[Treatments]":
            in_doctors_section = False
            continue

        if in_doctors_section:
            parts = line.split()
            if len(parts) == 2:
                doctor_name, doctor_hash = parts
                doctor_hashes.add(doctor_hash)

    return doctor_hashes

def determine_role(username_hash: str, doctor_hashes) -> str:
    """Determines the role of a user based on their username hash.
    Args:     
        username_hash: The hashed username of the user.
        doctor_hashes: A set of doctor username hashes.
    Returns:
        "doctor" if the user is a doctor, "patient" otherwise.
    """
    if username_hash in doctor_hashes:
        return "doctor"
    return "patient"

def handle_auth_request(client_message: str, udp_socket: socket.socket) -> str:
    """
    Handles an authentication request from a client.
    Expects a message in the format:
    AUTH|<username_hash>|<password_hash>
    Args:     
        client_message: The authentication request message from the client.
        udp_socket: The UDP socket to communicate with the Authentication Server.
    Returns:
        A response message to send back to the client, either "AUTH_OK|<role>" or "AUTH_FAIL".
    """
    parts = parse_message(client_message)

    if len(parts) != 3 or parts[0] != "AUTH":
        return "AUTH_FAIL"

    username_hash = parts[1]
    password_hash = parts[2]
    hash_suffix = get_hash_suffix(username_hash)

    print(
        f"Hospital Server received an authentication request from a user with hash suffix {hash_suffix}."
    )

    auth_message = build_message("AUTH", username_hash, password_hash)
    send_udp(udp_socket, auth_message, LOCALHOST, AUTH_PORT)

    print("Hospital Server has sent an authentication request to the Authentication Server.")

    auth_response, _ = receive_udp(udp_socket)

    print(f"Hospital server has received the response from the authentication server using UDP over port {HOSPITAL_UDP_PORT}.")

    if auth_response == "AUTH_OK":
        print(f"User with a hash suffix {hash_suffix} has been granted access to the system. Determining the access of the user.")

        doctor_hashes = load_doctor_hashes(HOSPITAL_FILE)
        role = determine_role(username_hash, doctor_hashes)

        if role == "doctor":
            print(f"User with hash suffix {hash_suffix} will be granted doctor access.")
        else:
            print(f"User with hash {hash_suffix} will be granted patient access.")

        return build_message("AUTH_OK", role)

    return "AUTH_FAIL"

def get_doctor_list(filepath: str) -> list:
    """Reads hospital.txt and returns a list of doctor names from the [Doctors] section.    
    Expected format:
    [Doctors]
    <doctor_name> <hashed_doctor_name>
    ...
    [Treatments]
    ...
    Args:
        filepath: The path to the hospital file.
    Returns:
        A list of doctor names.
    """
    doctors = []
    lines = read_file_lines(filepath)

    in_doctors = False

    for line in lines:
        if line == "[Doctors]":
            in_doctors = True
            continue

        if line == "[Treatments]":
            break

        if in_doctors:
            parts = line.split()
            if len(parts) == 2:
                doctor_name = parts[0]
                doctors.append(doctor_name)

    return doctors


def main():
    # UDP socket for backend communication
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((LOCALHOST, HOSPITAL_UDP_PORT))

    # TCP socket for client connections
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_socket.bind((LOCALHOST, HOSPITAL_TCP_PORT))
    tcp_socket.listen(BACKLOG)

    print(f"Hospital Server is up and running using UDP on port {HOSPITAL_UDP_PORT}.")

    while True:
        conn, addr = tcp_socket.accept()

        try:
            message = receive_tcp(conn)
            if not message:
                conn.close()
                continue

            parts = parse_message(message)
            if not parts:
                conn.close()
                continue

            command = parts[0]

            if command == "AUTH":
                response = handle_auth_request(message, udp_socket)

                send_tcp(conn, response)

                print(
                    f"Hospital Server has sent the response from Authentication Server to the client using TCP over port {HOSPITAL_TCP_PORT}."
                )

            elif command == "LOOKUP":
                username_hash = parts[1]
                suffix = get_hash_suffix(username_hash)

                print(
                    f"Hospital Server received a lookup request from a user with a hash suffix {suffix} over port {HOSPITAL_TCP_PORT}."
                )

                doctors = get_doctor_list(HOSPITAL_FILE)

                print("Hospital Server sent the doctor lookup request to the Appointment server.")

                print(
                    f"Hospital Server has received the response from Appointment Server using UDP over port {HOSPITAL_UDP_PORT}."
                )

                response_text = "The following doctors are available:\n"
                for d in doctors:
                    response_text += f"{d}\n"

                send_tcp(conn, response_text.strip())

                print("Hospital Server has sent the doctor lookup to the client.")


            else:
                send_tcp(conn, "UNSUPPORTED")

        finally:
            conn.close()


if __name__ == "__main__":
    main()