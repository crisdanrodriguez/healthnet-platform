import socket
import hashlib
from typing import Iterable, List, Tuple


# =========================
# CONSTANTS
# =========================

# Host for all services
LOCALHOST = "127.0.0.1"

# Port numbers for each service
AUTH_PORT = 21656
PRESCRIPTION_PORT = 22656
APPOINTMENT_PORT = 23656
HOSPITAL_UDP_PORT = 25656
HOSPITAL_TCP_PORT = 26656

# Encoding and message formatting
ENCODING = "utf-8"
DELIMITER = "::"
DEFAULT_BUFFER_SIZE = 4096

# Valid appointment time slots
VALID_TIME_SLOTS = (
    "9:00",
    "10:00",
    "11:00",
    "12:00",
    "13:00",
    "14:00",
    "15:00",
    "16:00",
)
VALID_TIME_SLOT_SET = set(VALID_TIME_SLOTS)


# =========================
# HELPERS
# =========================

def sha256_hash(text: str) -> str:
    # Hashes a string using SHA-256.
    text = text.strip()
    return hashlib.sha256(text.encode(ENCODING)).hexdigest()

def get_hash_suffix(hash_text: str) -> str:
    # Returns only the last 5 characters of a hash for printing.
    return hash_text[-5:]

def create_message(*parts: object) -> str:
    # Creates one message string using the project delimiter.
    return DELIMITER.join(str(part) for part in parts)

def parse_message(message: str) -> List[str]:
    # Splits a received message back into its parts.
    return message.strip().split(DELIMITER)

def send_tcp(sock: socket.socket, message: str) -> None:
    # Sends a string message through a TCP socket.
    sock.sendall(message.encode(ENCODING))

def receive_tcp(sock: socket.socket, buffer_size: int = DEFAULT_BUFFER_SIZE) -> str:
    # Receives one TCP message and converts it back to a string.
    data = sock.recv(buffer_size)
    return data.decode(ENCODING)

def send_udp(sock: socket.socket, message: str, host: str, port: int) -> None:
    # Sends one UDP message to a specific server port.
    sock.sendto(message.encode(ENCODING), (host, port))

def receive_udp(
    sock: socket.socket, 
    buffer_size: int = DEFAULT_BUFFER_SIZE,
) -> Tuple[str, Tuple[str, int]]:
    # Receives one UDP message and also returns who sent it.
    data, addr = sock.recvfrom(buffer_size)
    return data.decode(ENCODING), addr

def normalize_time_slot(time_str: str) -> str:
    # Converts time inputs like "09:00" or "9:00am" into the format used by appointments.txt.
    value = time_str.strip().lower().replace(" ", "")

    period = None
    if value.endswith("am"):
        period = "am"
        value = value[:-2]
    elif value.endswith("pm"):
        period = "pm"
        value = value[:-2]

    if ":" not in value:
        return time_str.strip()

    hour_text, minute_text = value.split(":", 1)
    if not hour_text.isdigit() or not minute_text.isdigit():
        return time_str.strip()

    hour = int(hour_text)
    minute = int(minute_text)

    if period == "pm" and hour != 12:
        hour += 12
    elif period == "am" and hour == 12:
        hour = 0

    return f"{hour}:{minute:02d}"

def is_valid_time_slot(time_str: str) -> bool:
    # Checks if the requested time is one of the allowed appointment times.
    return normalize_time_slot(time_str) in VALID_TIME_SLOT_SET

def read_file_lines(filepath: str) -> List[str]:
    # Reads all lines from a text file.
    try:
        with open(filepath, "r", encoding = ENCODING) as file_obj:
            return [line.strip() for line in file_obj.readlines()]
    except FileNotFoundError:
        # Missing data files are treated as empty so servers do not crash at startup.
        return []

def write_file_lines(filepath: str, lines: Iterable[str]) -> None:
    # Writes a list of lines to a file.
    with open(filepath, "w", encoding = ENCODING) as file_obj:
        for line in lines:
            file_obj.write(f"{line}\n")

def append_file_line(filepath: str, line: str) -> None:
    # Adds one line at the end of a file.
    with open(filepath, "a", encoding = ENCODING) as file_obj:
        file_obj.write(f"{line}\n")
