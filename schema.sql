-- ============================================================================
-- Student Academic Progression and Portfolio Management System
-- Database Schema Definition (Normalized to 3NF)
-- DBMS Mini-Project for College Faculty Demonstration & Viva Defense
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- Table 1: students
-- Primary student profile. Stores static student attributes (3NF: no transitive
-- dependencies; roll_no and email unique; percentages validated 0-100).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    roll_no TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE,
    phone TEXT,
    department TEXT NOT NULL DEFAULT 'Computer Engineering',
    admission_year INTEGER NOT NULL,
    secondary_percent REAL CHECK(secondary_percent IS NULL OR (secondary_percent >= 0.0 AND secondary_percent <= 100.0)),
    higher_secondary_percent REAL CHECK(higher_secondary_percent IS NULL OR (higher_secondary_percent >= 0.0 AND higher_secondary_percent <= 100.0)),
    current_semester INTEGER DEFAULT 1 CHECK(current_semester BETWEEN 1 AND 12),
    current_status TEXT NOT NULL DEFAULT 'Active' CHECK(current_status IN ('Active', 'Graduated', 'Discontinued', 'On Leave', 'Drop Year')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- Table 2: semesters
-- Academic performance per semester. Prevents duplicate semester entries per student.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS semesters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    semester_no INTEGER NOT NULL CHECK(semester_no BETWEEN 1 AND 12),
    academic_year TEXT NOT NULL, -- e.g., '2023-2024'
    sgpa REAL CHECK(sgpa IS NULL OR (sgpa >= 0.0 AND sgpa <= 10.0)),
    cgpa REAL CHECK(cgpa IS NULL OR (cgpa >= 0.0 AND cgpa <= 10.0)),
    status TEXT NOT NULL DEFAULT 'Completed' CHECK(status IN ('Completed', 'Ongoing', 'Detained', 'Dropped')),
    remarks TEXT,
    UNIQUE(student_id, semester_no)
);

-- ----------------------------------------------------------------------------
-- Table 3: subjects
-- Master catalog of subjects. Avoids repeating subject titles/types across marks.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_code TEXT NOT NULL UNIQUE,
    subject_name TEXT NOT NULL,
    subject_type TEXT NOT NULL CHECK(subject_type IN ('Theory', 'Lab')),
    credits INTEGER NOT NULL DEFAULT 3 CHECK(credits > 0),
    default_max_marks REAL NOT NULL DEFAULT 100.0 CHECK(default_max_marks > 0)
);

-- ----------------------------------------------------------------------------
-- Table 4: semester_subject_marks
-- Associates subject marks with a specific semester.
-- Enforces marks_obtained <= max_marks and uniqueness per (semester, subject).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS semester_subject_marks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    semester_id INTEGER NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    marks_obtained REAL NOT NULL CHECK(marks_obtained >= 0.0),
    max_marks REAL NOT NULL CHECK(max_marks > 0.0 AND marks_obtained <= max_marks),
    grade_point REAL CHECK(grade_point IS NULL OR (grade_point >= 0.0 AND grade_point <= 10.0)),
    UNIQUE(semester_id, subject_id)
);

-- ----------------------------------------------------------------------------
-- Table 5: activity_categories
-- Normalized activity category lookup to avoid duplicate strings.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activity_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    activity_type TEXT NOT NULL CHECK(activity_type IN ('Technical', 'Co-curricular', 'Extra-curricular'))
);

-- ----------------------------------------------------------------------------
-- Table 6: activities
-- Student achievements in technical, co-curricular, and extra-curricular areas.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES activity_categories(id) ON DELETE RESTRICT,
    activity_name TEXT NOT NULL,
    description TEXT,
    activity_date TEXT NOT NULL,
    achievement_level TEXT DEFAULT 'Participant' CHECK(achievement_level IN ('Participant', 'Winner', 'Runner-up', 'College Level', 'State Level', 'National Level', 'International Level', 'Special Mention')),
    certificate_ref TEXT
);

-- ----------------------------------------------------------------------------
-- Table 7: seminars
-- Internal and external seminar participations / presentations.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS seminars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    seminar_type TEXT NOT NULL CHECK(seminar_type IN ('Internal', 'External')),
    seminar_date TEXT NOT NULL,
    organizer TEXT NOT NULL,
    certificate_url TEXT
);

-- ----------------------------------------------------------------------------
-- Table 8: gap_years
-- Tracks academic interruptions / drop years with validated start/end years.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gap_years (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    start_year INTEGER NOT NULL,
    end_year INTEGER NOT NULL,
    gap_type TEXT DEFAULT 'Academic Drop' CHECK(gap_type IN ('Academic Drop', 'Medical Leave', 'Financial / Personal', 'Preparation / Transition')),
    reason TEXT NOT NULL,
    CHECK(end_year >= start_year)
);

-- ----------------------------------------------------------------------------
-- Table 9: sync_log
-- Audit log of Google Sheets synchronization attempts.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    synced_at TEXT NOT NULL,
    sync_type TEXT NOT NULL DEFAULT 'Manual',
    status TEXT NOT NULL CHECK(status IN ('SUCCESS', 'FAILED', 'PARTIAL')),
    records_synced INTEGER NOT NULL DEFAULT 0,
    message TEXT
);

-- ----------------------------------------------------------------------------
-- Performance Indexes
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_students_roll ON students(roll_no);
CREATE INDEX IF NOT EXISTS idx_semesters_student ON semesters(student_id);
CREATE INDEX IF NOT EXISTS idx_marks_semester ON semester_subject_marks(semester_id);
CREATE INDEX IF NOT EXISTS idx_marks_subject ON semester_subject_marks(subject_id);
CREATE INDEX IF NOT EXISTS idx_activities_student ON activities(student_id);
CREATE INDEX IF NOT EXISTS idx_activities_cat ON activities(category_id);
CREATE INDEX IF NOT EXISTS idx_seminars_student ON seminars(student_id);
CREATE INDEX IF NOT EXISTS idx_gap_years_student ON gap_years(student_id);
CREATE INDEX IF NOT EXISTS idx_sync_log_time ON sync_log(synced_at DESC);
