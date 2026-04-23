import socket
from utils import *

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 🔁 cambia por valores reales
    username = "LiamCarter"
    password = "Xf7dkP92 "

    user_hash = sha256_hash(username)
    pass_hash = sha256_hash(password)

    msg = build_message("AUTH", user_hash, pass_hash)

    send_udp(sock, msg, LOCALHOST, AUTH_PORT)

    response, _ = receive_udp(sock)

    print("Response from auth server:", response)


if __name__ == "__main__":
    main()