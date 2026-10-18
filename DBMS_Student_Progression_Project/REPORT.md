# User & Technical Report — StudentTrack DBMS Mini-Project

## 1. Objective
To build a relational database application that records student profiles, secondary and higher-secondary marks, semester-wise SGPA/CGPA, subject and lab marks, gap years, seminars, and co-curricular/extra-curricular activities. The system offers a GUI, search, progression chart, CSV export, and optional Google Sheets synchronization.

## 2. Technology stack
- Python 3 with Flask for HTTP routes and server-side GUI.
- SQLite relational database with foreign-key enforcement.
- HTML/CSS for responsive GUI.
- Chart.js for the semester progression line chart.
- `gspread` and Google service-account credentials for optional Google Sheets integration.

## 3. Relational schema and normalization
- **Students** (`id` PK, `roll_no` UNIQUE, `full_name`, `email` UNIQUE, department, admission year, secondary %, higher-secondary %, status).
- **Semesters** (`id` PK, `student_id` FK, semester number, academic year, SGPA, CGPA); unique `(student_id, semester_no)`.
- **Subjects** (`id` PK, subject code UNIQUE, subject name, subject type).
- **Marks** (`id` PK, `semester_id` FK, `subject_id` FK, obtained marks, maximum marks); unique `(semester_id, subject_id)`.
- **ActivityTypes** (`id` PK, category UNIQUE).
- **Activities** (`id` PK, `student_id` FK, `activity_type_id` FK, title, description, date, level).
- **Seminars** (`id` PK, `student_id` FK, title, organizer type, date, certificate reference).
- **GapYears** (`id` PK, `student_id` FK, start year, end year, reason).
- **SyncLog** (`id` PK, timestamp, status, message).

The design is normalized to approximately 3NF: student profile attributes are stored once, semester facts are stored by student/semester, subject descriptions are separated from marks, and activity categories are stored separately. Many-to-one relationships use foreign keys instead of repeating profile strings. Each table has a primary key.

## 4. Constraints and error handling
- `NOT NULL` for essential fields.
- `UNIQUE` for roll number, email, subject code, activity category, student/semester and semester/subject pairs.
- Foreign keys with `ON DELETE CASCADE` for dependent records.
- `CHECK` constraints: percentages 0–100; SGPA/CGPA 0–10; semester 1–12; marks >= 0 and <= maximum; seminar and activity category allowed values; gap end year >= start year.
- If a duplicate or invalid value is submitted, the database rejects it and the interface displays an error message.

## 5. User operation guide
1. Start the app using `run_windows.bat`.
2. Open `http://127.0.0.1:5000`.
3. Search by student name or roll number. Use the form to add a student.
4. Open the student profile to add semester records and view SGPA/CGPA progression.
5. Add subjects and enter theory/lab marks against a recorded semester.
6. Add seminars with Internal/External classification.
7. Add activities with Co-curricular/Extra-curricular classification.
8. Add gap-year records to display the academic interruption indicator.
9. Export a CSV or configure the Google Sheets credentials and press Sync.

## 6. Google Sheets synchronization
The sync action exports a joined student-semester view to the spreadsheet tab named `Progression`. It uses a Google service account and spreadsheet ID supplied through local configuration. Sync overwrites the tab with a fresh database snapshot; it is intentionally one-way to prevent unvalidated spreadsheet edits from corrupting the database. It is user-triggered and requires network access and valid credentials. The current implementation does not provide two-way synchronization or automatic background sync after every write.

## 7. Known limitations / future improvements
- Authentication and role-based access are not included; use only as a local academic demo.
- Sync is button-triggered; automatic post-write sync or scheduled sync can be added.
- The marks GUI supports one subject mark per semester/subject pair. For a real institution, add exam components, credit values, grading rules and audit history.
- SQLite is suitable for a local demo; MySQL/PostgreSQL can be used for deployment.
- Delete/update controls for individual marks and portfolio entries can be added.
