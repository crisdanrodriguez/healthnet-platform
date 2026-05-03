import socket
import hashlib
from pathlib import Path
from typing import Iterable, List, Tuple


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# All servers run on this same machine for the project.
LOCALHOST = "127.0.0.1"

# Each service gets its own port so messages go to the right process.
AUTH_PORT = 21656
PRESCRIPTION_PORT = 22656
APPOINTMENT_PORT = 23656
HOSPITAL_UDP_PORT = 25656
HOSPITAL_TCP_PORT = 26656

# Used one encoding and delimiter everywhere so all servers read messages the same way.
ENCODING = "utf-8"
DELIMITER = "::"
# 4096 is much bigger than our short text messages, so it is enough for one request/response.
DEFAULT_BUFFER_SIZE = 4096

# Valid appointment time slots
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


def data_path(filename: str) -> Path:
    return DATA_DIR / filename


def sha256_hash(text: str) -> str:
    text = text.strip()
    return hashlib.sha256(text.encode(ENCODING)).hexdigest()


def get_hash_suffix(hash_text: str) -> str:
    return hash_text[-5:]


def create_message(*parts: object) -> str:
    return DELIMITER.join(str(part) for part in parts)


def parse_message(message: str) -> List[str]:
    return message.strip().split(DELIMITER)


def send_tcp(sock: socket.socket, message: str) -> None:
    sock.sendall(message.encode(ENCODING))


def receive_tcp(sock: socket.socket, buffer_size: int = DEFAULT_BUFFER_SIZE) -> str:
    data = sock.recv(buffer_size)
    return data.decode(ENCODING)


def send_udp(sock: socket.socket, message: str, host: str, port: int) -> None:
    sock.sendto(message.encode(ENCODING), (host, port))


def receive_udp(
    sock: socket.socket,
    buffer_size: int = DEFAULT_BUFFER_SIZE,
) -> Tuple[str, Tuple[str, int]]:
    data, addr = sock.recvfrom(buffer_size)
    return data.decode(ENCODING), addr


def normalize_time_slot(time_str: str) -> str:
    # Converts time inputs like "09:00" or "9:00am" into the format used by appointments.txt.
    value = time_str.strip().lower().replace(" ", "")

    # Handle optional "am"/"pm" suffixes and remove them from the value for further processing.
    period = None
    if value.endswith("am"):
        period = "am"
        value = value[:-2]
    elif value.endswith("pm"):
        period = "pm"
        value = value[:-2]

    if ":" not in value:
        return time_str.strip()

    # Validate the remaining time format and convert to 24-hour time if needed.
    hour_text, minute_text = value.split(":", 1)
    if not hour_text.isdigit() or not minute_text.isdigit():
        return time_str.strip()

    hour = int(hour_text)
    minute = int(minute_text)

    if period == "pm" and hour != 12:
        hour += 12
    elif period == "am" and hour == 12:
        hour = 0

    return f"{hour:02d}:{minute:02d}"


def is_valid_time_slot(time_str: str) -> bool:
    return normalize_time_slot(time_str) in VALID_TIME_SLOT_SET


def read_file_lines(filepath: str | Path) -> List[str]:
    # Read a data file and strip newlines so parsing is easier later.
    try:
        with open(filepath, "r", encoding=ENCODING) as file_obj:
            return [line.strip() for line in file_obj.readlines()]
    except FileNotFoundError:
        # Missing data files are treated as empty so servers do not crash at startup.
        return []


def write_file_lines(filepath: str | Path, lines: Iterable[str]) -> None:
    # Rewrite the whole file when the appointment state changes.
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding=ENCODING) as file_obj:
        for line in lines:
            file_obj.write(f"{line}\n")


def append_file_line(filepath: str | Path, line: str) -> None:
    # Append is enough for prescriptions because old records do not need to be changed.
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "a+", encoding=ENCODING) as file_obj:
        # If the file already has content but no ending newline, add one first.
        if file_obj.tell() > 0:
            file_obj.seek(file_obj.tell() - 1)
            if file_obj.read(1) != "\n":
                file_obj.write("\n")
        file_obj.write(f"{line}\n")
