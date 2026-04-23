import sys
import socket
from utils import *

# Approach: Authentication Server is a backend UDP service.
# It only verifies hashed credentials sent by Hospital Server.


USERS_FILE = "users.txt"


def load_users(filepath: str) -> set:
    # Loads all valid hashed username/password pairs from users.txt.
    users = set()
    lines = read_file_lines(filepath)

    for line in lines:
        parts = line.split()
        if len(parts) == 2:
            # users.txt stores pre-hashed username/password pairs.
            username_hash, password_hash = parts
            users.add((username_hash, password_hash))

    return users

def authenticate(users, username_hash: str, password_hash: str) -> bool:
    # Checks if this exact username hash and password hash exist in the users set.
    return (username_hash, password_hash) in users


def main():
    # Starts the UDP authentication server and waits for requests from Hospital Server.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        # Authentication is a backend service, so it listens for UDP from Hospital.
        server_socket.bind((LOCALHOST, AUTH_PORT))

        print(f"Authentication Server is up and running using UDP on port {AUTH_PORT}.")

        users = load_users(USERS_FILE)

        try:
            while True:
                message, addr = receive_udp(server_socket)
                parts = parse_message(message)

                if not parts:
                    continue

                command = parts[0]

                if command != "AUTH" or len(parts) != 3:
                    # Ignore malformed backend messages instead of stopping the server.
                    continue

                username_hash = parts[1]
                password_hash = parts[2]
                hash_suffix = get_hash_suffix(username_hash)

                print(
                    f"Authentication Server has received an authentication request for a user with hash suffix: {hash_suffix}."
                )

                # A valid login must match the exact username hash and password hash.
                if authenticate(users, username_hash, password_hash):
                    print(f"Authentication succeeded for a user with hash suffix: {hash_suffix}.")
                    response = "AUTH_OK"
                else:
                    print(f"Authentication failed for a user with hash suffix: {hash_suffix}.")
                    response = "AUTH_FAIL"

                send_udp(server_socket, response, addr[0], addr[1])

                print("The Authentication Server has sent the authentication result to the Hospital Server.")
        except KeyboardInterrupt:
            print("\nAuthentication Server shutting down.")
        except OSError as e:
            print(f"Authentication Server error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
