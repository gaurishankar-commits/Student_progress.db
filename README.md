# Student Academic Progression and Portfolio Management System

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1.3-green.svg)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite%203NF-003B57.svg)](https://sqlite.org/)
[![Bootstrap](https://img.shields.io/badge/Frontend-Bootstrap%205.3-7952B3.svg)](https://getbootstrap.com/)
[![Tests](https://img.shields.io/badge/Tests-17%20Passed-brightgreen.svg)]()

> A full-stack academic database management system built with Python Flask, SQLite (normalized to 3NF), Bootstrap 5, Chart.js, and Google Sheets integration. Designed for college faculty demonstrations and technical viva examinations.

---

## 🌟 Key Features

### 1. 3NF Normalized Relational Database
- **9 Structured Entities:** `students`, `semesters`, `subjects`, `semester_subject_marks`, `activity_categories`, `activities`, `seminars`, `gap_years`, and `sync_log`.
- **Integrity Constraints:** Strict primary keys, foreign keys with `ON DELETE CASCADE`, unique constraints (`roll_no`, `email`, student/semester pairs, semester/subject pairs), and numerical range `CHECK` constraints (percentages 0–100, SGPA/CGPA 0–10, marks obtained $\le$ max marks, gap end year $\ge$ start year).
- **SQLite Foreign Key Enforcement:** Enabled via `PRAGMA foreign_keys = ON;`.

### 2. Comprehensive Academic Progression
- **Pre-Engineering Records:** Secondary School (10th) and Higher Secondary (12th) percentages.
- **Semester History:** Semesters 1 through 8+ tracking academic years, SGPA, and cumulative CGPA.
- **Course Marks Breakdown:** Distinguishes Theory and Laboratory courses with credits, marks obtained, max marks, percentage, and grade points.
- **Gap & Drop Years:** Records study breaks with verified reasons; visually distinguishes documented gap years from missing semester records.

### 3. Dynamic Progression Visualizations (Chart.js)
- Responsive line graph plotting SGPA and CGPA across semesters on a 0.0–10.0 grade scale.
- Non-interpolating broken lines across missing semesters (`spanGaps: false`).
- Timeline markers and warning callouts for documented academic drop years.

### 4. Portfolio & Achievement Segregation
- **Seminars:** Classifies presentations as Internal (departmental) or External (conferences/symposiums) with dates, organizers, and certificate URLs.
- **Activities:** Segregates Technical & Co-curricular (hackathons, paper presentations, internships) from Extra-curricular (sports, cultural fests, leadership).
- **Department-Wide Browser:** Global portfolio explorer with category filtering and search.

### 5. Google Sheets Cloud Synchronization & CSV Export
- One-way database-to-cloud export publishing joined progression tables to Google Sheets tab `Progression`.
- Resilient error handling: missing credentials or network drops are caught, logged in `sync_log`, and reported without crashing the application.
- One-click offline CSV export for immediate spreadsheet verification.

---

## 📂 Project Structure

```text
DBMS_Student_Progression_Project/
├── app.py                  # Main Flask application controller & routes
├── database.py             # Database access layer, 3NF helpers & seed data loader
├── schema.sql              # 3NF relational schema definition with constraints & indexes
├── sheets_sync.py          # Google Sheets integration with gspread & error handling
├── requirements.txt        # Python package dependencies
├── run_windows.bat         # 1-click Windows startup batch script
├── config.example.env      # Example configuration template
├── .gitignore              # Ignores local databases, virtual environments, and secrets
├── README.md               # Quick-start documentation and guide
├── REPORT.md               # Technical report & 15 college viva questions with answers
├── ER_DIAGRAM.md           # Mermaid ER diagram and table specifications
├── TESTING.md              # Test execution log, test matrix, and verification report
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Master layout with sidebar navigation
│   ├── dashboard.html      # Overview metrics & sync status
│   ├── students.html       # Searchable student directory table
│   ├── add_student.html    # Student registration form
│   ├── student_detail.html # Progression chart & tabbed marks/portfolio
│   ├── subjects.html       # Master course catalog (Theory vs Lab)
│   ├── portfolio.html      # Department-wide activities browser
│   └── sync_hub.html       # Google Sheets connection hub & audit log
├── static/
│   ├── css/
│   │   └── style.css       # Custom academic navy/slate/teal stylesheet
│   └── js/
│       └── main.js         # Chart.js progression curve & client helpers
└── tests/
    ├── test_database.py    # Unit tests for foreign keys, constraints & CASCADE
    └── test_app.py         # Integration tests for routes, CRUD & sync resilience
```

---

## 🚀 Quick Start Guide (Windows)

### Option 1: Automatic 1-Click Launch
Double-click `run_windows.bat` in the project directory. It automatically verifies dependencies, initializes the database, and starts the server.

### Option 2: Manual Terminal Launch
1. Open PowerShell or Command Prompt in the project directory:
   ```powershell
   cd "C:\Users\Gaurishankar Yadav\Downloads\DBMS_Student_Progression_Project"
   ```
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Initialize the database with demonstration data:
   ```powershell
   python -c "import database; database.init_db(); print('Database ready.')"
   ```
4. Start the application:
   ```powershell
   python app.py
   ```
5. Open your web browser at:
   **`http://127.0.0.1:5000`**

---

## 🧪 Running Automated Tests

Run the test suite to verify database constraints, referential actions, and Flask routes:
```powershell
python -m unittest discover -s tests -v
```
*Expected Result:* All 17 tests pass (`OK`).

---

## ☁️ Google Sheets Setup (Optional)

The system is fully functional offline. To connect live Google Sheets synchronization:
1. Create a service account in [Google Cloud Console](https://console.cloud.google.com/) and enable the **Google Sheets API** and **Google Drive API**.
2. Download the service account JSON key file, rename it to `service_account.json`, and place it in the project root folder.
3. Create a blank Google Sheet, copy its ID from the URL (`/d/<ID>/edit`), and set the environment variable:
   ```powershell
   $env:GOOGLE_SHEET_ID="YOUR_SPREADSHEET_ID"
   ```
4. Share the spreadsheet with the service account client email as **Editor**.
5. Click **Sync Google Sheets** on the dashboard or visit `/sync/hub`.

---

## 🎓 Viva Preparation

Before demonstrating to faculty, review `REPORT.md` Section 12, which contains **15 likely viva questions with short, accurate answers** covering:
- 1NF, 2NF, and 3NF normalization justification
- Foreign key constraints & `ON DELETE CASCADE`
- Indexing benefits and B-Tree mechanics
- SQL query optimization with `LEFT JOIN`
- Preventing SQL injection via parameterized queries
- Handling missing data in dynamic visualizations
