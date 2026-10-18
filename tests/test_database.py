"""
==============================================================================
Unit & Integration Tests for Database Constraints & Referential Integrity
(tests/test_database.py)
==============================================================================
Validates:
1. SQLite Foreign Key Enforcement (PRAGMA foreign_keys = ON)
2. UNIQUE Constraints (Roll No, Email, Semester per Student, Subject Marks)
3. CHECK Constraints (Percentages 0-100, SGPA/CGPA 0-10, Marks <= Max, End >= Start)
4. ON DELETE CASCADE Referential Actions
"""

import os
import unittest
import sqlite3
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import database

SCHEMA_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "schema.sql"))


class DatabaseConstraintsTestCase(unittest.TestCase):
    def setUp(self):
        """Create an in-memory SQLite database using schema.sql for isolated testing."""
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")

        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            self.conn.executescript(f.read())

        # Seed categories and subjects for foreign key testing
        self.conn.execute("INSERT INTO activity_categories(name, activity_type) VALUES('Hackathon', 'Technical')")
        self.conn.execute("INSERT INTO subjects(subject_code, subject_name, subject_type) VALUES('CS101', 'Data Structures', 'Theory')")

    def tearDown(self):
        self.conn.close()

    def test_01_foreign_keys_pragmas_enabled(self):
        """Test that foreign key enforcement is active in SQLite."""
        cur = self.conn.execute("PRAGMA foreign_keys;")
        self.assertEqual(cur.fetchone()[0], 1)

    def test_02_student_unique_roll_number(self):
        """Test that duplicate student roll numbers are rejected."""
        self.conn.execute(
            """INSERT INTO students(roll_no, full_name, admission_year)
               VALUES('TEST-001', 'Student A', 2023)"""
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """INSERT INTO students(roll_no, full_name, admission_year)
                   VALUES('TEST-001', 'Student Duplicate', 2023)"""
            )

    def test_03_student_unique_email(self):
        """Test that duplicate student emails are rejected."""
        self.conn.execute(
            """INSERT INTO students(roll_no, full_name, email, admission_year)
               VALUES('TEST-002', 'Student B', 'student@test.com', 2023)"""
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """INSERT INTO students(roll_no, full_name, email, admission_year)
                   VALUES('TEST-003', 'Student C', 'student@test.com', 2023)"""
            )

    def test_04_percentage_check_constraints(self):
        """Test that secondary/higher secondary percentages must be between 0 and 100."""
        # Value > 100 should fail
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """INSERT INTO students(roll_no, full_name, admission_year, secondary_percent)
                   VALUES('TEST-004', 'Student D', 2023, 105.0)"""
            )
        # Value < 0 should fail
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """INSERT INTO students(roll_no, full_name, admission_year, higher_secondary_percent)
                   VALUES('TEST-005', 'Student E', 2023, -5.0)"""
            )

    def test_05_semester_sgpa_cgpa_check_constraints(self):
        """Test that SGPA and CGPA must be between 0.0 and 10.0."""
        cur = self.conn.execute(
            """INSERT INTO students(roll_no, full_name, admission_year)
               VALUES('TEST-006', 'Student F', 2023)"""
        )
        sid = cur.lastrowid

        # Valid SGPA/CGPA passes
        self.conn.execute(
            """INSERT INTO semesters(student_id, semester_no, academic_year, sgpa, cgpa)
               VALUES(?, 1, '2023-2024', 8.5, 8.5)""", (sid,)
        )

        # Invalid SGPA > 10 fails
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """INSERT INTO semesters(student_id, semester_no, academic_year, sgpa, cgpa)
                   VALUES(?, 2, '2023-2024', 11.2, 8.5)""", (sid,)
            )

    def test_06_unique_student_semester_constraint(self):
        """Test that a student cannot have duplicate records for the same semester."""
        cur = self.conn.execute(
            """INSERT INTO students(roll_no, full_name, admission_year)
               VALUES('TEST-007', 'Student G', 2023)"""
        )
        sid = cur.lastrowid

        self.conn.execute(
            """INSERT INTO semesters(student_id, semester_no, academic_year, sgpa, cgpa)
               VALUES(?, 1, '2023-2024', 8.0, 8.0)""", (sid,)
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """INSERT INTO semesters(student_id, semester_no, academic_year, sgpa, cgpa)
                   VALUES(?, 1, '2023-2024', 9.0, 9.0)""", (sid,)
            )

    def test_07_subject_marks_obtained_cannot_exceed_max_marks(self):
        """Test that marks_obtained <= max_marks constraint is strictly enforced."""
        cur_s = self.conn.execute("INSERT INTO students(roll_no, full_name, admission_year) VALUES('TEST-008', 'Student H', 2023)")
        sid = cur_s.lastrowid
        cur_sem = self.conn.execute("INSERT INTO semesters(student_id, semester_no, academic_year) VALUES(?, 1, '2023-2024')", (sid,))
        sem_id = cur_sem.lastrowid
        sub_id = self.conn.execute("SELECT id FROM subjects WHERE subject_code = 'CS101'").fetchone()[0]

        # 85 out of 100 is valid
        self.conn.execute(
            """INSERT INTO semester_subject_marks(semester_id, subject_id, marks_obtained, max_marks)
               VALUES(?, ?, 85.0, 100.0)""", (sem_id, sub_id)
        )

        # 110 out of 100 should fail check constraint
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """INSERT INTO semester_subject_marks(semester_id, subject_id, marks_obtained, max_marks)
                   VALUES(?, ?, 110.0, 100.0)""", (sem_id, sub_id)
            )

    def test_08_gap_year_chronology_constraint(self):
        """Test that gap year end_year cannot be earlier than start_year."""
        cur = self.conn.execute("INSERT INTO students(roll_no, full_name, admission_year) VALUES('TEST-009', 'Student I', 2021)")
        sid = cur.lastrowid

        # Valid: 2021 to 2022
        self.conn.execute(
            """INSERT INTO gap_years(student_id, start_year, end_year, reason)
               VALUES(?, 2021, 2022, 'Valid reason')""", (sid,)
        )

        # Invalid: 2024 to 2021
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """INSERT INTO gap_years(student_id, start_year, end_year, reason)
                   VALUES(?, 2024, 2021, 'Invalid chronology')""", (sid,)
            )

    def test_09_on_delete_cascade_referential_integrity(self):
        """Test that deleting a student cascades and deletes semesters, marks, seminars, and activities."""
        cur = self.conn.execute("INSERT INTO students(roll_no, full_name, admission_year) VALUES('TEST-CASCADE', 'Cascade Student', 2022)")
        sid = cur.lastrowid

        # Insert child semester & marks
        cur_sem = self.conn.execute("INSERT INTO semesters(student_id, semester_no, academic_year) VALUES(?, 1, '2022-2023')", (sid,))
        sem_id = cur_sem.lastrowid
        sub_id = self.conn.execute("SELECT id FROM subjects WHERE subject_code = 'CS101'").fetchone()[0]
        self.conn.execute("INSERT INTO semester_subject_marks(semester_id, subject_id, marks_obtained, max_marks) VALUES(?, ?, 90, 100)", (sem_id, sub_id))

        # Insert child seminar & activity
        self.conn.execute("INSERT INTO seminars(student_id, title, seminar_type, seminar_date, organizer) VALUES(?, 'Sem Test', 'Internal', '2023-01-01', 'Dept')", (sid,))
        cat_id = self.conn.execute("SELECT id FROM activity_categories LIMIT 1").fetchone()[0]
        self.conn.execute("INSERT INTO activities(student_id, category_id, activity_name, activity_date) VALUES(?, ?, 'Act Test', '2023-01-01')", (sid, cat_id))

        # Delete student
        self.conn.execute("DELETE FROM students WHERE id = ?", (sid,))

        # Verify child tables are completely cleaned up by cascade
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM semesters WHERE student_id = ?", (sid,)).fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM semester_subject_marks WHERE semester_id = ?", (sem_id,)).fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM seminars WHERE student_id = ?", (sid,)).fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM activities WHERE student_id = ?", (sid,)).fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
