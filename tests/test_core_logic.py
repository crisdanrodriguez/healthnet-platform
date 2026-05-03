import tempfile
import unittest
from pathlib import Path

from appointment_server import (
    get_available_slots,
    load_appointments,
    schedule_appointment,
)
from authentication_server import authenticate, load_users
from hospital_server import determine_role, get_treatment_for_illness
from utils import (
    create_message,
    is_valid_time_slot,
    normalize_time_slot,
    parse_message,
    sha256_hash,
    write_file_lines,
)


class UtilsTests(unittest.TestCase):
    def test_message_round_trip(self):
        message = create_message("AUTH", "user_hash", "password_hash")

        self.assertEqual(parse_message(message), ["AUTH", "user_hash", "password_hash"])

    def test_time_slot_normalization(self):
        self.assertEqual(normalize_time_slot("9:00am"), "09:00")
        self.assertEqual(normalize_time_slot("1:00pm"), "13:00")
        self.assertTrue(is_valid_time_slot("09:00"))
        self.assertFalse(is_valid_time_slot("8:30"))

    def test_sha256_hash_strips_input(self):
        self.assertEqual(sha256_hash("AvaMitchell"), sha256_hash(" AvaMitchell "))


class AuthenticationTests(unittest.TestCase):
    def test_load_and_authenticate_user(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            users_file = Path(temp_dir) / "users.txt"
            write_file_lines(users_file, ["user_hash password_hash"])

            users = load_users(users_file)

        self.assertTrue(authenticate(users, "user_hash", "password_hash"))
        self.assertFalse(authenticate(users, "user_hash", "wrong_password_hash"))


class AppointmentTests(unittest.TestCase):
    def test_schedule_appointment_marks_slot_as_booked(self):
        appointments = {"Dr.House": ["9:00", "10:00"]}

        status, available_slots = schedule_appointment(
            appointments,
            "Dr.House",
            "9:00",
            "patient_hash",
            "Flu",
        )

        self.assertEqual(status, "SUCCESS")
        self.assertIsNone(available_slots)
        self.assertEqual(appointments["Dr.House"][0], "9:00 patient_hash Flu")

    def test_load_appointments_groups_doctors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            appointments_file = Path(temp_dir) / "appointments.txt"
            write_file_lines(appointments_file, ["Dr.House", "9:00", "10:00 patient Flu"])

            appointments = load_appointments(appointments_file)

        self.assertEqual(get_available_slots(appointments, "Dr.House"), ["9:00"])


class HospitalTests(unittest.TestCase):
    def test_determine_role(self):
        self.assertEqual(determine_role("doctor_hash", {"doctor_hash"}), "doctor")
        self.assertEqual(determine_role("patient_hash", {"doctor_hash"}), "patient")

    def test_get_treatment_for_illness(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            hospital_file = Path(temp_dir) / "hospital.txt"
            write_file_lines(
                hospital_file,
                ["[Doctors]", "Dr.House doctor_hash", "[Treatments]", "Flu Antivirals"],
            )

            treatment = get_treatment_for_illness(hospital_file, "Flu")

        self.assertEqual(treatment, "Antivirals")


if __name__ == "__main__":
    unittest.main()
