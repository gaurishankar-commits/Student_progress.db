import sqlite3
import openpyxl
from datetime import datetime
import os

wb = openpyxl.load_workbook('colleague_sheet.xlsx')

db_path = 'student_progression.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Enable foreign keys
cur.execute("PRAGMA foreign_keys = OFF;")

# Clear existing tables to load fresh colleague dataset
tables = ["semester_subject_marks", "semesters", "subjects", "gap_years", "seminars", "activities", "students", "sync_log", "activity_categories"]
for t in tables:
    cur.execute(f"DELETE FROM {t}")
    cur.execute(f"DELETE FROM sqlite_sequence WHERE name='{t}'")

# Ensure Activity Categories
categories = [
    (1, "Technical Competitions & Hackathons", "Technical"),
    (2, "Hardware & Robotics", "Technical"),
    (3, "Workshops & Certifications", "Co-curricular"),
    (4, "Sports & Athletics", "Extra-curricular"),
    (5, "Cultural & Arts", "Extra-curricular"),
    (6, "General Co-curricular", "Co-curricular")
]
for cid, cname, ctype in categories:
    cur.execute("INSERT OR IGNORE INTO activity_categories(id, name, activity_type) VALUES(?, ?, ?)", (cid, cname, ctype))

print("Existing tables cleared and categories initialized.")

# 1. Load Students
ws_students = wb['Students']
student_rows = [r for r in ws_students.iter_rows(values_only=True) if r and r[0] is not None][1:]

for r in student_rows:
    old_id = int(r[0])
    roll_no = str(r[1]).strip()
    name = str(r[2]).strip()
    email = str(r[3]).strip() if r[3] else None
    adm_year = int(float(r[4])) if r[4] else 2023
    status = str(r[5]).strip() if r[5] else 'Active'
    if status == 'Enrolled':
        status = 'Active'
    phone = str(int(float(r[6]))) if r[6] else None
    dept = str(r[7]).strip() if r[7] else 'Computer Engineering'
    
    cur.execute("""
        INSERT INTO students(id, roll_no, full_name, email, phone, department, admission_year, secondary_percent, higher_secondary_percent, current_semester, current_status)
        VALUES(?, ?, ?, ?, ?, ?, ?, 85.0, 82.0, 1, ?)
    """, (old_id, roll_no, name, email, phone, dept, adm_year, status))

print(f"Loaded {len(student_rows)} students.")

# 2. Load Subjects from Subject Marks sheet
ws_marks = wb['Subject Marks']
marks_rows = [r for r in ws_marks.iter_rows(values_only=True) if r and r[0] is not None][1:]

subject_code_map = {} # code -> subject_id
sub_id_counter = 1
for r in marks_rows:
    code = str(r[3]).strip()
    sub_name = str(r[4]).strip()
    sub_type = str(r[5]).strip() if r[5] else 'Theory'
    if sub_type not in ('Theory', 'Lab'):
        sub_type = 'Theory'
    max_m = float(r[7]) if r[7] else 100.0
    
    if code not in subject_code_map:
        cur.execute("""
            INSERT OR IGNORE INTO subjects(id, subject_code, subject_name, subject_type, credits, default_max_marks)
            VALUES(?, ?, ?, ?, 4, ?)
        """, (sub_id_counter, code, sub_name, sub_type, max_m))
        subject_code_map[code] = sub_id_counter
        sub_id_counter += 1

print(f"Loaded {len(subject_code_map)} unique subjects.")

# 3. Load Semesters
ws_semesters = wb['Semesters']
sem_rows = [r for r in ws_semesters.iter_rows(values_only=True) if r and r[0] is not None][1:]

for r in sem_rows:
    old_sem_id = int(r[0])
    old_stu_id = int(r[1])
    sem_no = int(float(r[5])) if r[5] else 1
    ac_year = str(r[6]).strip() if r[6] else '2023-24'
    sgpa = float(r[7]) if r[7] is not None else 8.0
    cgpa = float(r[8]) if r[8] is not None else 8.0
    
    cur.execute("""
        INSERT INTO semesters(id, student_id, semester_no, academic_year, sgpa, cgpa, status, remarks)
        VALUES(?, ?, ?, ?, ?, ?, 'Completed', 'Colleague Dataset Import')
    """, (old_sem_id, old_stu_id, sem_no, ac_year, sgpa, cgpa))

print(f"Loaded {len(sem_rows)} semesters.")

# 4. Load Subject Marks
for r in marks_rows:
    old_mark_id = int(r[0])
    old_sem_id = int(r[1])
    code = str(r[3]).strip()
    sub_id = subject_code_map[code]
    obtained = float(r[6]) if r[6] is not None else 0.0
    max_m = float(r[7]) if r[7] is not None else 100.0
    grade_pt = round((obtained / max_m) * 10, 1)
    
    cur.execute("""
        INSERT INTO semester_subject_marks(id, semester_id, subject_id, marks_obtained, max_marks, grade_point)
        VALUES(?, ?, ?, ?, ?, ?)
    """, (old_mark_id, old_sem_id, sub_id, obtained, max_m, grade_pt))

print(f"Loaded {len(marks_rows)} subject marks.")

# 5. Load Drop Years
ws_drop = wb['Drop Years']
drop_rows = [r for r in ws_drop.iter_rows(values_only=True) if r and r[0] is not None][1:]
for r in drop_rows:
    did = int(r[0])
    stu_id = int(r[1])
    ac_yr = str(r[4]).strip() if r[4] else '2023-24'
    reason = str(r[5]).strip() if r[5] else 'Drop Year'
    start_y = 2023
    end_y = 2024
    if '-' in ac_yr:
        parts = ac_yr.split('-')
        try:
            start_y = int(parts[0])
            end_y = start_y + 1
        except Exception:
            pass
    cur.execute("""
        INSERT INTO gap_years(id, student_id, start_year, end_year, gap_type, reason)
        VALUES(?, ?, ?, ?, 'Medical Leave', ?)
    """, (did, stu_id, start_y, end_y, reason))

print(f"Loaded {len(drop_rows)} drop years.")

# 6. Load Seminars
ws_seminars = wb['Seminars']
sem_rows = [r for r in ws_seminars.iter_rows(values_only=True) if r and r[0] is not None][1:]
for r in sem_rows:
    sid = int(r[0])
    stu_id = int(r[1])
    title = str(r[4]).strip() if r[4] else 'Seminar'
    organizer = str(r[5]).strip() if r[5] else 'Institution'
    scope = str(r[6]).strip() if r[6] else 'Internal'
    if scope not in ('Internal', 'External'):
        scope = 'Internal'
    dt = r[7]
    dt_str = dt.strftime('%Y-%m-%d') if isinstance(dt, datetime) else str(dt)[:10] if dt else '2024-01-01'
    cert = str(r[8]).strip() if r[8] else None
    
    cur.execute("""
        INSERT INTO seminars(id, student_id, title, seminar_type, seminar_date, organizer, certificate_url)
        VALUES(?, ?, ?, ?, ?, ?, ?)
    """, (sid, stu_id, title, scope, dt_str, organizer, cert))

print(f"Loaded {len(sem_rows)} seminars.")

# 7. Load Activities
ws_act = wb['Activities']
act_rows = [r for r in ws_act.iter_rows(values_only=True) if r and r[0] is not None][1:]
for r in act_rows:
    aid = int(r[0])
    stu_id = int(r[1])
    title = str(r[4]).strip() if r[4] else 'Activity'
    organizer = str(r[5]).strip() if r[5] else 'Institution'
    atype = str(r[6]).strip() if r[6] else 'Technical'
    
    # Map type to category_id
    if 'Tech' in atype or 'Robo' in atype or 'Hard' in atype:
        cat_id = 1
    elif 'Sport' in atype:
        cat_id = 4
    elif 'Cult' in atype:
        cat_id = 5
    else:
        cat_id = 3
        
    dt = r[7]
    dt_str = dt.strftime('%Y-%m-%d') if isinstance(dt, datetime) else str(dt)[:10] if dt else '2024-01-01'
    details = str(r[8]).strip() if r[8] else organizer
    
    cur.execute("""
        INSERT INTO activities(id, student_id, category_id, activity_name, activity_date, description, achievement_level)
        VALUES(?, ?, ?, ?, ?, ?, 'Participant')
    """, (aid, stu_id, cat_id, title, dt_str, details))

print(f"Loaded {len(act_rows)} activities.")

# Update student current_semester based on max semester recorded
cur.execute("""
    UPDATE students
    SET current_semester = COALESCE((
        SELECT MAX(semester_no) FROM semesters WHERE semesters.student_id = students.id
    ), 1)
""")

cur.execute("PRAGMA foreign_keys = ON;")
conn.commit()
conn.close()

print("ALL COLLEAGUE DATASET IMPORTED SUCCESSFULLY!")
