# HealthNet Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-0A66C2?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Sockets](https://img.shields.io/badge/Sockets-Stdlib-0A66C2?style=flat-square&logo=python&logoColor=white)](https://docs.python.org/3/library/socket.html)
[![Tests](https://img.shields.io/github/actions/workflow/status/crisdanrodriguez/healthnet-platform/ci.yml?branch=main&label=Tests&style=flat-square&logo=githubactions&logoColor=white&color=0A66C2)](https://github.com/crisdanrodriguez/healthnet-platform/actions/workflows/ci.yml)

HealthNet Platform is a Python socket-programming project that models a small hospital system with one TCP client-facing server and three UDP backend services for authentication, appointments, and prescriptions.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Results](#results)
- [Documentation](#documentation)
- [Development](#development)
- [License](#license)
- [AI Assistance and Last Updated](#ai-assistance-and-last-updated)

## Overview

The client communicates only with the Hospital Server over TCP. The Hospital Server routes requests to backend UDP services:

```text
Client <-- TCP --> Hospital Server <-- UDP --> Backend Services
```

Backend services:

- `authentication_server.py` validates hashed credentials.
- `appointment_server.py` manages doctor lookup, scheduling, cancellation, and appointment views.
- `prescription_server.py` stores and retrieves prescription records.

The project uses only the Python standard library.

## Installation

Clone the repository and use Python 3.10 or newer:

```bash
git clone https://github.com/crisdanrodriguez/healthnet-platform.git
cd healthnet-platform
python3 --version
```

No third-party dependencies are required for runtime.

## Usage

Start each service in a separate terminal from the repository root:

```bash
python3 hospital_server.py
python3 authentication_server.py
python3 appointment_server.py
python3 prescription_server.py
```

Then start a client session:

```bash
python3 client.py AvaMitchell 'qL4@zT81'
```

Doctor demo account:

```bash
python3 client.py Dr.House 'rT8#vM42'
```

Patient commands:

```text
lookup
lookup <doctor>
schedule <doctor> <start_time> <illness>
cancel
view_appointment
view_prescription
quit
```

Doctor commands:

```text
view_appointments
prescribe <patient> <frequency>
view_prescription <patient>
quit
```

## Project Structure

```text
.
├── .github/workflows/ci.yml
├── data/
│   ├── appointments.txt
│   ├── hospital.txt
│   ├── prescriptions.txt
│   └── users.txt
├── tests/
│   └── test_core_logic.py
├── appointment_server.py
├── authentication_server.py
├── client.py
├── hospital_server.py
├── prescription_server.py
├── utils.py
├── pyproject.toml
└── README.md
```

## Results

This repository includes a runnable local demo of a distributed hospital workflow:

- patient and doctor authentication with SHA-256 credential hashes
- doctor availability lookup
- appointment scheduling and cancellation
- prescription creation and lookup

No screenshots, videos, or benchmark reports are included.

## Documentation

The source files contain concise comments around the socket flow and data ownership. Supporting data files are stored in `data/` to keep the repository root focused on executable code and project metadata.

## Development

Run the basic verification suite:

```bash
python3 -m unittest discover -s tests
python3 -m compileall appointment_server.py authentication_server.py client.py hospital_server.py prescription_server.py utils.py tests
```

The GitHub Actions workflow runs the same checks on Python 3.10, 3.11, and 3.12.

## License

This project is licensed under the terms of the [MIT License](LICENSE).

## AI Assistance and Last Updated

This repository was organized and documented with AI assistance from Codex.

Last updated: May 2026.
