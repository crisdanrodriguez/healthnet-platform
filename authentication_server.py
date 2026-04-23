import socket
from utils import *


USERS_FILE = "users.txt"


def load_users(filepath: str) -> set:
    """
    Loads valid (username_hash, password_hash) pairs from users.txt.
    Expected format per line:
        <hashed_username> <hashed_password>
    Args:
        filepath: The path to the users file.
    """
    users = set()
    lines = read_file_lines(filepath)

    for line in lines:
        parts = line.split()
        if len(parts) == 2:
            username_hash, password_hash = parts
            users.add((username_hash, password_hash))

    return users

def authenticate(users, username_hash: str, password_hash: str) -> bool:
    """Check if the provided username and password hashes match any valid user.
    Args:
        users: A set of valid (username_hash, password_hash) pairs.
        username_hash: The hashed username to authenticate.
        password_hash: The hashed password to authenticate.
    Returns:
        True if the credentials are valid, False otherwise.
    """
    return (username_hash, password_hash) in users

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((LOCALHOST, AUTH_PORT))

    print(f"Authentication Server is up and running using UDP on port {AUTH_PORT}.")

    users = load_users(USERS_FILE)

    while True:
        message, addr = receive_udp(server_socket)
        parts = parse_message(message)

        if not parts:
            continue

        command = parts[0]

        if command != "AUTH" or len(parts) != 3:
            continue

        username_hash = parts[1]
        password_hash = parts[2]
        hash_suffix = get_hash_suffix(username_hash)

        print(
            f"Authentication Server has received an authentication request for a user with hash suffix: {hash_suffix}."
        )

        if authenticate(users, username_hash, password_hash):
            print(f"Authentication succeeded for a user with hash suffix: {hash_suffix}.")
            response = "AUTH_OK"
        else:
            print(f"Authentication failed for a user with hash suffix: {hash_suffix}.")
            response = "AUTH_FAIL"

        send_udp(server_socket, response, addr[0], addr[1])

        print("The Authentication Server has sent the authentication result to the Hospital Server.")


if __name__ == "__main__":
    main()