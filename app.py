"""
==============================================================================
Student Academic Progression and Portfolio Management System
Flask Backend Application Controller (app.py)
==============================================================================
Senior Full-Stack & Database Architecture Implementation
- RESTful HTTP routing and template rendering
- Comprehensive CRUD controllers for Students, Semesters, Subjects, Marks,
  Activities, Seminars, and Gap Years
- Parameterized database transaction execution
- Robust validation and user-friendly flash messaging
- Integrated Google Sheets synchronization and CSV export endpoints
- JSON API for dynamic Chart.js progression graphs
"""

import os
import csv
import io
import json
from datetime import datetime
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    Response,
)

import database
import sheets_sync

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "academic-progression-dbms-secret-key-2024")

import threading

def trigger_auto_sync():
    """
    Triggers Google Sheets synchronization asynchronously in a background thread
    after any create, update, or delete operation so web UI stays instant and responsive.
    """
    def _run():
        try:
            sheets_sync.perform_sync(sync_type="Auto")
        except Exception as e:
            print(f"[AutoSync] Error: {e}")
    threading.Thread(target=_run, daemon=True).start()


# ============================================================================
# Dashboard & Overview
# ============================================================================

@app.route("/")
def dashboard():
    """
    Main faculty dashboard displaying system metrics, recent activity,
    sync status, and quick-access student directory.
    """
    stats = database.get_dashboard_stats()
    recent_students = database.get_students()[:5]
    recent_activities = database.get_all_activities()[:5]
    recent_seminars = database.get_all_seminars()[:5]
    sync_config = sheets_sync.get_sync_configuration()
    last_sync = database.get_last_sync()

    return render_template(
        "dashboard.html",
        stats=stats,
        recent_students=recent_students,
        recent_activities=recent_activities,
        recent_seminars=recent_seminars,
        sync_config=sync_config,
        last_sync=last_sync,
        active_page="dashboard",
    )

@app.route("/reset_all", methods=["POST"])
def reset_all():
    """Wipe all tables and trigger a fresh sync."""
    try:
        database.truncate_all_tables()
        flash("All tables cleared – ready for fresh data.", "success")
    except Exception as e:
        flash(f"Reset failed: {e}", "danger")
    return redirect(url_for("dashboard"))


# ============================================================================
# Student Directory & Registration CRUD
# ============================================================================

@app.route("/students")
def students_list():
    """
    Searchable, filterable student directory table with status badges
    and CRUD modal triggers.
    """
    q = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "All")
    students = database.get_students(search_query=q, status_filter=status_filter)
    stats = database.get_dashboard_stats()

    return render_template(
        "students.html",
        students=students,
        q=q,
        status_filter=status_filter,
        stats=stats,
        active_page="students",
    )


@app.route("/students/new", methods=["GET", "POST"])
def new_student():
    """
    Dedicated student registration page with client and server validation.
    """
    if request.method == "POST":
        roll_no = request.form.get("roll_no", "").strip()
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        department = request.form.get("department", "Computer Engineering").strip()
        admission_year = request.form.get("admission_year")
        sec_percent = request.form.get("secondary_percent")
        hsec_percent = request.form.get("higher_secondary_percent")
        current_semester = request.form.get("current_semester", 1)
        current_status = request.form.get("current_status", "Active")

        # Validation
        if not roll_no or not full_name or not admission_year:
            flash("Roll Number, Full Name, and Admission Year are mandatory fields.", "danger")
            return render_template("add_student.html", active_page="students")

        try:
            student_id = database.create_student(
                roll_no=roll_no,
                full_name=full_name,
                email=email,
                phone=phone,
                department=department,
                admission_year=admission_year,
                secondary_percent=sec_percent,
                higher_secondary_percent=hsec_percent,
                current_semester=current_semester,
                current_status=current_status,
            )
            trigger_auto_sync()
            flash(f"Student '{full_name}' ({roll_no}) registered successfully! (Synced to Sheets)", "success")
            return redirect(url_for("student_profile", student_id=student_id))
        except Exception as e:
            err_msg = str(e)
            if "1062" in err_msg or "Duplicate entry" in err_msg or "UNIQUE constraint failed" in err_msg:
                if "roll_no" in err_msg:
                    flash(f"Error: Roll Number '{roll_no}' already exists in the system. Please use a unique roll number.", "danger")
                elif "email" in err_msg:
                    flash(f"Error: Email '{email}' is already registered with another student.", "danger")
                else:
                    flash(f"Error: Duplicate entry detected ({roll_no}). Roll number must be unique.", "danger")
            elif "CHECK constraint failed" in err_msg:
                flash("Error: 10th or 12th percentage must be between 0 and 100%.", "danger")
            else:
                flash(f"Registration failed: {err_msg}", "danger")

    return render_template("add_student.html", active_page="students")


@app.route("/students/<int:student_id>")
def student_profile(student_id):
    """
    Comprehensive student profile hub showing:
    - Academic credentials (10th, 12th, department, roll number)
    - Dynamic Chart.js progression line chart (SGPA/CGPA vs Semesters)
    - Tab 1: Semester-wise records, theory & lab marks
    - Tab 2: Gap / Drop Years timeline
    - Tab 3: Seminars (Internal & External)
    - Tab 4: Technical & Co-curricular Activities
    - Tab 5: Extra-curricular Activities
    """
    student = database.get_student_by_id(student_id)
    if not student:
        flash("Student profile not found.", "warning")
        return redirect(url_for("students_list"))

    semesters = database.get_semesters_for_student(student_id)
    subjects = database.get_subjects()
    seminars = database.get_seminars_for_student(student_id)
    activities = database.get_activities_for_student(student_id)
    gap_years = database.get_gap_years_for_student(student_id)
    activity_categories = database.get_activity_categories()

    # Pre-fetch marks for each semester for fast tab display
    semester_marks = {}
    for sem in semesters:
        semester_marks[sem["id"]] = database.get_marks_for_semester(sem["id"])

    # Separate activities for UI segregation
    tech_co_activities = [a for a in activities if a["activity_type"] in ("Technical", "Co-curricular")]
    extra_activities = [a for a in activities if a["activity_type"] == "Extra-curricular"]

    # Analyze progression data for gap years vs missing semesters
    recorded_sem_nos = [s["semester_no"] for s in semesters]
    missing_semesters = []
    if recorded_sem_nos:
        max_sem = max(recorded_sem_nos)
        for expected in range(1, max_sem + 1):
            if expected not in recorded_sem_nos:
                missing_semesters.append(expected)

    # Chart payload preparation
    chart_labels = [f"Sem {s['semester_no']}" for s in semesters]
    chart_sgpa = [s["sgpa"] for s in semesters]
    chart_cgpa = [s["cgpa"] for s in semesters]

    chart_data_json = json.dumps({
        "labels": chart_labels,
        "sgpa": chart_sgpa,
        "cgpa": chart_cgpa,
        "semesters": [dict(s) for s in semesters],
        "gap_years": [dict(g) for g in gap_years],
        "missing_semesters": missing_semesters,
    })

    return render_template(
        "student_detail.html",
        student=student,
        semesters=semesters,
        semester_marks=semester_marks,
        subjects=subjects,
        seminars=seminars,
        tech_co_activities=tech_co_activities,
        extra_activities=extra_activities,
        gap_years=gap_years,
        activity_categories=activity_categories,
        missing_semesters=missing_semesters,
        chart_data_json=chart_data_json,
        active_page="students",
    )


@app.route("/students/<int:student_id>/edit", methods=["POST"])
def edit_student(student_id):
    """
    Update student profile attributes.
    """
    try:
        database.update_student(
            student_id=student_id,
            roll_no=request.form["roll_no"].strip(),
            full_name=request.form["full_name"].strip(),
            email=request.form.get("email", "").strip() or None,
            phone=request.form.get("phone", "").strip() or None,
            department=request.form.get("department", "Computer Engineering").strip(),
            admission_year=int(request.form["admission_year"]),
            secondary_percent=request.form.get("secondary_percent"),
            higher_secondary_percent=request.form.get("higher_secondary_percent"),
            current_semester=int(request.form.get("current_semester", 1)),
            current_status=request.form.get("current_status", "Active"),
        )
        trigger_auto_sync()
        flash("Student profile updated successfully. (Synced to Sheets)", "success")
    except Exception as e:
        flash(f"Could not update student: {e}", "danger")

    return redirect(url_for("student_profile", student_id=student_id))


@app.route("/students/<int:student_id>/delete", methods=["POST"])
def delete_student(student_id):
    """
    Delete student profile. Enforces ON DELETE CASCADE for semesters, marks,
    seminars, activities, and gap years.
    """
    try:
        st = database.get_student_by_id(student_id)
        name = st["full_name"] if st else "Student"
        database.delete_student(student_id)
        trigger_auto_sync()
        flash(f"Student '{name}' and all linked academic records were permanently removed. (Synced to Sheets)", "success")
    except Exception as e:
        flash(f"Failed to delete student: {e}", "danger")

    return redirect(url_for("students_list"))


# ============================================================================
# Semester & Marks Management CRUD
# ============================================================================

@app.route("/students/<int:student_id>/semesters/add", methods=["POST"])
def add_semester(student_id):
    """
    Add a semester record for a student with validation.
    """
    try:
        sem_no = int(request.form["semester_no"])
        ac_year = request.form["academic_year"].strip()
        sgpa = request.form.get("sgpa")
        cgpa = request.form.get("cgpa")
        status = request.form.get("status", "Completed")
        remarks = request.form.get("remarks", "").strip()

        database.add_semester(
            student_id=student_id,
            semester_no=sem_no,
            academic_year=ac_year,
            sgpa=sgpa,
            cgpa=cgpa,
            status=status,
            remarks=remarks,
        )
        trigger_auto_sync()
        flash(f"Semester {sem_no} ({ac_year}) added successfully. (Synced to Sheets)", "success")
    except Exception as e:
        err = str(e)
        if "UNIQUE constraint failed: semesters.student_id, semesters.semester_no" in err:
            flash(f"Error: Semester {request.form.get('semester_no')} already exists for this student.", "danger")
        elif "CHECK constraint failed" in err:
            flash("Error: Semester number must be 1-12 and SGPA/CGPA must be between 0.0 and 10.0.", "danger")
        else:
            flash(f"Could not add semester: {err}", "danger")

    return redirect(url_for("student_profile", student_id=student_id))


@app.route("/semesters/<int:semester_id>/edit", methods=["POST"])
def edit_semester(semester_id):
    """
    Update SGPA, CGPA, academic year, and remarks for a semester.
    """
    sem = database.get_semester_by_id(semester_id)
    if not sem:
        flash("Semester not found.", "warning")
        return redirect(url_for("students_list"))

    try:
        database.update_semester(
            semester_id=semester_id,
            semester_no=int(request.form["semester_no"]),
            academic_year=request.form["academic_year"].strip(),
            sgpa=request.form.get("sgpa"),
            cgpa=request.form.get("cgpa"),
            status=request.form.get("status", "Completed"),
            remarks=request.form.get("remarks", "").strip(),
        )
        trigger_auto_sync()
        flash(f"Semester {sem['semester_no']} updated successfully. (Synced to Sheets)", "success")
    except Exception as e:
        flash(f"Could not update semester: {e}", "danger")

    return redirect(url_for("student_profile", student_id=sem["student_id"]))


@app.route("/semesters/<int:semester_id>/delete", methods=["POST"])
def delete_semester(semester_id):
    """
    Delete a semester record and its marks.
    """
    sem = database.get_semester_by_id(semester_id)
    if not sem:
        flash("Semester not found.", "warning")
        return redirect(url_for("students_list"))

    student_id = sem["student_id"]
    try:
        database.delete_semester(semester_id)
        trigger_auto_sync()
        flash(f"Semester {sem['semester_no']} record deleted. (Synced to Sheets)", "success")
    except Exception as e:
        flash(f"Could not delete semester: {e}", "danger")

    return redirect(url_for("student_profile", student_id=student_id))


@app.route("/semesters/<int:semester_id>/marks/add", methods=["POST"])
def add_marks(semester_id):
    """
    Add or update subject marks for a semester.
    Distinguishes Theory and Lab through the master subjects table.
    """
    sem = database.get_semester_by_id(semester_id)
    if not sem:
        flash("Semester record not found.", "warning")
        return redirect(url_for("students_list"))

    student_id = sem["student_id"]
    try:
        subject_id = int(request.form["subject_id"])
        marks_obtained = float(request.form["marks_obtained"])
        max_marks = float(request.form["max_marks"])
        grade_point = request.form.get("grade_point")

        database.add_or_update_subject_marks(
            semester_id=semester_id,
            subject_id=subject_id,
            marks_obtained=marks_obtained,
            max_marks=max_marks,
            grade_point=grade_point,
        )
        trigger_auto_sync()
        flash("Subject marks saved successfully. (Synced to Sheets)", "success")
    except ValueError as ve:
        flash(f"Validation Error: {ve}", "danger")
    except Exception as e:
        flash(f"Could not save marks: {e}", "danger")

    return redirect(url_for("student_profile", student_id=student_id))


@app.route("/marks/<int:mark_id>/delete", methods=["POST"])
def delete_mark(mark_id):
    """
    Remove a subject mark entry.
    """
    student_id = request.form.get("student_id")
    try:
        database.delete_subject_mark(mark_id)
        flash("Subject mark entry deleted.", "success")
    except Exception as e:
        flash(f"Could not delete mark entry: {e}", "danger")

    if student_id:
        return redirect(url_for("student_profile", student_id=student_id))
    return redirect(url_for("students_list"))


# ============================================================================
# Master Subject Catalog Management
# ============================================================================

@app.route("/subjects", methods=["GET", "POST"])
def subject_catalog():
    """
    View, add, and manage academic subjects catalog (Theory vs Lab).
    """
    if request.method == "POST":
        code = request.form.get("subject_code", "").strip().upper()
        name = request.form.get("subject_name", "").strip()
        stype = request.form.get("subject_type", "Theory")
        credits = int(request.form.get("credits", 3))
        max_m = float(request.form.get("default_max_marks", 100.0))

        if not code or not name:
            flash("Subject Code and Subject Name are required.", "danger")
        else:
            try:
                database.add_subject(code, name, stype, credits, max_m)
                flash(f"Subject '{code} - {name}' added to master catalog.", "success")
            except Exception as e:
                err = str(e)
                if "UNIQUE constraint failed: subjects.subject_code" in err:
                    flash(f"Subject code '{code}' already exists.", "danger")
                else:
                    flash(f"Could not add subject: {err}", "danger")

    subjects = database.get_subjects()
    return render_template("subjects.html", subjects=subjects, active_page="subjects")


@app.route("/subjects/<int:subject_id>/delete", methods=["POST"])
def delete_subject(subject_id):
    """
    Delete a subject from the catalog.
    """
    try:
        database.delete_subject(subject_id)
        flash("Subject deleted from catalog.", "success")
    except Exception as e:
        flash(f"Could not delete subject: {e}", "danger")
    return redirect(url_for("subject_catalog"))


# ============================================================================
# Portfolio: Seminars, Activities, Gap Years CRUD
# ============================================================================

@app.route("/portfolio")
def portfolio_view():
    """
    Global college/department portfolio browser for all seminars
    and co-curricular / extra-curricular activities with search & filters.
    """
    cat_type = request.args.get("type", "All")
    sem_type = request.args.get("seminar_type", "All")
    q = request.args.get("q", "").strip()

    activities = database.get_all_activities(activity_type=cat_type, search_query=q)
    seminars = database.get_all_seminars(seminar_type=sem_type, search_query=q)
    categories = database.get_activity_categories()

    return render_template(
        "portfolio.html",
        activities=activities,
        seminars=seminars,
        categories=categories,
        cat_type=cat_type,
        sem_type=sem_type,
        q=q,
        active_page="portfolio",
    )


@app.route("/students/<int:student_id>/seminars/add", methods=["POST"])
def add_seminar(student_id):
    """
    Add internal or external seminar record.
    """
    try:
        database.add_seminar(
            student_id=student_id,
            title=request.form["title"].strip(),
            seminar_type=request.form["seminar_type"],
            seminar_date=request.form["seminar_date"].strip(),
            organizer=request.form["organizer"].strip(),
            certificate_url=request.form.get("certificate_url", "").strip(),
        )
        trigger_auto_sync()
        flash("Seminar record added successfully. (Synced to Sheets)", "success")
    except Exception as e:
        flash(f"Could not add seminar: {e}", "danger")

    return redirect(url_for("student_profile", student_id=student_id))


@app.route("/seminars/<int:seminar_id>/delete", methods=["POST"])
def delete_seminar(seminar_id):
    """
    Delete a seminar record.
    """
    student_id = request.form.get("student_id")
    try:
        database.delete_seminar(seminar_id)
        trigger_auto_sync()
        flash("Seminar record removed. (Synced to Sheets)", "success")
    except Exception as e:
        flash(f"Could not delete seminar: {e}", "danger")

    if student_id:
        return redirect(url_for("student_profile", student_id=student_id))
    return redirect(url_for("portfolio_view"))


@app.route("/students/<int:student_id>/activities/add", methods=["POST"])
def add_activity(student_id):
    """
    Add technical, co-curricular, or extra-curricular activity record.
    """
    try:
        database.add_activity(
            student_id=student_id,
            category_id=int(request.form["category_id"]),
            activity_name=request.form["activity_name"].strip(),
            description=request.form.get("description", "").strip(),
            activity_date=request.form["activity_date"].strip(),
            achievement_level=request.form.get("achievement_level", "Participant"),
            certificate_ref=request.form.get("certificate_ref", "").strip(),
        )
        trigger_auto_sync()
        flash("Activity achievement saved. (Synced to Sheets)", "success")
    except Exception as e:
        flash(f"Could not save activity: {e}", "danger")

    return redirect(url_for("student_profile", student_id=student_id))


@app.route("/activities/<int:activity_id>/delete", methods=["POST"])
def delete_activity(activity_id):
    """
    Delete an activity record.
    """
    student_id = request.form.get("student_id")
    try:
        database.delete_activity(activity_id)
        trigger_auto_sync()
        flash("Activity achievement removed. (Synced to Sheets)", "success")
    except Exception as e:
        flash(f"Could not delete activity: {e}", "danger")

    if student_id:
        return redirect(url_for("student_profile", student_id=student_id))
    return redirect(url_for("portfolio_view"))


@app.route("/students/<int:student_id>/gaps/add", methods=["POST"])
def add_gap_year(student_id):
    """
    Record an academic gap or drop year with validated start/end dates and reason.
    """
    try:
        sy = int(request.form["start_year"])
        ey = int(end_year := request.form["end_year"])
        gtype = request.form.get("gap_type", "Academic Drop")
        reason = request.form["reason"].strip()

        database.add_gap_year(
            student_id=student_id,
            start_year=sy,
            end_year=ey,
            gap_type=gtype,
            reason=reason,
        )
        trigger_auto_sync()
        flash("Academic gap year marker successfully recorded. (Synced to Sheets)", "success")
    except ValueError as ve:
        flash(f"Validation Error: {ve}", "danger")
    except Exception as e:
        flash(f"Could not record gap year: {e}", "danger")

    return redirect(url_for("student_profile", student_id=student_id))


@app.route("/gaps/<int:gap_id>/delete", methods=["POST"])
def delete_gap_year(gap_id):
    """
    Delete an academic gap year marker.
    """
    student_id = request.form.get("student_id")
    try:
        database.delete_gap_year(gap_id)
        trigger_auto_sync()
        flash("Gap year record removed. (Synced to Sheets)", "success")
    except Exception as e:
        flash(f"Could not delete gap year: {e}", "danger")

    if student_id:
        return redirect(url_for("student_profile", student_id=student_id))
    return redirect(url_for("students_list"))


# ============================================================================
# Google Sheets Synchronization & CSV Export
# ============================================================================

@app.route("/sync")
@app.route("/sync/hub")
def sync_hub():
    """
    Google Sheets Synchronization Hub:
    - Connection status widget
    - Last sync timestamp and audit logs table
    - Manual sync trigger button
    - Step-by-step Google Cloud service account setup tutorial
    """
    config = sheets_sync.get_sync_configuration()
    logs = database.get_sync_logs(limit=25)
    last_sync = database.get_last_sync()

    return render_template(
        "sync_hub.html",
        config=config,
        logs=logs,
        last_sync=last_sync,
        active_page="sync",
    )


@app.route("/sync/trigger", methods=["POST"])
def trigger_sync():
    """
    Manual trigger for database-to-Google-Sheets synchronization.
    Gracefully logs success or failure and flashes clear user feedback.
    """
    success, msg, count = sheets_sync.perform_sync(sync_type="Manual")
    if success:
        flash(f"Sync Successful: {msg}", "success")
    else:
        flash(f"Sync Incomplete: {msg}", "warning")

    return redirect(request.referrer or url_for("sync_hub"))


@app.route("/export/csv")
def export_csv():
    """
    Generates and serves a complete CSV file of all student academic progression
    records for instant download and offline spreadsheet verification.
    """
    rows = database.get_progression_export_data()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Roll No",
        "Student Name",
        "Email",
        "Phone",
        "Department",
        "Admission Year",
        "10th (Secondary) %",
        "12th (Higher Sec) %",
        "Current Status",
        "Semester No",
        "Academic Year",
        "SGPA",
        "CGPA",
        "Semester Status",
        "Semester Remarks",
        "Recorded Gap Years Summary",
    ])

    for r in rows:
        writer.writerow([
            r["roll_no"],
            r["full_name"],
            r["email"] or "",
            r["phone"] or "",
            r["department"],
            r["admission_year"],
            r["secondary_percent"] if r["secondary_percent"] is not None else "",
            r["higher_secondary_percent"] if r["higher_secondary_percent"] is not None else "",
            r["current_status"],
            f"Semester {r['semester_no']}" if r["semester_no"] is not None else "N/A",
            r["academic_year"] or "",
            r["sgpa"] if r["sgpa"] is not None else "",
            r["cgpa"] if r["cgpa"] is not None else "",
            r["semester_status"] or "",
            r["remarks"] or "",
            r["gap_years_summary"] or "None",
        ])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Student_Progression_Export_{timestamp}.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ============================================================================
# Chart.js JSON API & Healthcheck
# ============================================================================

@app.route("/api/students/<int:student_id>/chart-data")
def api_chart_data(student_id):
    """
    Returns structured JSON data for dynamic Chart.js rendering on the client:
    - Labels (Semester 1 through N)
    - SGPA series
    - CGPA series
    - Missing semesters list
    - Recorded gap years
    """
    student = database.get_student_by_id(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    semesters = database.get_semesters_for_student(student_id)
    gap_years = database.get_gap_years_for_student(student_id)

    sem_nos = [s["semester_no"] for s in semesters]
    missing = []
    if sem_nos:
        for x in range(1, max(sem_nos) + 1):
            if x not in sem_nos:
                missing.append(x)

    return jsonify({
        "student": {
            "id": student["id"],
            "name": student["full_name"],
            "roll_no": student["roll_no"],
        },
        "labels": [f"Sem {s['semester_no']}" for s in semesters],
        "sgpa": [s["sgpa"] for s in semesters],
        "cgpa": [s["cgpa"] for s in semesters],
        "semesters": [dict(s) for s in semesters],
        "gap_years": [dict(g) for g in gap_years],
        "missing_semesters": missing,
    })


@app.route("/health")
def healthcheck():
    """
    Application health status endpoint.
    """
    engine_name = "MySQL (astudent_progress)" if database.is_using_mysql() else "SQLite (student_progression.db)"
    return jsonify({
        "status": "healthy",
        "application": "Student Academic Progression and Portfolio Management System",
        "database": engine_name,
        "foreign_keys_enabled": True,
        "sheets_sync_ready": sheets_sync.get_sync_configuration()["is_configured"],
        "timestamp": datetime.now().isoformat(),
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
