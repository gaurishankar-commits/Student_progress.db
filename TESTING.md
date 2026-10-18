# Verification & Testing Report (TESTING.md)

## Student Academic Progression and Portfolio Management System
**Test Framework:** Python `unittest` & Flask Test Client  
**Execution Environment:** Windows 11 / Python 3.14 / SQLite 3.x / Flask 3.1.3

---

### 1. Test Strategy Overview

The testing methodology incorporates a dual-tier verification suite:
1. **Tier 1: Relational Database Integrity & Constraint Verification (`tests/test_database.py`)**  
   Executes schema validation on an isolated in-memory SQLite database instance with foreign key pragma enforcement (`PRAGMA foreign_keys = ON;`) to prove that SQL-level constraints, unique keys, check boundaries, and referential cascades operate reliably.
2. **Tier 2: Application Controller, Routing & Error-Handling Verification (`tests/test_app.py`)**  
   Simulates client HTTP transactions using Flask's test client, verifying complete CRUD routes, dynamic JSON payloads, CSV generation, and resilient failure handling when Google Cloud credentials are unconfigured.

---

### 2. Automated Test Execution Results

Command executed:
```powershell
python -m unittest discover -s tests -v
```

Execution Summary:
```text
test_01_dashboard_route_loads (test_app.AppRoutingAndCRUDTestCase.test_01_dashboard_route_loads)
Dashboard page loads with 200 OK and metrics. ... ok
test_02_students_directory_route (test_app.AppRoutingAndCRUDTestCase.test_02_students_directory_route)
Student directory loads and lists registered students. ... ok
test_03_create_new_student_crud (test_app.AppRoutingAndCRUDTestCase.test_03_create_new_student_crud)
Register a new student via POST /students/new. ... ok
test_04_student_profile_and_chart_data (test_app.AppRoutingAndCRUDTestCase.test_04_student_profile_and_chart_data)
Student profile page loads and includes chart JSON payload. ... ok
test_05_api_chart_data_endpoint (test_app.AppRoutingAndCRUDTestCase.test_05_api_chart_data_endpoint)
JSON API returns structured SGPA/CGPA series and labels. ... ok
test_06_csv_export_endpoint (test_app.AppRoutingAndCRUDTestCase.test_06_csv_export_endpoint)
CSV export returns text/csv with correct headers. ... ok
test_07_sync_without_credentials_does_not_crash (test_app.AppRoutingAndCRUDTestCase.test_07_sync_without_credentials_does_not_crash)
Google Sheets sync gracefully handles unconfigured state without 500 error. ... ok
test_08_healthcheck_endpoint (test_app.AppRoutingAndCRUDTestCase.test_08_healthcheck_endpoint)
Healthcheck endpoint returns healthy JSON status. ... ok
test_01_foreign_keys_pragmas_enabled (test_database.DatabaseConstraintsTestCase.test_01_foreign_keys_pragmas_enabled)
Test that foreign key enforcement is active in SQLite. ... ok
test_02_student_unique_roll_number (test_database.DatabaseConstraintsTestCase.test_02_student_unique_roll_number)
Test that duplicate student roll numbers are rejected. ... ok
test_03_student_unique_email (test_database.DatabaseConstraintsTestCase.test_03_student_unique_email)
Test that duplicate student emails are rejected. ... ok
test_04_percentage_check_constraints (test_database.DatabaseConstraintsTestCase.test_04_percentage_check_constraints)
Test that secondary/higher secondary percentages must be between 0 and 100. ... ok
test_05_semester_sgpa_cgpa_check_constraints (test_database.DatabaseConstraintsTestCase.test_05_semester_sgpa_cgpa_check_constraints)
Test that SGPA and CGPA must be between 0.0 and 10.0. ... ok
test_06_unique_student_semester_constraint (test_database.DatabaseConstraintsTestCase.test_06_unique_student_semester_constraint)
Test that a student cannot have duplicate records for the same semester. ... ok
test_07_subject_marks_obtained_cannot_exceed_max_marks (test_database.DatabaseConstraintsTestCase.test_07_subject_marks_obtained_cannot_exceed_max_marks)
Test that marks_obtained <= max_marks constraint is strictly enforced. ... ok
test_08_gap_year_chronology_constraint (test_database.DatabaseConstraintsTestCase.test_08_gap_year_chronology_constraint)
Test that gap year end_year cannot be earlier than start_year. ... ok
test_09_on_delete_cascade_referential_integrity (test_database.DatabaseConstraintsTestCase.test_09_on_delete_cascade_referential_integrity)
Test that deleting a student cascades and deletes semesters, marks, seminars, and activities. ... ok

----------------------------------------------------------------------
Ran 17 tests in 0.638s

OK
```

---

### 3. Test Cases Matrix

| Test ID | Module | Component Tested | Input / Condition | Expected Outcome | Result |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-01** | `test_database` | SQLite Foreign Keys | `PRAGMA foreign_keys;` | Value equals 1 (Enforced) | **PASS** |
| **TC-02** | `test_database` | Roll Number Uniqueness | Duplicate roll number `TEST-001` | Raises `sqlite3.IntegrityError` | **PASS** |
| **TC-03** | `test_database` | Email Uniqueness | Duplicate email `student@test.com` | Raises `sqlite3.IntegrityError` | **PASS** |
| **TC-04** | `test_database` | Percentage CHECK | Percentage `105.0%` & `-5.0%` | Raises `sqlite3.IntegrityError` | **PASS** |
| **TC-05** | `test_database` | SGPA/CGPA CHECK | SGPA `11.20` | Raises `sqlite3.IntegrityError` | **PASS** |
| **TC-06** | `test_database` | Semester Uniqueness | Duplicate Semester 1 for same student | Raises `sqlite3.IntegrityError` | **PASS** |
| **TC-07** | `test_database` | Marks Boundary CHECK | Marks obtained `110.0 / 100.0` | Raises `sqlite3.IntegrityError` | **PASS** |
| **TC-08** | `test_database` | Gap Chronology CHECK | Start year `2024`, End year `2021` | Raises `sqlite3.IntegrityError` | **PASS** |
| **TC-09** | `test_database` | Referential CASCADE | Delete parent `student(id)` | Cascades & deletes semesters, marks, seminars, activities | **PASS** |
| **TC-10** | `test_app` | Dashboard Route | GET `/` | HTTP 200, renders stat metrics | **PASS** |
| **TC-11** | `test_app` | Student Directory | GET `/students` | HTTP 200, renders directory table | **PASS** |
| **TC-12** | `test_app` | Student Enrollment CRUD | POST `/students/new` | HTTP 200 / 302, persists student record | **PASS** |
| **TC-13** | `test_app` | Student Detail Hub | GET `/students/<id>` | HTTP 200, contains Chart.js JSON | **PASS** |
| **TC-14** | `test_app` | Chart.js JSON API | GET `/api/students/<id>/chart-data` | HTTP 200, JSON labels and series | **PASS** |
| **TC-15** | `test_app` | Progression CSV Export | GET `/export/csv` | HTTP 200, Content-Type `text/csv` | **PASS** |
| **TC-16** | `test_app` | Sync Error Resilience | POST `/sync` with no credentials | HTTP 200 / 302, logs failure to `sync_log`, zero crash | **PASS** |
| **TC-17** | `test_app` | System Healthcheck | GET `/health` | HTTP 200, JSON `"status": "healthy"` | **PASS** |

---

### 4. Edge Cases Tested

1. **Attempting to input marks greater than maximum marks:**
   - Attempted: `marks_obtained = 95.0, max_marks = 50.0` in Lab exam.
   - Observed: SQLite constraint rejected operation immediately with `CHECK constraint failed: max_marks > 0.0 AND marks_obtained <= max_marks`.
2. **Attempting inverted gap year dates:**
   - Attempted: `start_year = 2024, end_year = 2022`.
   - Observed: Rejected with `CHECK constraint failed: end_year >= start_year`.
3. **Triggering Google Sheets sync without internet or credentials:**
   - Observed: The backend intercepted the missing file, recorded a `FAILED` entry into `sync_log` table with the diagnostic message, and returned a non-blocking warning notification to the GUI. The application did not terminate or crash.
