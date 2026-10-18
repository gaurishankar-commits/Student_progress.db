import os, sqlite3, json, csv, io
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    gspread = None
    Credentials = None

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "student_progression.db")
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-for-local-demo")

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS students (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 roll_no TEXT NOT NULL UNIQUE,
 full_name TEXT NOT NULL,
 email TEXT UNIQUE,
 department TEXT NOT NULL DEFAULT 'Electrical and Computer Engineering',
 admission_year INTEGER,
 secondary_percent REAL CHECK(secondary_percent IS NULL OR secondary_percent BETWEEN 0 AND 100),
 higher_secondary_percent REAL CHECK(higher_secondary_percent IS NULL OR higher_secondary_percent BETWEEN 0 AND 100),
 current_status TEXT NOT NULL DEFAULT 'Active' CHECK(current_status IN ('Active','Graduated','Discontinued','On Leave')),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS semesters (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
 semester_no INTEGER NOT NULL CHECK(semester_no BETWEEN 1 AND 12),
 academic_year TEXT,
 sgpa REAL CHECK(sgpa IS NULL OR sgpa BETWEEN 0 AND 10),
 cgpa REAL CHECK(cgpa IS NULL OR cgpa BETWEEN 0 AND 10),
 UNIQUE(student_id, semester_no)
);
CREATE TABLE IF NOT EXISTS subjects (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 subject_code TEXT NOT NULL UNIQUE,
 subject_name TEXT NOT NULL,
 subject_type TEXT NOT NULL CHECK(subject_type IN ('Theory','Lab'))
);
CREATE TABLE IF NOT EXISTS marks (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 semester_id INTEGER NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,
 subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
 marks_obtained REAL NOT NULL CHECK(marks_obtained >= 0),
 max_marks REAL NOT NULL CHECK(max_marks > 0 AND marks_obtained <= max_marks),
 UNIQUE(semester_id, subject_id)
);
CREATE TABLE IF NOT EXISTS activity_types (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 category TEXT NOT NULL UNIQUE CHECK(category IN ('Co-curricular','Extra-curricular'))
);
CREATE TABLE IF NOT EXISTS activities (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
 activity_type_id INTEGER NOT NULL REFERENCES activity_types(id),
 title TEXT NOT NULL,
 description TEXT,
 activity_date TEXT,
 achievement_level TEXT
);
CREATE TABLE IF NOT EXISTS seminars (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
 title TEXT NOT NULL,
 organizer_type TEXT NOT NULL CHECK(organizer_type IN ('Internal','External')),
 seminar_date TEXT,
 certificate_ref TEXT
);
CREATE TABLE IF NOT EXISTS gap_years (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
 start_year INTEGER NOT NULL,
 end_year INTEGER NOT NULL,
 reason TEXT,
 CHECK(end_year >= start_year)
);
CREATE TABLE IF NOT EXISTS sync_log (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 synced_at TEXT NOT NULL,
 status TEXT NOT NULL,
 message TEXT
);
INSERT OR IGNORE INTO activity_types(category) VALUES ('Co-curricular'), ('Extra-curricular');
"""

def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db():
    with connect() as con:
        con.executescript(SCHEMA)
        count = con.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        if count == 0:
            cur = con.execute("""INSERT INTO students(roll_no,full_name,email,department,admission_year,secondary_percent,higher_secondary_percent,current_status)
                VALUES(?,?,?,?,?,?,?,?)""",
                ("60", "Demo Student", "demo@example.com", "Electrical and Computer Engineering", 2024, 88.5, 82.0, "Active"))
            sid = cur.lastrowid
            demo = [(1,"2024-25",8.1,8.1),(2,"2024-25",8.4,8.25),(3,"2025-26",7.9,8.13),(5,"2026-27",8.6,8.25)]
            for sem, year, sgpa, cgpa in demo:
                con.execute("INSERT INTO semesters(student_id,semester_no,academic_year,sgpa,cgpa) VALUES(?,?,?,?,?)",(sid,sem,year,sgpa,cgpa))
            con.execute("INSERT INTO gap_years(student_id,start_year,end_year,reason) VALUES(?,?,?,?)",(sid,2025,2025,"Demo gap year marker — edit or delete this sample"))
            con.execute("INSERT INTO seminars(student_id,title,organizer_type,seminar_date) VALUES(?,?,?,?)",(sid,"Introduction to Embedded Systems","Internal","2025-02-10"))
            con.execute("INSERT INTO activities(student_id,activity_type_id,title,description,activity_date,achievement_level) VALUES(?,?,?,?,?,?)",
                (sid,1,"Technical Poster Presentation","Sample co-curricular entry","2025-03-01","Participant"))

init_db()

def all_students():
    with connect() as con:
        return con.execute("SELECT * FROM students ORDER BY full_name").fetchall()

@app.route("/")
def index():
    q = request.args.get("q","").strip()
    with connect() as con:
        if q:
            students = con.execute("SELECT * FROM students WHERE full_name LIKE ? OR roll_no LIKE ? ORDER BY full_name", (f"%{q}%",f"%{q}%")).fetchall()
        else:
            students = con.execute("SELECT * FROM students ORDER BY full_name").fetchall()
        stats = {
            "students": con.execute("SELECT COUNT(*) FROM students").fetchone()[0],
            "semesters": con.execute("SELECT COUNT(*) FROM semesters").fetchone()[0],
            "activities": con.execute("SELECT COUNT(*) FROM activities").fetchone()[0],
            "seminars": con.execute("SELECT COUNT(*) FROM seminars").fetchone()[0],
        }
    return render_template("index.html", students=students, stats=stats, q=q)

@app.route("/students/add", methods=["POST"])
def add_student():
    try:
        with connect() as con:
            con.execute("""INSERT INTO students(roll_no,full_name,email,department,admission_year,secondary_percent,higher_secondary_percent,current_status)
                VALUES(?,?,?,?,?,?,?,?)""", (
                request.form["roll_no"].strip(), request.form["full_name"].strip(),
                request.form.get("email","").strip() or None, request.form.get("department","Electrical and Computer Engineering").strip(),
                int(request.form["admission_year"]) if request.form.get("admission_year") else None,
                float(request.form["secondary_percent"]) if request.form.get("secondary_percent") else None,
                float(request.form["higher_secondary_percent"]) if request.form.get("higher_secondary_percent") else None,
                request.form.get("current_status","Active")))
        flash("Student added successfully.", "success")
    except (sqlite3.IntegrityError, ValueError) as e:
        flash(f"Could not add student: {e}", "error")
    return redirect(url_for("index"))

@app.route("/students/<int:sid>")
def student_detail(sid):
    with connect() as con:
        student = con.execute("SELECT * FROM students WHERE id=?",(sid,)).fetchone()
        if not student:
            flash("Student not found.", "error"); return redirect(url_for("index"))
        semesters = con.execute("SELECT * FROM semesters WHERE student_id=? ORDER BY semester_no",(sid,)).fetchall()
        activities = con.execute("""SELECT a.*, t.category FROM activities a JOIN activity_types t ON t.id=a.activity_type_id
            WHERE a.student_id=? ORDER BY a.activity_date DESC""",(sid,)).fetchall()
        seminars = con.execute("SELECT * FROM seminars WHERE student_id=? ORDER BY seminar_date DESC",(sid,)).fetchall()
        gaps = con.execute("SELECT * FROM gap_years WHERE student_id=? ORDER BY start_year",(sid,)).fetchall()
        marks = con.execute("""SELECT m.*,s.semester_no,sub.subject_code,sub.subject_name,sub.subject_type
            FROM marks m JOIN semesters s ON s.id=m.semester_id JOIN subjects sub ON sub.id=m.subject_id
            WHERE s.student_id=? ORDER BY s.semester_no,sub.subject_type,sub.subject_name""",(sid,)).fetchall()
        subjects = con.execute("SELECT * FROM subjects ORDER BY subject_type,subject_name").fetchall()
    chart = {"labels":[f"Sem {x['semester_no']}" for x in semesters],
             "sgpa":[x["sgpa"] for x in semesters], "cgpa":[x["cgpa"] for x in semesters]}
    return render_template("student.html", student=student, semesters=semesters, activities=activities,
        seminars=seminars, gaps=gaps, marks=marks, subjects=subjects, chart_json=json.dumps(chart))

@app.route("/students/<int:sid>/delete", methods=["POST"])
def delete_student(sid):
    with connect() as con:
        con.execute("DELETE FROM students WHERE id=?", (sid,))
    flash("Student and linked records deleted (ON DELETE CASCADE).", "success")
    return redirect(url_for("index"))

@app.route("/students/<int:sid>/semester", methods=["POST"])
def add_semester(sid):
    try:
        with connect() as con:
            con.execute("INSERT INTO semesters(student_id,semester_no,academic_year,sgpa,cgpa) VALUES(?,?,?,?,?)",
                (sid,int(request.form["semester_no"]),request.form.get("academic_year","").strip() or None,
                 float(request.form["sgpa"]) if request.form.get("sgpa") else None,
                 float(request.form["cgpa"]) if request.form.get("cgpa") else None))
        flash("Semester record saved.", "success")
    except (sqlite3.IntegrityError, ValueError) as e: flash(f"Could not save semester: {e}", "error")
    return redirect(url_for("student_detail",sid=sid))

@app.route("/students/<int:sid>/subject", methods=["POST"])
def add_subject(sid):
    try:
        with connect() as con:
            con.execute("INSERT INTO subjects(subject_code,subject_name,subject_type) VALUES(?,?,?)",
                (request.form["subject_code"].strip().upper(),request.form["subject_name"].strip(),request.form["subject_type"]))
        flash("Subject created. Add its marks in the marks section using the subject and semester IDs in the database.", "success")
    except sqlite3.IntegrityError as e: flash(f"Could not create subject: {e}", "error")
    return redirect(url_for("student_detail",sid=sid))

@app.route("/students/<int:sid>/marks", methods=["POST"])
def add_marks(sid):
    try:
        with connect() as con:
            sem = con.execute("SELECT id FROM semesters WHERE student_id=? AND semester_no=?",(sid,int(request.form["semester_no"]))).fetchone()
            if not sem: raise ValueError("Add the semester record first.")
            con.execute("INSERT INTO marks(semester_id,subject_id,marks_obtained,max_marks) VALUES(?,?,?,?)",
                (sem["id"],int(request.form["subject_id"]),float(request.form["marks_obtained"]),float(request.form["max_marks"])))
        flash("Marks saved.", "success")
    except (sqlite3.IntegrityError, ValueError) as e: flash(f"Could not save marks: {e}", "error")
    return redirect(url_for("student_detail",sid=sid))

@app.route("/students/<int:sid>/activity", methods=["POST"])
def add_activity(sid):
    try:
        with connect() as con:
            tid = con.execute("SELECT id FROM activity_types WHERE category=?",(request.form["category"],)).fetchone()["id"]
            con.execute("INSERT INTO activities(student_id,activity_type_id,title,description,activity_date,achievement_level) VALUES(?,?,?,?,?,?)",
                (sid,tid,request.form["title"].strip(),request.form.get("description","").strip(),request.form.get("activity_date") or None,request.form.get("achievement_level","").strip()))
        flash("Activity saved.", "success")
    except (sqlite3.IntegrityError, ValueError) as e: flash(f"Could not save activity: {e}", "error")
    return redirect(url_for("student_detail",sid=sid))

@app.route("/students/<int:sid>/seminar", methods=["POST"])
def add_seminar(sid):
    try:
        with connect() as con:
            con.execute("INSERT INTO seminars(student_id,title,organizer_type,seminar_date,certificate_ref) VALUES(?,?,?,?,?)",
                (sid,request.form["title"].strip(),request.form["organizer_type"],request.form.get("seminar_date") or None,request.form.get("certificate_ref","").strip() or None))
        flash("Seminar saved.", "success")
    except sqlite3.IntegrityError as e: flash(f"Could not save seminar: {e}", "error")
    return redirect(url_for("student_detail",sid=sid))

@app.route("/students/<int:sid>/gap", methods=["POST"])
def add_gap(sid):
    try:
        with connect() as con:
            con.execute("INSERT INTO gap_years(student_id,start_year,end_year,reason) VALUES(?,?,?,?)",
                (sid,int(request.form["start_year"]),int(request.form["end_year"]),request.form.get("reason","").strip()))
        flash("Gap-year marker saved.", "success")
    except (sqlite3.IntegrityError, ValueError) as e: flash(f"Could not save gap year: {e}", "error")
    return redirect(url_for("student_detail",sid=sid))

@app.route("/export.csv")
def export_csv():
    with connect() as con:
        rows = con.execute("""SELECT st.roll_no,st.full_name,st.email,st.department,st.admission_year,st.secondary_percent,
            st.higher_secondary_percent,st.current_status,se.semester_no,se.academic_year,se.sgpa,se.cgpa
            FROM students st LEFT JOIN semesters se ON se.student_id=st.id ORDER BY st.roll_no,se.semester_no""").fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Roll No","Student Name","Email","Department","Admission Year","Secondary %","Higher Secondary %","Status","Semester","Academic Year","SGPA","CGPA"])
    writer.writerows([tuple(r) for r in rows])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition":"attachment; filename=student_progression_export.csv"})

def push_to_google_sheets():
    """One-way DB -> Google Sheets sync. Requires service_account.json and GOOGLE_SHEET_ID."""
    if not gspread or not Credentials:
        raise RuntimeError("Install gspread and google-auth first (pip install -r requirements.txt).")
    cred_path = os.path.join(APP_DIR, "service_account.json")
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
    if not os.path.exists(cred_path): raise RuntimeError("service_account.json is missing.")
    if not sheet_id: raise RuntimeError("Set GOOGLE_SHEET_ID environment variable.")
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(cred_path, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id)
    with connect() as con:
        rows = con.execute("""SELECT st.roll_no,st.full_name,st.email,st.department,st.admission_year,st.secondary_percent,
            st.higher_secondary_percent,st.current_status,se.semester_no,se.academic_year,se.sgpa,se.cgpa
            FROM students st LEFT JOIN semesters se ON se.student_id=st.id ORDER BY st.roll_no,se.semester_no""").fetchall()
    values = [["Roll No","Student Name","Email","Department","Admission Year","Secondary %","Higher Secondary %","Status","Semester","Academic Year","SGPA","CGPA"]]
    values.extend([[("" if v is None else v) for v in tuple(r)] for r in rows])
    ws = sheet.worksheet("Progression") if "Progression" in [w.title for w in sheet.worksheets()] else sheet.add_worksheet(title="Progression", rows=max(100,len(values)+10), cols=len(values[0]))
    ws.clear()
    ws.update(values, "A1")
    return len(rows)

@app.route("/sync", methods=["POST"])
def sync():
    try:
        n = push_to_google_sheets()
        msg = f"Synced {n} progression rows to Google Sheets."
        with connect() as con: con.execute("INSERT INTO sync_log(synced_at,status,message) VALUES(?,?,?)",(datetime.now().isoformat(timespec="seconds"),"success",msg))
        flash(msg,"success")
    except Exception as e:
        with connect() as con: con.execute("INSERT INTO sync_log(synced_at,status,message) VALUES(?,?,?)",(datetime.now().isoformat(timespec="seconds"),"error",str(e)))
        flash(f"Sync not completed: {e}","error")
    return redirect(request.referrer or url_for("index"))

@app.route("/health")
def health(): return jsonify({"status":"ok","database":os.path.basename(DB_PATH)})

if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
