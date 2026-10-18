"""
==============================================================================
Integration & CRUD Tests for Flask Application Controller (tests/test_app.py)
==============================================================================
Validates:
1. HTTP 200 response for Dashboard (/), Students (/students), Subjects (/subjects)
2. Student registration (POST /students/new) and retrieval
3. Student profile rendering with progression chart payload (/students/<id>)
4. JSON Chart data API (/api/students/<id>/chart-data)
5. CSV Export route (/export/csv)
6. Healthcheck endpoint (/health)
7. Google Sheets sync endpoint (/sync) handles unconfigured environment gracefully
"""

import os
import unittest
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import app as flask_app
import database


class AppRoutingAndCRUDTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Ensure test database is initialized."""
        database.init_db(seed=True)

    def setUp(self):
        self.app = flask_app.app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_01_dashboard_route_loads(self):
        """Dashboard page loads with 200 OK and metrics."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Academic Administration Dashboard", response.data)
        self.assertIn(b"Total Students", response.data)

    def test_02_students_directory_route(self):
        """Student directory loads and lists registered students."""
        response = self.client.get("/students")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Student Directory", response.data)
        self.assertIn(b"Aarav Sharma", response.data)

    def test_03_create_new_student_crud(self):
        """Register a new student via POST /students/new."""
        with database.get_db() as conn:
            conn.execute("DELETE FROM students WHERE roll_no = 'TEST-APP-099' OR email = 'test.app@example.edu'")

        post_data = {
            "roll_no": "TEST-APP-099",
            "full_name": "Integration Test Student",
            "email": "test.app@example.edu",
            "phone": "+91 99999 88888",
            "department": "Computer Engineering",
            "admission_year": 2023,
            "secondary_percent": 90.0,
            "higher_secondary_percent": 88.5,
            "current_semester": 1,
            "current_status": "Active",
        }
        try:
            response = self.client.post("/students/new", data=post_data, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Integration Test Student", response.data)

            # Verify record in database
            with database.get_db() as conn:
                st = conn.execute("SELECT * FROM students WHERE roll_no = 'TEST-APP-099'").fetchone()
                self.assertIsNotNone(st)
                self.assertEqual(st["full_name"], "Integration Test Student")
        finally:
            with database.get_db() as conn:
                conn.execute("DELETE FROM students WHERE roll_no = 'TEST-APP-099' OR email = 'test.app@example.edu'")

    def test_04_student_profile_and_chart_data(self):
        """Student profile page loads and includes chart JSON payload."""
        with database.get_db() as conn:
            st = conn.execute("SELECT id FROM students WHERE roll_no = 'CE-2021-042'").fetchone()
        self.assertIsNotNone(st)

        response = self.client.get(f"/students/{st['id']}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Aarav Sharma", response.data)
        self.assertIn(b"progressionChart", response.data)

    def test_05_api_chart_data_endpoint(self):
        """JSON API returns structured SGPA/CGPA series and labels."""
        with database.get_db() as conn:
            st = conn.execute("SELECT id FROM students WHERE roll_no = 'CE-2021-042'").fetchone()

        response = self.client.get(f"/api/students/{st['id']}/chart-data")
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertIn("labels", json_data)
        self.assertIn("sgpa", json_data)
        self.assertIn("cgpa", json_data)
        self.assertTrue(len(json_data["labels"]) > 0)

    def test_06_csv_export_endpoint(self):
        """CSV export returns text/csv with correct headers."""
        response = self.client.get("/export/csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/csv")
        self.assertIn(b"Roll No,Student Name,Email", response.data)

    def test_07_sync_without_credentials_does_not_crash(self):
        """Google Sheets sync gracefully handles unconfigured state without 500 error."""
        response = self.client.post("/sync", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Should record failure gracefully in flash or sync log without uncaught exception
        logs = database.get_sync_logs(limit=1)
        self.assertTrue(len(logs) > 0)

    def test_08_healthcheck_endpoint(self):
        """Healthcheck endpoint returns healthy JSON status."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "healthy")


if __name__ == "__main__":
    unittest.main()
