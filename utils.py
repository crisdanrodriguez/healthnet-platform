import hashlib
import socket
from typing import Iterable


# =========================
# CONSTANTS
# =========================

LOCALHOST = "127.0.0.1"

AUTH_PORT = 21656
PRESCRIPTION_PORT = 22656
APPOINTMENT_PORT = 23656
HOSPITAL_UDP_PORT = 25656
HOSPITAL_TCP_PORT = 26656

ENCODING = "utf-8"
DELIMITER = "::"
DEFAULT_BUFFER_SIZE = 4096
HASH_SUFFIX_LENGTH = 5

VALID_TIME_SLOTS = (
    "09:00",
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
    """
    Return the SHA-256 hash of the input text.
    Args:
        text: The input string to hash.
    Returns:
        A hexadecimal string representing the SHA-256 hash of the input text.
    """
    text = text.strip()
    return hashlib.sha256(text.encode(ENCODING)).hexdigest()

def get_hash_suffix(hash_text: str) -> str:
    """
    Return the suffix used to display a shorter hash identifier.
    Args:
        hash_text: The full hash string.
    Returns:
        The last HASH_SUFFIX_LENGTH characters of the hash string.
    """
    return hash_text[-HASH_SUFFIX_LENGTH:]

def build_message(*parts: object) -> str:
    """
    Build a delimited message string.
    Args:
        *parts: The parts to include in the message.
    Returns:
        A delimited message string.
    """
    return DELIMITER.join(str(part) for part in parts)

def parse_message(message: str) -> list[str]:
    """
    Split a message into its fields.
    Args:
        message: The message string to split.
    Returns:
        A list of the fields in the message.
    """
    return message.strip().split(DELIMITER)

def send_tcp(sock: socket.socket, message: str) -> None:
    """
    Send a message through a connected TCP socket.
    Args:
        sock: The connected TCP socket.
        message: The message string to send.
    """
    sock.sendall(message.encode(ENCODING))

def receive_tcp(sock: socket.socket, buffer_size: int = DEFAULT_BUFFER_SIZE) -> str:
    """
    Receive and decode one TCP message.
    Args:
        sock: The connected TCP socket.
        buffer_size: The size of the buffer to use for receiving data.
    Returns:
        The decoded message string.
    """
    data = sock.recv(buffer_size)
    return data.decode(ENCODING)

def send_udp(sock: socket.socket, message: str, host: str, port: int) -> None:
    """
    Send a UDP message to the given host and port.
    Args:
        sock: The UDP socket.
        message: The message string to send.
        host: The host to send the message to.
        port: The port to send the message to.
    """
    sock.sendto(message.encode(ENCODING), (host, port))

def receive_udp(
    sock: socket.socket, 
    buffer_size: int = DEFAULT_BUFFER_SIZE,
) -> tuple[str, tuple[str, int]]:
    """
    Receive one UDP message and return the decoded payload and sender.
    Args:
        sock: The UDP socket.
        buffer_size: The size of the buffer to use for receiving data.
    Returns:
        A tuple containing the decoded message string and the sender's address (host, port)."""
    data, addr = sock.recvfrom(buffer_size)
    return data.decode(ENCODING), addr

def is_valid_time_slot(time_str: str) -> bool:
    """
    Check whether a time string is one of the allowed slots.
    Args:
        time_str: The time string to check.
    Returns:
        True if the time string is valid, False otherwise.
    """
    return time_str in VALID_TIME_SLOT_SET

def read_file_lines(filepath: str) -> list[str]:
    """
    Read a file and return its stripped lines.
    Args:
        filepath: The path to the file to read.
    Returns:
        A list of the stripped lines in the file.
    """
    try:
        with open(filepath, "r", encoding = ENCODING) as file_obj:
            return [line.strip() for line in file_obj.readlines()]
    except FileNotFoundError:
        return []

def write_file_lines(filepath: str, lines: Iterable[str]) -> None:
    """
    Overwrite a file with the provided lines.
    Args:
        filepath: The path to the file to write.
        lines: The lines to write to the file.
    """
    with open(filepath, "w", encoding = ENCODING) as file_obj:
        for line in lines:
            file_obj.write(f"{line}\n")

def append_file_line(filepath: str, line: str) -> None:
    """
    Append a single line to a file.
    Args:
        filepath: The path to the file to append to.
        line: The line to append.
    """
    with open(filepath, "a", encoding = ENCODING) as file_obj:
        file_obj.write(f"{line}\n")

def parse_appointments(filepath: str) -> dict[str, list[str]]:
    """
    Group appointment lines by doctor.
    Args:
        filepath: The path to the file containing appointment data.
    Returns:
        A dictionary mapping doctor names to lists of their appointment lines.
    """
    appointments: dict[str, list[str]] = {}
    current_doctor = None

    for line in read_file_lines(filepath):
        if not line:
            continue

        if _is_doctor_header(line):
            current_doctor = line
            appointments[current_doctor] = []
            continue

        if current_doctor is not None:
            appointments[current_doctor].append(line)

    return appointments

def write_appointments(filepath: str, data: dict[str, list[str]]) -> None:
    """
    Write grouped appointment data back to the file format used here.
    Args:
        filepath: The path to the file to write.
        data: The grouped appointment data.
    """
    lines: list[str] = []
    for doctor, slots in data.items():
        lines.append(doctor)
        lines.extend(slots)

    write_file_lines(filepath, lines)

# =========================
# PRIVATE HELPERS
# =========================

def _is_doctor_header(line: str) -> bool:
    """
    Check whether a line marks the start of a doctor's section.
    Args:
        line: The line to check.
    Returns:
        True if the line is a doctor header, False otherwise.
    """
    parts = line.split()
    return len(parts) == 1 and ":" not in parts[0]
