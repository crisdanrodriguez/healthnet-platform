**Name:** Cristian Daniel Rodriguez Vazquez  
**USC ID:** [Your USC ID]

## What This Project Does

This is my socket programming project for a small hospital system.

I split the system into a client, one main Hospital Server, and three backend servers:

- `client.py`
- `hospital_server.py`
- `authentication_server.py`
- `appointment_server.py`
- `prescription_server.py`

The client only talks to the Hospital Server. Then the Hospital Server talks to the other servers depending on what the user wants to do.

## Main Idea

I used TCP between the client and the Hospital Server because the client sends a command and waits for a direct response.

I used UDP between the Hospital Server and the backend servers because those messages are smaller internal requests.

```text
Client <--TCP--> Hospital Server <--UDP--> Backend Servers
```

Backend servers:

```text
Authentication Server
Appointment Server
Prescription Server
```

## Files

| File | What I Use It For |
| --- | --- |
| `client.py` | Runs the user side. It logs in and lets the user type commands. |
| `hospital_server.py` | Main middle server. It receives client requests and sends them to the right backend server. |
| `authentication_server.py` | Checks if the username/password hashes are valid. |
| `appointment_server.py` | Handles lookup, schedule, cancel, and appointment views. |
| `prescription_server.py` | Saves and returns prescription information. |
| `utils.py` | Shared helper functions for sockets, hashing, files, and messages. |
| `users.txt` | Has hashed username/password pairs. |
| `hospital.txt` | Has doctor hashes and treatment data. |
| `appointments.txt` | Has doctor schedules. |
| `prescriptions.txt` | Has prescription records. |
| `original.txt` | Plain usernames/passwords used for testing. |

## Message Format

I used `::` as the separator for messages.

Some examples:

```text
AUTH::<username_hash>::<password_hash>
LOOKUP::<user_hash>
LOOKUP_DOCTOR::<user_hash>::<doctor_name>
SCHEDULE::<patient_hash>::<doctor_name>::<time>::<illness>
```

Some responses look like:

```text
AUTH_OK::patient
AUTH_OK::doctor
AUTH_FAIL
SCHEDULE_RESP::SUCCESS::<doctor_name>::<time>
```

## How To Run

There is no Makefile for this project, so run everything directly with `python3`.

Use separate terminals for each server.

Start the servers in this order:

### 1. Authentication Server

```bash
python3 authentication_server.py
```

### 2. Appointment Server

```bash
python3 appointment_server.py
```

### 3. Prescription Server

```bash
python3 prescription_server.py
```

### 4. Hospital Server

```bash
python3 hospital_server.py
```

### 5. Client

```bash
python3 client.py <username> <password>
```

Example patient:

```bash
python3 client.py AvaMitchell qL4@zT81
```

Example doctor:

```bash
python3 client.py Dr.House 'rT8#vM42'
```

I put quotes around the doctor password because it has `#`, and the shell can treat that as a comment.

## Commands

After logging in, the commands depend on whether the user is a patient or a doctor.

### Patient

```text
lookup
lookup <doctor>
schedule <doctor> <start_time> <illness>
cancel
view_appointment
view_prescription
quit
```

Example:

```text
lookup
lookup Dr.House
schedule Dr.House 9:00 Flu
view_appointment
cancel
quit
```

For appointment times, I allow formats like:

```text
9:00
09:00
9:00am
```

### Doctor

```text
view_appointments
prescribe <patient> <frequency>
view_prescription <patient>
quit
```

Example:

```text
view_appointments
prescribe AvaMitchell Daily
view_prescription AvaMitchell
quit
```

## Notes

- All `.txt` files should stay in the same folder as the Python files.
- I hash usernames and passwords with SHA-256.
- The client sends hashes, not plain text credentials.
- The Hospital Server is the only server the client talks to directly.
- The backend servers only talk to the Hospital Server.
- When a doctor prescribes something, I clear that appointment slot.
- If the prescription frequency is `None`, I treat it as no active prescription.

## Testing Environment

I tested this with Python 3 on Ubuntu/Linux.

No extra packages are needed.

## TA Example Code

I followed the socket style from the TA examples:

- `stream_server.py` for TCP
- `datagram_server.py` for UDP

The rest of the project logic was written for this assignment.
