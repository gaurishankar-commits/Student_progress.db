"""
==============================================================================
Student Academic Progression and Portfolio Management System
Database Access Layer & 3NF Query Helpers (database.py)
Supports SQLite and MySQL seamlessly with automatic failover/fallback.
==============================================================================
"""

import os
import sqlite3
from datetime import datetime

try:
    import pymysql
    import pymysql.cursors
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.environ.get("VERCEL"):
    import shutil
    DB_PATH = "/tmp/student_progression.db"
    orig_db = os.path.join(BASE_DIR, "student_progression.db")
    if not os.path.exists(DB_PATH) and os.path.exists(orig_db):
        try:
            shutil.copy2(orig_db, DB_PATH)
        except Exception:
            pass
else:
    DB_PATH = os.path.join(BASE_DIR, "student_progression.db")

SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")

# Load simple key-value .env file if present
ENV_PATH = os.path.join(BASE_DIR, ".env")
if os.path.exists(ENV_PATH):
    try:
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip()
                    if k not in os.environ:
                        os.environ[k] = v
    except Exception:
        pass

# Database Engine Configuration - defaults safely to sqlite
DB_BACKEND = os.environ.get("DB_BACKEND", "sqlite").lower()
DB_NAME = os.environ.get("DB_NAME", "astudent_progress")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 3306))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "Gauri@2026")


class DBConnectionWrapper:
    """
    Unified database connection wrapper that normalizes SQLite and MySQL interfaces:
    - Provides execute(sql, params) and executescript(sql)
    - Returns rows accessible both by column name and by integer index
    - Normalizes SQL parameter placeholder from '?' to '%s' when on MySQL
    - Provides lastrowid and commit/rollback context management
    """
    def __init__(self, raw_conn, is_mysql=False):
        self.raw_conn = raw_conn
        self.is_mysql = is_mysql
        self.lastrowid = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            if hasattr(self.raw_conn, "rollback"):
                self.raw_conn.rollback()
        else:
            if hasattr(self.raw_conn, "commit"):
                self.raw_conn.commit()
        if hasattr(self.raw_conn, "close"):
            self.raw_conn.close()

    def _prepare_sql(self, sql):
        if self.is_mysql:
            # Replace SQLite ? with MySQL %s
            sql = sql.replace("?", "%s")
            # Replace SQLite concat operator with MySQL CONCAT where applicable
            # SQLite: start_year || '-' || end_year
            if "start_year ||" in sql:
                sql = sql.replace(
                    "start_year || '-' || end_year || ' (' || gap_type || ': ' || reason || ')'",
                    "CONCAT(start_year, '-', end_year, ' (', gap_type, ': ', reason, ')')"
                )
        return sql

    def execute(self, sql, params=None):
        sql = self._prepare_sql(sql)
        params = params or ()
        if self.is_mysql:
            cur = self.raw_conn.cursor()
            cur.execute(sql, params)
            self.lastrowid = cur.lastrowid
            return DBCursorWrapper(cur, is_mysql=True, lastrowid=cur.lastrowid)
        else:
            cur = self.raw_conn.execute(sql, params)
            self.lastrowid = cur.lastrowid
            return DBCursorWrapper(cur, is_mysql=False, lastrowid=cur.lastrowid)

    def executemany(self, sql, seq_of_params):
        sql = self._prepare_sql(sql)
        if self.is_mysql:
            cur = self.raw_conn.cursor()
            cur.executemany(sql, seq_of_params)
            self.lastrowid = cur.lastrowid
            return DBCursorWrapper(cur, is_mysql=True, lastrowid=cur.lastrowid)
        else:
            cur = self.raw_conn.executemany(sql, seq_of_params)
            self.lastrowid = cur.lastrowid
            return DBCursorWrapper(cur, is_mysql=False, lastrowid=cur.lastrowid)

    def executescript(self, script):
        if self.is_mysql:
            # Split and execute statement by statement
            cur = self.raw_conn.cursor()
            statements = script.split(";")
            for stmt in statements:
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)
        else:
            self.raw_conn.executescript(script)


class DBRowWrapper:
    """Row wrapper that supports dict-like key access and list-like index access."""
    def __init__(self, data_dict):
        self._data = data_dict or {}
        self._keys = list(self._data.keys())
        self._values = list(self._data.values())

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._data.get(key)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def keys(self):
        return self._keys

    def values(self):
        return self._values

    def items(self):
        return self._data.items()

    def __contains__(self, key):
        return key in self._data

    def __repr__(self):
        return repr(self._data)


class DBCursorWrapper:
    def __init__(self, raw_cur, is_mysql=False, lastrowid=None):
        self.raw_cur = raw_cur
        self.is_mysql = is_mysql
        self.lastrowid = lastrowid

    def fetchone(self):
        row = self.raw_cur.fetchone()
        if row is None:
            return None
        if self.is_mysql:
            return DBRowWrapper(row)
        return row

    def fetchall(self):
        rows = self.raw_cur.fetchall()
        if self.is_mysql:
            return [DBRowWrapper(r) for r in rows]
        return rows


def get_db():
    """
    Establish and return a connection based on configured DB_BACKEND.
    Falls back gracefully to SQLite if MySQL connection fails.
    """
    global DB_BACKEND
    if DB_BACKEND == "mysql" and HAS_PYMYSQL:
        try:
            conn = pymysql.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                autocommit=False,
                cursorclass=pymysql.cursors.DictCursor
            )
            return DBConnectionWrapper(conn, is_mysql=True)
        except Exception as e:
            print(f"[database.py] MySQL connection failed ({e}). Falling back to SQLite.")

    # SQLite connection
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return DBConnectionWrapper(conn, is_mysql=False)


def is_using_mysql():
    """Returns True if MySQL is active, False for SQLite."""
    try:
        with get_db() as conn:
            return conn.is_mysql
    except Exception:
        return False


def init_db(seed=True):
    """
    Initialize database schema (MySQL or SQLite) and seed sample demonstration data if empty.
    """
    with get_db() as conn:
        if conn.is_mysql:
            # Create MySQL tables with proper types and FKs
            conn.execute("SET FOREIGN_KEY_CHECKS = 0;")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INT AUTO_INCREMENT PRIMARY KEY,
                roll_no VARCHAR(50) NOT NULL UNIQUE,
                full_name VARCHAR(150) NOT NULL,
                email VARCHAR(150) UNIQUE,
                phone VARCHAR(50),
                department VARCHAR(100) NOT NULL DEFAULT 'Computer Engineering',
                admission_year INT NOT NULL,
                secondary_percent DOUBLE,
                higher_secondary_percent DOUBLE,
                current_semester INT DEFAULT 1,
                current_status VARCHAR(50) NOT NULL DEFAULT 'Active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS semesters (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                semester_no INT NOT NULL,
                academic_year VARCHAR(50) NOT NULL,
                sgpa DOUBLE,
                cgpa DOUBLE,
                status VARCHAR(50) NOT NULL DEFAULT 'Completed',
                remarks TEXT,
                UNIQUE KEY uq_student_sem (student_id, semester_no),
                CONSTRAINT fk_sem_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
            ) ENGINE=InnoDB;
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INT AUTO_INCREMENT PRIMARY KEY,
                subject_code VARCHAR(50) NOT NULL UNIQUE,
                subject_name VARCHAR(150) NOT NULL,
                subject_type ENUM('Theory', 'Lab') NOT NULL,
                credits INT NOT NULL DEFAULT 3,
                default_max_marks DOUBLE NOT NULL DEFAULT 100.0
            ) ENGINE=InnoDB;
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS semester_subject_marks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                semester_id INT NOT NULL,
                subject_id INT NOT NULL,
                marks_obtained DOUBLE NOT NULL,
                max_marks DOUBLE NOT NULL,
                grade_point DOUBLE,
                UNIQUE KEY uq_sem_sub (semester_id, subject_id),
                CONSTRAINT fk_mark_sem FOREIGN KEY (semester_id) REFERENCES semesters(id) ON DELETE CASCADE,
                CONSTRAINT fk_mark_sub FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            ) ENGINE=InnoDB;
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS activity_categories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(150) NOT NULL UNIQUE,
                activity_type ENUM('Technical', 'Co-curricular', 'Extra-curricular') NOT NULL
            ) ENGINE=InnoDB;
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                category_id INT NOT NULL,
                activity_name VARCHAR(200) NOT NULL,
                description TEXT,
                activity_date VARCHAR(50) NOT NULL,
                achievement_level VARCHAR(100) DEFAULT 'Participant',
                certificate_ref VARCHAR(200),
                CONSTRAINT fk_act_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                CONSTRAINT fk_act_cat FOREIGN KEY (category_id) REFERENCES activity_categories(id)
            ) ENGINE=InnoDB;
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS seminars (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                title VARCHAR(250) NOT NULL,
                seminar_type ENUM('Internal', 'External') NOT NULL,
                seminar_date VARCHAR(50) NOT NULL,
                organizer VARCHAR(200) NOT NULL,
                certificate_url TEXT,
                CONSTRAINT fk_sem_stud FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
            ) ENGINE=InnoDB;
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS gap_years (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                start_year INT NOT NULL,
                end_year INT NOT NULL,
                gap_type VARCHAR(100) DEFAULT 'Academic Drop',
                reason TEXT NOT NULL,
                CONSTRAINT fk_gap_stud FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
            ) ENGINE=InnoDB;
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                synced_at VARCHAR(50) NOT NULL,
                sync_type VARCHAR(50) NOT NULL DEFAULT 'Manual',
                status VARCHAR(50) NOT NULL,
                records_synced INT NOT NULL DEFAULT 0,
                message TEXT
            ) ENGINE=InnoDB;
            """)
            conn.execute("SET FOREIGN_KEY_CHECKS = 1;")
        else:
            with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)

        # Seed categories if missing
        cats = [
            ("Coding Contest & Hackathon", "Technical"),
            ("Research Paper Presentation", "Technical"),
            ("Robotics & IoT Projects", "Technical"),
            ("Technical Workshop & Seminar", "Technical"),
            ("Industry Internship", "Co-curricular"),
            ("Project Exhibition", "Co-curricular"),
            ("Tech Symposium & Quiz", "Co-curricular"),
            ("Open Source Contribution", "Co-curricular"),
            ("Sports & Athletics", "Extra-curricular"),
            ("Cultural Fest & Performing Arts", "Extra-curricular"),
            ("Debate & Literary Events", "Extra-curricular"),
            ("Student Council & Leadership", "Extra-curricular"),
            ("Social Volunteering & NSS", "Extra-curricular"),
        ]
        insert_cat_sql = "INSERT IGNORE INTO activity_categories(name, activity_type) VALUES(?, ?)" if conn.is_mysql else "INSERT OR IGNORE INTO activity_categories(name, activity_type) VALUES(?, ?)"
        for name, ctype in cats:
            conn.execute(insert_cat_sql, (name, ctype))

        # Seed master subjects if empty
        sub_count = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
        if sub_count == 0:
            subjects = [
                ("CS101", "Data Structures & Algorithms", "Theory", 4, 100.0),
                ("CS102", "Data Structures Laboratory", "Lab", 2, 50.0),
                ("CS201", "Database Management Systems", "Theory", 4, 100.0),
                ("CS202", "Database Systems Laboratory", "Lab", 2, 50.0),
                ("CS301", "Operating Systems", "Theory", 4, 100.0),
                ("CS302", "Operating Systems Laboratory", "Lab", 2, 50.0),
                ("CS401", "Computer Networks", "Theory", 4, 100.0),
                ("CS402", "Network & Security Laboratory", "Lab", 2, 50.0),
                ("CS501", "Software Engineering & Agile", "Theory", 3, 100.0),
                ("CS502", "Web Technologies Laboratory", "Lab", 2, 50.0),
                ("CS601", "Cloud Computing & Distributed Systems", "Theory", 4, 100.0),
                ("CS602", "Cloud Computing Laboratory", "Lab", 2, 50.0),
                ("CS701", "Artificial Intelligence & Machine Learning", "Theory", 4, 100.0),
                ("CS702", "AI & Machine Learning Laboratory", "Lab", 2, 50.0),
                ("CS801", "Capstone Major Project", "Lab", 6, 200.0),
            ]
            insert_sub_sql = "INSERT IGNORE INTO subjects(subject_code, subject_name, subject_type, credits, default_max_marks) VALUES(?, ?, ?, ?, ?)" if conn.is_mysql else "INSERT OR IGNORE INTO subjects(subject_code, subject_name, subject_type, credits, default_max_marks) VALUES(?, ?, ?, ?, ?)"
            for code, name, stype, credits, max_m in subjects:
                conn.execute(insert_sub_sql, (code, name, stype, credits, max_m))

        if seed:
            seed_sample_data(conn)
            ensure_seed_students(conn)


def ensure_seed_students(conn):
    try:
        existing_rolls = {r[0] for r in conn.execute("SELECT roll_no FROM students").fetchall()}
        if len(existing_rolls) >= 10:
            return
        if "CE-2026-048" not in existing_rolls:
            c5 = conn.execute(
                """INSERT INTO students(roll_no, full_name, email, phone, department, admission_year,
                                       secondary_percent, higher_secondary_percent, current_semester, current_status)
                   VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("CE-2026-048", "dhiraj suthar", "dhiraj.suthar@example.edu", "+91 98765 43214", "Computer Engineering", 2026, 88.0, 85.0, 1, "Active")
            )
            s5_id = c5.lastrowid
            conn.execute(
                """INSERT INTO semesters(student_id, semester_no, academic_year, sgpa, cgpa, status, remarks)
                   VALUES(?, ?, ?, ?, ?, ?, ?)""",
                (s5_id, 1, "2026-2027", 8.40, 8.40, "Completed", "First semester")
            )
        if "CE-2025-99" not in existing_rolls:
            c6 = conn.execute(
                """INSERT INTO students(roll_no, full_name, email, phone, department, admission_year,
                                       secondary_percent, higher_secondary_percent, current_semester, current_status)
                   VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("CE-2025-99", "Praveen tiwari", "praveen.t@example.edu", "+91 98765 43215", "Computer Engineering", 2025, 90.0, 87.5, 2, "Active")
            )
            s6_id = c6.lastrowid
            conn.execute(
                """INSERT INTO semesters(student_id, semester_no, academic_year, sgpa, cgpa, status, remarks)
                   VALUES(?, ?, ?, ?, ?, ?, ?)""",
                (s6_id, 1, "2025-2026", 8.70, 8.70, "Completed", "Good start")
            )
        if "CE-2022-001" not in existing_rolls:
            c7 = conn.execute(
                """INSERT INTO students(roll_no, full_name, email, phone, department, admission_year,
                                       secondary_percent, higher_secondary_percent, current_semester, current_status)
                   VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("CE-2022-001", "Gaurishankar Yadav", "gaurishankaryadav896@gmail.com", "+91 98765 00001", "Computer Engineering", 2022, 94.5, 92.0, 5, "Active")
            )
            s7_id = c7.lastrowid
            for sem_no, ac_yr, sgpa, cgpa, rem in [
                (1, "2022-2023", 9.20, 9.20, "Outstanding first semester"),
                (2, "2022-2023", 9.40, 9.30, "Dean List Honoree"),
                (3, "2023-2024", 9.50, 9.37, "DBMS Subject Topper"),
                (4, "2023-2024", 9.60, 9.43, "Full-Stack Project Distinction"),
                (5, "2024-2025", 9.50, 9.44, "Continuous Academic Excellence"),
            ]:
                conn.execute(
                    """INSERT INTO semesters(student_id, semester_no, academic_year, sgpa, cgpa, status, remarks)
                       VALUES(?, ?, ?, ?, ?, ?, ?)""",
                    (s7_id, sem_no, ac_yr, sgpa, cgpa, "Completed", rem)
                )
            conn.execute(
                """INSERT INTO seminars(student_id, title, seminar_type, seminar_date, organizer)
                   VALUES(?, ?, ?, ?, ?)""",
                (s7_id, "Relational Database Normalization & Cloud Scalability", "Internal", "2024-03-15", "Dept of Computer Engineering")
            )
        if "ECE-2025-31" not in existing_rolls:
            c8 = conn.execute(
                """INSERT INTO students(roll_no, full_name, email, phone, department, admission_year,
                                       secondary_percent, higher_secondary_percent, current_semester, current_status)
                   VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("ECE-2025-31", "Vyomesh Shetty", "vyomesh79@gmail.com", "+91 98765 00002", "Electronics & Communication", 2025, 91.0, 89.0, 1, "Active")
            )
            s8_id = c8.lastrowid
            conn.execute(
                """INSERT INTO semesters(student_id, semester_no, academic_year, sgpa, cgpa, status, remarks)
                   VALUES(?, ?, ?, ?, ?, ?, ?)""",
                (s8_id, 1, "2025-2026", 8.90, 8.90, "Completed", "First semester distinction")
            )
    except Exception as e:
        print(f"[database.py] ensure_seed_students notice: {e}")


def truncate_all_tables():
    """Delete all rows from every table and reset auto‑increment counters.
    Works for both MySQL (using TRUNCATE) and SQLite (DELETE + sqlite_sequence reset)."""
    tables = [
        "activities",
        "seminars",
        "gap_years",
        "semester_subject_marks",
        "semesters",
        "subjects",
        "students",
    ]
    with get_db() as conn:
        if conn.is_mysql:
            # Disable foreign key checks for MySQL
            conn.execute("SET FOREIGN_KEY_CHECKS=0;")
            # MySQL: TRUNCATE resets AUTO_INCREMENT automatically
            for t in tables:
                conn.execute(f"TRUNCATE TABLE {t}")
            # Re‑enable foreign key checks
            conn.execute("SET FOREIGN_KEY_CHECKS=1;")
        else:
            # Disable foreign key enforcement for SQLite
            conn.execute("PRAGMA foreign_keys = OFF;")
            # SQLite: DELETE rows then reset sequence counters
            for t in tables:
                conn.execute(f"DELETE FROM {t}")
            # Reset sqlite_sequence for all tables in one statement
            placeholders = ", ".join(["?" for _ in tables])
            conn.execute(
                f"DELETE FROM sqlite_sequence WHERE name IN ({placeholders})",
                tables,
            )
            # Re‑enable foreign key enforcement
            conn.execute("PRAGMA foreign_keys = ON;")
        return True


def seed_sample_data(conn):
    """Populates rich demonstration records if database is empty."""
    student_count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    if student_count > 0:
        return

    print("[database.py] Seeding demonstration records...")

    c1 = conn.execute(
        """INSERT INTO students(roll_no, full_name, email, phone, department, admission_year,
                               secondary_percent, higher_secondary_percent, current_semester, current_status)
           VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("CE-2021-042", "Aarav Sharma", "aarav.sharma@example.edu", "+91 98765 43210", "Computer Engineering", 2021, 92.4, 89.6, 7, "Active")
    )
    s1_id = c1.lastrowid

    s1_sems = [
        (1, "2021-2022", 8.50, 8.50, "Completed", "Strong core performance"),
        (2, "2021-2022", 8.75, 8.63, "Completed", "Excellence in data structures"),
        (3, "2022-2023", 8.90, 8.72, "Completed", "Database topper"),
        (4, "2022-2023", 9.10, 8.81, "Completed", "Published research paper"),
        (5, "2023-2024", 8.80, 8.81, "Completed", "Consistent track record"),
        (6, "2023-2024", 9.25, 8.88, "Completed", "High distinction in Cloud"),
    ]
    sem_ids_s1 = {}
    for sem_no, ac_yr, sgpa, cgpa, st, rem in s1_sems:
        cur = conn.execute(
            """INSERT INTO semesters(student_id, semester_no, academic_year, sgpa, cgpa, status, remarks)
               VALUES(?, ?, ?, ?, ?, ?, ?)""",
            (s1_id, sem_no, ac_yr, sgpa, cgpa, st, rem)
        )
        sem_ids_s1[sem_no] = cur.lastrowid

    c2 = conn.execute(
        """INSERT INTO students(roll_no, full_name, email, phone, department, admission_year,
                               secondary_percent, higher_secondary_percent, current_semester, current_status)
           VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("CE-2020-015", "Priya Nair", "priya.nair@example.edu", "+91 98765 43211", "Computer Engineering", 2020, 88.0, 84.5, 8, "Active")
    )
    s2_id = c2.lastrowid

    s2_sems = [
        (1, "2020-2021", 8.20, 8.20, "Completed", "First year foundation"),
        (2, "2020-2021", 8.40, 8.30, "Completed", "Good analytical skills"),
        (3, "2022-2023", 8.10, 8.23, "Completed", "Resumed after medical recovery"),
        (4, "2022-2023", 8.50, 8.30, "Completed", "Rapid academic bounce-back"),
        (5, "2023-2024", 8.60, 8.36, "Completed", "Project team lead"),
        (6, "2023-2024", 8.75, 8.42, "Completed", "Dean's list honors"),
    ]
    sem_ids_s2 = {}
    for sem_no, ac_yr, sgpa, cgpa, st, rem in s2_sems:
        cur = conn.execute(
            """INSERT INTO semesters(student_id, semester_no, academic_year, sgpa, cgpa, status, remarks)
               VALUES(?, ?, ?, ?, ?, ?, ?)""",
            (s2_id, sem_no, ac_yr, sgpa, cgpa, st, rem)
        )
        sem_ids_s2[sem_no] = cur.lastrowid

    conn.execute(
        """INSERT INTO gap_years(student_id, start_year, end_year, gap_type, reason)
           VALUES(?, ?, ?, ?, ?)""",
        (s2_id, 2021, 2022, "Medical Leave", "Underwent orthopedic knee surgery followed by physiotherapy rehabilitation.")
    )

    c3 = conn.execute(
        """INSERT INTO students(roll_no, full_name, email, phone, department, admission_year,
                               secondary_percent, higher_secondary_percent, current_semester, current_status)
           VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("CE-2022-088", "Rohan Patel", "rohan.patel@example.edu", "+91 98765 43212", "Computer Engineering", 2022, 79.5, 76.0, 5, "Active")
    )
    s3_id = c3.lastrowid
    conn.execute(
        """INSERT INTO semesters(student_id, semester_no, academic_year, sgpa, cgpa, status, remarks)
           VALUES(?, ?, ?, ?, ?, ?, ?)""",
        (s3_id, 1, "2022-2023", 7.80, 7.80, "Completed", "Joined under state quota")
    )
    conn.execute(
        """INSERT INTO semesters(student_id, semester_no, academic_year, sgpa, cgpa, status, remarks)
           VALUES(?, ?, ?, ?, ?, ?, ?)""",
        (s3_id, 3, "2023-2024", 8.15, 7.97, "Completed", "Grade improvement shown")
    )

    c4 = conn.execute(
        """INSERT INTO students(roll_no, full_name, email, phone, department, admission_year,
                               secondary_percent, higher_secondary_percent, current_semester, current_status)
           VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("CE-2020-004", "Ananya Deshmukh", "ananya.d@example.edu", "+91 98765 43213", "Computer Engineering", 2020, 95.2, 94.0, 8, "Graduated")
    )
    s4_id = c4.lastrowid
    conn.execute(
        """INSERT INTO semesters(student_id, semester_no, academic_year, sgpa, cgpa, status, remarks)
           VALUES(?, ?, ?, ?, ?, ?, ?)""",
        (s4_id, 8, "2023-2024", 9.80, 9.45, "Completed", "Gold Medalist / College Valedictorian")
    )

    c5 = conn.execute(
        """INSERT INTO students(roll_no, full_name, email, phone, department, admission_year,
                               secondary_percent, higher_secondary_percent, current_semester, current_status)
           VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("CE-2026-048", "dhiraj suthar", "dhiraj.suthar@example.edu", "+91 98765 43214", "Computer Engineering", 2026, 88.0, 85.0, 1, "Active")
    )
    s5_id = c5.lastrowid
    conn.execute(
        """INSERT INTO semesters(student_id, semester_no, academic_year, sgpa, cgpa, status, remarks)
           VALUES(?, ?, ?, ?, ?, ?, ?)""",
        (s5_id, 1, "2026-2027", 8.40, 8.40, "Completed", "First semester")
    )

    c6 = conn.execute(
        """INSERT INTO students(roll_no, full_name, email, phone, department, admission_year,
                               secondary_percent, higher_secondary_percent, current_semester, current_status)
           VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("CE-2025-99", "Praveen tiwari", "praveen.t@example.edu", "+91 98765 43215", "Computer Engineering", 2025, 90.0, 87.5, 2, "Active")
    )
    s6_id = c6.lastrowid
    conn.execute(
        """INSERT INTO semesters(student_id, semester_no, academic_year, sgpa, cgpa, status, remarks)
           VALUES(?, ?, ?, ?, ?, ?, ?)""",
        (s6_id, 1, "2025-2026", 8.70, 8.70, "Completed", "Good start")
    )

    subjects = {row["subject_code"]: row["id"] for row in conn.execute("SELECT id, subject_code FROM subjects").fetchall()}

    if 1 in sem_ids_s1:
        conn.execute(
            """INSERT INTO semester_subject_marks(semester_id, subject_id, marks_obtained, max_marks, grade_point)
               VALUES(?, ?, ?, ?, ?)""",
            (sem_ids_s1[1], subjects["CS101"], 86.0, 100.0, 9.0)
        )
        conn.execute(
            """INSERT INTO semester_subject_marks(semester_id, subject_id, marks_obtained, max_marks, grade_point)
               VALUES(?, ?, ?, ?, ?)""",
            (sem_ids_s1[1], subjects["CS102"], 45.0, 50.0, 9.0)
        )

    if 3 in sem_ids_s1:
        conn.execute(
            """INSERT INTO semester_subject_marks(semester_id, subject_id, marks_obtained, max_marks, grade_point)
               VALUES(?, ?, ?, ?, ?)""",
            (sem_ids_s1[3], subjects["CS201"], 92.0, 100.0, 10.0)
        )
        conn.execute(
            """INSERT INTO semester_subject_marks(semester_id, subject_id, marks_obtained, max_marks, grade_point)
               VALUES(?, ?, ?, ?, ?)""",
            (sem_ids_s1[3], subjects["CS202"], 48.0, 50.0, 10.0)
        )

    # Seminars
    conn.execute(
        """INSERT INTO seminars(student_id, title, seminar_type, seminar_date, organizer, certificate_url)
           VALUES(?, ?, ?, ?, ?, ?)""",
        (s1_id, "Next-Gen Database Architectures and Distributed Consensus", "Internal", "2023-09-15", "Department of Computer Engineering, ECE Forum", "https://drive.google.com/cert/aarav-db-seminar")
    )
    conn.execute(
        """INSERT INTO seminars(student_id, title, seminar_type, seminar_date, organizer, certificate_url)
           VALUES(?, ?, ?, ?, ?, ?)""",
        (s1_id, "Microservices and Serverless Infrastructure at Scale", "External", "2024-02-18", "IEEE Computer Society International Chapter", "https://ieee.org/certificates/2024/aarav-ms")
    )

    cats = {row["name"]: row["id"] for row in conn.execute("SELECT id, name FROM activity_categories").fetchall()}
    conn.execute(
        """INSERT INTO activities(student_id, category_id, activity_name, description, activity_date, achievement_level, certificate_ref)
           VALUES(?, ?, ?, ?, ?, ?, ?)""",
        (s1_id, cats.get("Coding Contest & Hackathon", 1), "Smart India Hackathon (SIH 2023)", "Developed an automated triage system for rural health centers.", "2023-10-12", "Winner", "SIH-2023-WIN-8841")
    )

    conn.execute(
        """INSERT INTO sync_log(synced_at, sync_type, status, records_synced, message)
           VALUES(?, ?, ?, ?, ?)""",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "System", "SUCCESS", 4, "Database initialized and demo data loaded.")
    )


# ============================================================================
# Dashboard Statistics
# ============================================================================

def get_dashboard_stats():
    """Returns high-level statistics for dashboard widgets."""
    with get_db() as conn:
        total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        total_semesters = conn.execute("SELECT COUNT(*) FROM semesters").fetchone()[0]
        total_seminars = conn.execute("SELECT COUNT(*) FROM seminars").fetchone()[0]
        total_activities = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
        total_gaps = conn.execute("SELECT COUNT(*) FROM gap_years").fetchone()[0]
        active_students = conn.execute("SELECT COUNT(*) FROM students WHERE current_status = 'Active'").fetchone()[0]
        avg_cgpa_row = conn.execute("SELECT AVG(cgpa) FROM semesters WHERE cgpa IS NOT NULL").fetchone()[0]
        avg_cgpa = round(float(avg_cgpa_row), 2) if avg_cgpa_row is not None else 0.0
        last_sync = conn.execute("SELECT * FROM sync_log ORDER BY id DESC LIMIT 1").fetchone()

    return {
        "total_students": total_students,
        "total_semesters": total_semesters,
        "total_seminars": total_seminars,
        "total_activities": total_activities,
        "total_gaps": total_gaps,
        "active_students": active_students,
        "avg_cgpa": avg_cgpa,
        "last_sync": last_sync,
        "db_engine": "MySQL" if is_using_mysql() else "SQLite"
    }


# ============================================================================
# Student CRUD
# ============================================================================

def get_students(search_query=None, status_filter=None):
    """Fetch students with calculated latest CGPA."""
    with get_db() as conn:
        sql = """
            SELECT s.*, 
                   (SELECT cgpa FROM semesters WHERE student_id = s.id ORDER BY semester_no DESC LIMIT 1) as latest_cgpa,
                   (SELECT COUNT(*) FROM semesters WHERE student_id = s.id) as recorded_semesters,
                   (SELECT COUNT(*) FROM gap_years WHERE student_id = s.id) as gap_count
            FROM students s
            WHERE 1=1
        """
        params = []
        if search_query:
            sql += " AND (s.full_name LIKE ? OR s.roll_no LIKE ? OR s.email LIKE ?)"
            q = f"%{search_query.strip()}%"
            params.extend([q, q, q])
        if status_filter and status_filter != "All":
            sql += " AND s.current_status = ?"
            params.append(status_filter)

        sql += " ORDER BY s.roll_no ASC"
        return conn.execute(sql, params).fetchall()


def get_student_by_id(student_id):
    """Fetch single student profile by primary key."""
    with get_db() as conn:
        return conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()


def create_student(roll_no, full_name, email, phone, department, admission_year,
                   secondary_percent, higher_secondary_percent, current_semester, current_status):
    """Insert a new student profile."""
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO students(roll_no, full_name, email, phone, department, admission_year,
                                   secondary_percent, higher_secondary_percent, current_semester, current_status)
               VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                roll_no.strip().upper(),
                full_name.strip(),
                email.strip() if email else None,
                phone.strip() if phone else None,
                department.strip() or "Computer Engineering",
                int(admission_year),
                float(secondary_percent) if secondary_percent is not None and secondary_percent != "" else None,
                float(higher_secondary_percent) if higher_secondary_percent is not None and higher_secondary_percent != "" else None,
                int(current_semester) if current_semester else 1,
                current_status or "Active",
            ),
        )
        return cur.lastrowid


def update_student(student_id, roll_no, full_name, email, phone, department, admission_year,
                   secondary_percent, higher_secondary_percent, current_semester, current_status):
    """Update an existing student profile."""
    with get_db() as conn:
        conn.execute(
            """UPDATE students
               SET roll_no = ?, full_name = ?, email = ?, phone = ?, department = ?, admission_year = ?,
                   secondary_percent = ?, higher_secondary_percent = ?, current_semester = ?, current_status = ?
               WHERE id = ?""",
            (
                roll_no.strip().upper(),
                full_name.strip(),
                email.strip() if email else None,
                phone.strip() if phone else None,
                department.strip() or "Computer Engineering",
                int(admission_year),
                float(secondary_percent) if secondary_percent is not None and secondary_percent != "" else None,
                float(higher_secondary_percent) if higher_secondary_percent is not None and higher_secondary_percent != "" else None,
                int(current_semester) if current_semester else 1,
                current_status or "Active",
                student_id,
            ),
        )


def delete_student(student_id):
    """Delete student profile (foreign keys CASCADE automatically)."""
    with get_db() as conn:
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))


# ============================================================================
# Semester & Marks CRUD
# ============================================================================

def get_semesters_for_student(student_id):
    """Fetch all semester records for a student ordered by semester_no."""
    with get_db() as conn:
        return conn.execute(
            """SELECT s.*, 
                      (SELECT COUNT(*) FROM semester_subject_marks WHERE semester_id = s.id) as subject_count
               FROM semesters s
               WHERE s.student_id = ?
               ORDER BY s.semester_no ASC""",
            (student_id,),
        ).fetchall()


def get_semester_by_id(semester_id):
    """Fetch semester by primary key."""
    with get_db() as conn:
        return conn.execute("SELECT * FROM semesters WHERE id = ?", (semester_id,)).fetchone()


def add_semester(student_id, semester_no, academic_year, sgpa=None, cgpa=None, status="Completed", remarks=None):
    """Insert a semester record."""
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO semesters(student_id, semester_no, academic_year, sgpa, cgpa, status, remarks)
               VALUES(?, ?, ?, ?, ?, ?, ?)""",
            (
                student_id,
                int(semester_no),
                academic_year.strip(),
                float(sgpa) if sgpa is not None and sgpa != "" else None,
                float(cgpa) if cgpa is not None and cgpa != "" else None,
                status or "Completed",
                remarks.strip() if remarks else None,
            ),
        )
        return cur.lastrowid


def update_semester(semester_id, semester_no, academic_year, sgpa=None, cgpa=None, status="Completed", remarks=None):
    """Update semester performance record."""
    with get_db() as conn:
        conn.execute(
            """UPDATE semesters
               SET semester_no = ?, academic_year = ?, sgpa = ?, cgpa = ?, status = ?, remarks = ?
               WHERE id = ?""",
            (
                int(semester_no),
                academic_year.strip(),
                float(sgpa) if sgpa is not None and sgpa != "" else None,
                float(cgpa) if cgpa is not None and cgpa != "" else None,
                status or "Completed",
                remarks.strip() if remarks else None,
                semester_id,
            ),
        )


def delete_semester(semester_id):
    """Delete semester record and cascade-delete its subject marks."""
    with get_db() as conn:
        conn.execute("DELETE FROM semesters WHERE id = ?", (semester_id,))


def get_subjects():
    """Return all master subjects."""
    with get_db() as conn:
        return conn.execute("SELECT * FROM subjects ORDER BY subject_type, subject_name").fetchall()


def add_subject(subject_code, subject_name, subject_type, credits=3, default_max_marks=100.0):
    """Add a master subject to catalog."""
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO subjects(subject_code, subject_name, subject_type, credits, default_max_marks)
               VALUES(?, ?, ?, ?, ?)""",
            (subject_code.strip().upper(), subject_name.strip(), subject_type, int(credits), float(default_max_marks)),
        )
        return cur.lastrowid


def delete_subject(subject_id):
    """Delete a master subject."""
    with get_db() as conn:
        conn.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))


def get_marks_for_semester(semester_id):
    """Fetch all subject marks for a semester with subject details."""
    with get_db() as conn:
        return conn.execute(
            """SELECT m.*, sub.subject_code, sub.subject_name, sub.subject_type, sub.credits
               FROM semester_subject_marks m
               JOIN subjects sub ON sub.id = m.subject_id
               WHERE m.semester_id = ?
               ORDER BY sub.subject_type DESC, sub.subject_code ASC""",
            (semester_id,),
        ).fetchall()


def get_all_marks_for_student(student_id):
    """Fetch all subject marks for a student across all semesters."""
    with get_db() as conn:
        return conn.execute(
            """SELECT m.*, sem.semester_no, sem.academic_year,
                      sub.subject_code, sub.subject_name, sub.subject_type, sub.credits
               FROM semester_subject_marks m
               JOIN semesters sem ON sem.id = m.semester_id
               JOIN subjects sub ON sub.id = m.subject_id
               WHERE sem.student_id = ?
               ORDER BY sem.semester_no ASC, sub.subject_type DESC, sub.subject_code ASC""",
            (student_id,),
        ).fetchall()


def add_or_update_subject_marks(semester_id, subject_id, marks_obtained, max_marks, grade_point=None):
    """Insert or update marks for a subject in a semester."""
    mo = float(marks_obtained)
    mm = float(max_marks)
    if mo < 0 or mm <= 0 or mo > mm:
        raise ValueError("Marks obtained must be between 0 and maximum marks.")

    gp = float(grade_point) if grade_point is not None and grade_point != "" else round((mo / mm) * 10.0, 2)

    with get_db() as conn:
        if conn.is_mysql:
            sql = """
                INSERT INTO semester_subject_marks(semester_id, subject_id, marks_obtained, max_marks, grade_point)
                VALUES(?, ?, ?, ?, ?)
                ON DUPLICATE KEY UPDATE
                    marks_obtained = VALUES(marks_obtained),
                    max_marks = VALUES(max_marks),
                    grade_point = VALUES(grade_point)
            """
        else:
            sql = """
                INSERT INTO semester_subject_marks(semester_id, subject_id, marks_obtained, max_marks, grade_point)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(semester_id, subject_id) DO UPDATE SET
                    marks_obtained = excluded.marks_obtained,
                    max_marks = excluded.max_marks,
                    grade_point = excluded.grade_point
            """
        conn.execute(sql, (semester_id, int(subject_id), mo, mm, gp))


def delete_subject_mark(mark_id):
    """Delete a subject mark record."""
    with get_db() as conn:
        conn.execute("DELETE FROM semester_subject_marks WHERE id = ?", (mark_id,))


# ============================================================================
# Seminars, Activities, Gap Years
# ============================================================================

def get_seminars_for_student(student_id):
    """Fetch seminars for a student."""
    with get_db() as conn:
        return conn.execute("SELECT * FROM seminars WHERE student_id = ? ORDER BY seminar_date DESC", (student_id,)).fetchall()


def get_all_seminars(seminar_type=None, search_query=None):
    """Fetch all seminars across students."""
    with get_db() as conn:
        sql = """
            SELECT sem.*, st.roll_no, st.full_name as student_name
            FROM seminars sem
            JOIN students st ON st.id = sem.student_id
            WHERE 1=1
        """
        params = []
        if seminar_type and seminar_type != "All":
            sql += " AND sem.seminar_type = ?"
            params.append(seminar_type)
        if search_query:
            sql += " AND (sem.title LIKE ? OR sem.organizer LIKE ? OR st.full_name LIKE ?)"
            q = f"%{search_query.strip()}%"
            params.extend([q, q, q])
        sql += " ORDER BY sem.seminar_date DESC"
        return conn.execute(sql, params).fetchall()


def add_seminar(student_id, title, seminar_type, seminar_date, organizer, certificate_url=None):
    """Record an internal or external seminar."""
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO seminars(student_id, title, seminar_type, seminar_date, organizer, certificate_url)
               VALUES(?, ?, ?, ?, ?, ?)""",
            (student_id, title.strip(), seminar_type, seminar_date.strip(), organizer.strip(), certificate_url.strip() if certificate_url else None),
        )
        return cur.lastrowid


def delete_seminar(seminar_id):
    """Delete a seminar record."""
    with get_db() as conn:
        conn.execute("DELETE FROM seminars WHERE id = ?", (seminar_id,))


def get_activity_categories():
    """Fetch all activity categories."""
    with get_db() as conn:
        return conn.execute("SELECT * FROM activity_categories ORDER BY activity_type, name").fetchall()


def get_activities_for_student(student_id, activity_type=None):
    """Fetch activities for a student."""
    with get_db() as conn:
        sql = """
            SELECT a.*, c.name as category_name, c.activity_type
            FROM activities a
            JOIN activity_categories c ON c.id = a.category_id
            WHERE a.student_id = ?
        """
        params = [student_id]
        if activity_type:
            sql += " AND c.activity_type = ?"
            params.append(activity_type)
        sql += " ORDER BY a.activity_date DESC"
        return conn.execute(sql, params).fetchall()


def get_all_activities(activity_type=None, search_query=None):
    """Fetch all activities across students."""
    with get_db() as conn:
        sql = """
            SELECT a.*, c.name as category_name, c.activity_type, st.roll_no, st.full_name as student_name
            FROM activities a
            JOIN activity_categories c ON c.id = a.category_id
            JOIN students st ON st.id = a.student_id
            WHERE 1=1
        """
        params = []
        if activity_type and activity_type != "All":
            sql += " AND c.activity_type = ?"
            params.append(activity_type)
        if search_query:
            sql += " AND (a.activity_name LIKE ? OR a.description LIKE ? OR st.full_name LIKE ?)"
            q = f"%{search_query.strip()}%"
            params.extend([q, q, q])
        sql += " ORDER BY a.activity_date DESC"
        return conn.execute(sql, params).fetchall()


def add_activity(student_id, category_id, activity_name, description, activity_date, achievement_level, certificate_ref=None):
    """Record an activity."""
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO activities(student_id, category_id, activity_name, description, activity_date, achievement_level, certificate_ref)
               VALUES(?, ?, ?, ?, ?, ?, ?)""",
            (student_id, int(category_id), activity_name.strip(), description.strip() if description else None, activity_date.strip(), achievement_level or "Participant", certificate_ref.strip() if certificate_ref else None),
        )
        return cur.lastrowid


def delete_activity(activity_id):
    """Delete an activity record."""
    with get_db() as conn:
        conn.execute("DELETE FROM activities WHERE id = ?", (activity_id,))


def get_gap_years_for_student(student_id):
    """Fetch gap years for a student."""
    with get_db() as conn:
        return conn.execute("SELECT * FROM gap_years WHERE student_id = ? ORDER BY start_year ASC", (student_id,)).fetchall()


def add_gap_year(student_id, start_year, end_year, gap_type, reason):
    """Record an academic gap year."""
    sy = int(start_year)
    ey = int(end_year)
    if ey < sy:
        raise ValueError("End year cannot be earlier than start year.")

    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO gap_years(student_id, start_year, end_year, gap_type, reason)
               VALUES(?, ?, ?, ?, ?)""",
            (student_id, sy, ey, gap_type or "Academic Drop", reason.strip()),
        )
        return cur.lastrowid


def delete_gap_year(gap_id):
    """Delete a gap year entry."""
    with get_db() as conn:
        conn.execute("DELETE FROM gap_years WHERE id = ?", (gap_id,))


# ============================================================================
# Synchronization Audit Logging & Progression Data Exporter
# ============================================================================

def log_sync(status, records_synced, message, sync_type="Manual"):
    """Record synchronization audit trail."""
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO sync_log(synced_at, sync_type, status, records_synced, message)
               VALUES(?, ?, ?, ?, ?)""",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), sync_type, status, int(records_synced), str(message)),
        )
        return cur.lastrowid


def get_sync_logs(limit=25):
    """Fetch latest synchronization audit logs."""
    with get_db() as conn:
        return conn.execute("SELECT * FROM sync_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()


def get_last_sync():
    """Fetch the most recent sync record."""
    with get_db() as conn:
        return conn.execute("SELECT * FROM sync_log ORDER BY id DESC LIMIT 1").fetchone()


def get_progression_export_data():
    """Generates a flattened, joined dataset of student profiles and progression."""
    with get_db() as conn:
        if conn.is_mysql:
            sql = """
                SELECT 
                    st.roll_no,
                    st.full_name,
                    st.email,
                    st.phone,
                    st.department,
                    st.admission_year,
                    st.secondary_percent,
                    st.higher_secondary_percent,
                    st.current_status,
                    sem.semester_no,
                    sem.academic_year,
                    sem.sgpa,
                    sem.cgpa,
                    sem.status as semester_status,
                    sem.remarks,
                    (SELECT GROUP_CONCAT(CONCAT(start_year, '-', end_year, ' (', gap_type, ': ', reason, ')') SEPARATOR '; ')
                     FROM gap_years WHERE student_id = st.id) as gap_years_summary
                FROM students st
                LEFT JOIN semesters sem ON sem.student_id = st.id
                ORDER BY st.roll_no ASC, sem.semester_no ASC
            """
        else:
            sql = """
                SELECT 
                    st.roll_no,
                    st.full_name,
                    st.email,
                    st.phone,
                    st.department,
                    st.admission_year,
                    st.secondary_percent,
                    st.higher_secondary_percent,
                    st.current_status,
                    sem.semester_no,
                    sem.academic_year,
                    sem.sgpa,
                    sem.cgpa,
                    sem.status as semester_status,
                    sem.remarks,
                    (SELECT GROUP_CONCAT(start_year || '-' || end_year || ' (' || gap_type || ': ' || reason || ')', '; ')
                     FROM gap_years WHERE student_id = st.id) as gap_years_summary
                FROM students st
                LEFT JOIN semesters sem ON sem.student_id = st.id
                ORDER BY st.roll_no ASC, sem.semester_no ASC
            """
        return conn.execute(sql).fetchall()


def get_all_normalized_tables_data():
    """
    Returns full data for all normalized tables to sync into individual Google Sheet tabs:
    - students
    - school_records (secondary & higher secondary percent)
    - semesters
    - subjects
    - semester_results (marks obtained, max marks, grade points)
    - drop_years (gap years)
    - achievements (activities & seminars)
    - achievement_categories
    """
    with get_db() as conn:
        students = conn.execute("SELECT id, roll_no, full_name, email, phone, department, admission_year, current_semester, current_status, created_at FROM students ORDER BY id ASC").fetchall()
        
        school_records = conn.execute("SELECT id as student_id, roll_no, full_name, secondary_percent as `10th_percent`, higher_secondary_percent as `12th_percent`, admission_year FROM students ORDER BY id ASC").fetchall()
        
        semesters = conn.execute("""
            SELECT sem.id, sem.student_id, st.roll_no, st.full_name, sem.semester_no, sem.academic_year, sem.sgpa, sem.cgpa, sem.status, sem.remarks
            FROM semesters sem
            JOIN students st ON st.id = sem.student_id
            ORDER BY sem.student_id ASC, sem.semester_no ASC
        """).fetchall()
        
        subjects = conn.execute("SELECT id, subject_code, subject_name, subject_type, credits, default_max_marks FROM subjects ORDER BY id ASC").fetchall()
        
        semester_results = conn.execute("""
            SELECT m.id, m.semester_id, st.roll_no, st.full_name, sem.semester_no, sub.subject_code, sub.subject_name, sub.subject_type, m.marks_obtained, m.max_marks, m.grade_point
            FROM semester_subject_marks m
            JOIN semesters sem ON sem.id = m.semester_id
            JOIN students st ON st.id = sem.student_id
            JOIN subjects sub ON sub.id = m.subject_id
            ORDER BY st.roll_no ASC, sem.semester_no ASC, sub.subject_code ASC
        """).fetchall()
        
        drop_years = conn.execute("""
            SELECT g.id, g.student_id, st.roll_no, st.full_name, g.start_year, g.end_year, g.gap_type, g.reason
            FROM gap_years g
            JOIN students st ON st.id = g.student_id
            ORDER BY g.student_id ASC
        """).fetchall()
        
        achievements = conn.execute("""
            SELECT a.id, a.student_id, st.roll_no, st.full_name, c.name as category, c.activity_type, a.activity_name, a.description, a.activity_date, a.achievement_level, a.certificate_ref
            FROM activities a
            JOIN students st ON st.id = a.student_id
            JOIN activity_categories c ON c.id = a.category_id
            ORDER BY a.activity_date DESC
        """).fetchall()
        
        categories = conn.execute("SELECT id, name, activity_type FROM activity_categories ORDER BY id ASC").fetchall()
        
    return {
        "students": [dict(r) for r in students],
        "school_records": [dict(r) for r in school_records],
        "semesters": [dict(r) for r in semesters],
        "subjects": [dict(r) for r in subjects],
        "semester_results": [dict(r) for r in semester_results],
        "drop_years": [dict(r) for r in drop_years],
        "achievements": [dict(r) for r in achievements],
        "achievement_categories": [dict(r) for r in categories],
    }

