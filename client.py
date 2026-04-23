import sys
import socket
from utils import *


def authenticate_user(username: str, password: str) -> dict:
    """
    Sends authentication request to Hospital Server using TCP.

    Request format:
        AUTH::<username_hash>::<password_hash>

    Response format:
        AUTH_OK::doctor
        AUTH_OK::patient
        AUTH_FAIL
    """
    username_hash = sha256_hash(username)
    password_hash = sha256_hash(password)

    message = build_message("AUTH", username_hash, password_hash)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((LOCALHOST, HOSPITAL_TCP_PORT))

        print("The client is up and running.")
        print(f"{username} sent an authentication request to the hospital server.")

        send_tcp(client_socket, message)

        response = receive_tcp(client_socket)
        parts = parse_message(response)

        if not parts:
            print("The credentials are incorrect. Please try again.")
            return None

        if parts[0] == "AUTH_FAIL":
            print("The credentials are incorrect. Please try again.")
            return None

        if parts[0] == "AUTH_OK" and len(parts) == 2:
            role = parts[1]

            if role == "patient":
                print(
                    f"{username} received the authentication result. Authentication successful. You have been granted patient access."
                )
                return {
                    "username": username,
                    "username_hash": username_hash,
                    "role": "patient",
                }

            if role == "doctor":
                print(
                    f"{username} received the authentication result. Authentication successful. You have been granted doctor access."
                )
                return {
                    "username": username,
                    "username_hash": username_hash,
                    "role": "doctor",
                }

        print("The credentials are incorrect. Please try again.")
        return None

def print_help(role: str) -> None:
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

def command_loop(user_info) -> None:
    """
    For now this loop only supports:
        help
        quit
        lookup

    We will later extend it with:
        schedule
        cancel
        view_appointment
        view_prescription
        etc.
    """
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

        elif command == "lookup":
            msg = build_message("LOOKUP", user_info["username_hash"])

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((LOCALHOST, HOSPITAL_TCP_PORT))

                print(f"{user_info['username']} sent a lookup request to the hospital server.")

                send_tcp(sock, msg)

                response = receive_tcp(sock)
                print(response)

        elif command == "quit":
            print("You have successfully been logged out.")
            break

        else:
            print_help(role)

def main():
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