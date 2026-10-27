import streamlit as st
import pandas as pd
import database
import sheets_sync

st.set_page_config(
    page_title="Student Academic Progression & Portfolio DBMS",
    page_icon="🎓",
    layout="wide"
)

# Custom Styling
st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: 700; color: #1a365d; margin-bottom: 0.2rem; }
    .sub-title { font-size: 1.05rem; color: #4a5568; margin-bottom: 1.5rem; }
    .stButton>button { border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# Ensure DB is initialized with seed data
database.init_db(seed=True)

st.markdown('<div class="main-title">🎓 Student Academic Progression & Portfolio DBMS</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Department of Computer Engineering &bull; Full CRUD &amp; Real-Time Google Sheets Synchronization</div>', unsafe_allow_html=True)

# Sidebar Navigation
menu = [
    "📊 Dashboard",
    "👥 Student Directory",
    "📈 Student Profile (CRUD)",
    "➕ Register Student",
    "☁️ Google Sheets Sync Hub"
]
choice = st.sidebar.radio("Navigation Menu", menu)

def sync_sheets():
    """Helper to sync immediately to Google Sheets and display notification."""
    with st.spinner("Pushing update to Google Sheets..."):
        success, msg, _ = sheets_sync.perform_sync(sync_type="Auto")
        if success:
            st.toast("✅ Google Sheet updated in real-time!", icon="📊")
        else:
            st.error(f"Google Sheets sync failed: {msg}")

# ==========================================
# 1. DASHBOARD
# ==========================================
if choice == "📊 Dashboard":
    st.subheader("System Performance & Academic Overview")
    stats = database.get_dashboard_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Students", stats["total_students"])
    with col2:
        st.metric("Semester Records", stats["total_semesters"])
    with col3:
        st.metric("Portfolio & Seminars", stats["total_seminars"] + stats["total_activities"])
    with col4:
        st.metric("Average CGPA", f"{stats['avg_cgpa']:.2f}")

    st.markdown("---")
    st.subheader("Registered Students Directory")
    students = database.get_students()
    if students:
        df_students = pd.DataFrame([dict(s) for s in students])
        display_cols = ["roll_no", "full_name", "department", "admission_year", "current_semester", "current_status"]
        st.dataframe(df_students[display_cols], use_container_width=True)

# ==========================================
# 2. STUDENT DIRECTORY (READ & FILTER)
# ==========================================
elif choice == "👥 Student Directory":
    st.subheader("Student Directory & Filtering Hub")
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔍 Search by Roll Number or Name", "")
    with col2:
        status_filter = st.selectbox("Status Filter", ["All", "Active", "Drop Year", "Graduated"])
    
    students = database.get_students(search_query=search, status_filter=status_filter)
    if students:
        df = pd.DataFrame([dict(s) for s in students])
        st.dataframe(df[["roll_no", "full_name", "email", "phone", "department", "admission_year", "secondary_percent", "higher_secondary_percent", "current_semester", "current_status"]], use_container_width=True)
    else:
        st.info("No matching students found.")

# ==========================================
# 3. STUDENT PROFILE & CRUD (UPDATE / DELETE)
# ==========================================
elif choice == "📈 Student Profile (CRUD)":
    st.subheader("Student Academic Profile, Marks & Record Management")
    students = database.get_students()
    
    if not students:
        st.info("No students registered yet.")
    else:
        student_options = {f"{s['roll_no']} — {s['full_name']}": s['id'] for s in students}
        selected_label = st.selectbox("Select Student to View or Manage", list(student_options.keys()))
        student_id = student_options[selected_label]
        
        student = database.get_student_by_id(student_id)
        semesters = database.get_semesters_for_student(student_id)
        
        tab_view, tab_edit, tab_sem, tab_delete = st.tabs(["📄 Academic Profile & Chart", "✏️ Edit Student", "➕ Add Semester / Marks", "🗑️ Delete Student"])
        
        # --- TAB: VIEW & CHARTS ---
        with tab_view:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Full Name:** {student['full_name']}")
                st.write(f"**Roll Number:** `{student['roll_no']}`")
                st.write(f"**Status:** `{student['current_status']}`")
            with col2:
                st.write(f"**Department:** {student['department']}")
                st.write(f"**Admission Year:** {student['admission_year']}")
                st.write(f"**Current Semester:** {student['current_semester']}")
            with col3:
                st.write(f"**Email:** {student['email'] or 'N/A'}")
                st.write(f"**Phone:** {student['phone'] or 'N/A'}")
                st.write(f"**10th / 12th %:** {student['secondary_percent']}% / {student['higher_secondary_percent']}%")
            
            st.markdown("---")
            if semesters:
                st.write("### 📈 SGPA & CGPA Academic Progression Curve")
                chart_df = pd.DataFrame({
                    "Semester": [f"Sem {s['semester_no']}" for s in semesters],
                    "SGPA": [float(s["sgpa"]) for s in semesters],
                    "CGPA": [float(s["cgpa"]) for s in semesters]
                }).set_index("Semester")
                st.line_chart(chart_df)
                
                st.write("### 📝 Semester Records")
                sem_df = pd.DataFrame([dict(s) for s in semesters])
                st.dataframe(sem_df[["semester_no", "academic_year", "sgpa", "cgpa", "status", "remarks"]], use_container_width=True)
            else:
                st.warning("No semester records found for this student. Use the '➕ Add Semester / Marks' tab above to add one.")

        # --- TAB: EDIT STUDENT (UPDATE) ---
        with tab_edit:
            st.write(f"### Update Student Details: {student['full_name']}")
            with st.form(f"edit_student_{student_id}"):
                c1, c2 = st.columns(2)
                with c1:
                    edit_roll = st.text_input("Roll Number", value=student["roll_no"])
                    edit_name = st.text_input("Full Name", value=student["full_name"])
                    edit_email = st.text_input("Email", value=student["email"] or "")
                    edit_phone = st.text_input("Phone", value=student["phone"] or "")
                with c2:
                    dept_list = ["Computer Engineering", "Information Technology", "AI & Data Science", "Electronics & Communication"]
                    cur_dept_idx = dept_list.index(student["department"]) if student["department"] in dept_list else 0
                    edit_dept = st.selectbox("Department", dept_list, index=cur_dept_idx)
                    edit_year = st.number_input("Admission Year", min_value=2015, max_value=2030, value=int(student["admission_year"]))
                    edit_sem = st.number_input("Current Semester", min_value=1, max_value=12, value=int(student["current_semester"]))
                    status_list = ["Active", "Drop Year", "Graduated"]
                    cur_st_idx = status_list.index(student["current_status"]) if student["current_status"] in status_list else 0
                    edit_status = st.selectbox("Status", status_list, index=cur_st_idx)
                
                update_btn = st.form_submit_button("💾 Save Changes & Sync to Google Sheets")
                if update_btn:
                    try:
                        database.update_student(
                            student_id=student_id,
                            roll_no=edit_roll.strip(),
                            full_name=edit_name.strip(),
                            email=edit_email.strip() or None,
                            phone=edit_phone.strip() or None,
                            department=edit_dept,
                            admission_year=edit_year,
                            secondary_percent=student["secondary_percent"],
                            higher_secondary_percent=student["higher_secondary_percent"],
                            current_semester=edit_sem,
                            current_status=edit_status
                        )
                        st.success("Student updated in database successfully!")
                        sync_sheets()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Update failed: {e}")

        # --- TAB: ADD SEMESTER & MARKS (CREATE) ---
        with tab_sem:
            st.write(f"### Add Semester Grades for {student['full_name']}")
            with st.form(f"add_sem_{student_id}"):
                sc1, sc2 = st.columns(2)
                with sc1:
                    new_sem_no = st.number_input("Semester Number (1-12)", min_value=1, max_value=12, value=len(semesters) + 1)
                    new_ac_year = st.text_input("Academic Year", value=f"{student['admission_year']}-{student['admission_year']+1}")
                with sc2:
                    new_sgpa = st.number_input("SGPA (0.00 - 10.00)", min_value=0.0, max_value=10.0, value=8.5, step=0.05)
                    new_cgpa = st.number_input("CGPA (0.00 - 10.00)", min_value=0.0, max_value=10.0, value=8.5, step=0.05)
                new_remarks = st.text_input("Remarks", value="Academic Progression")
                
                add_sem_btn = st.form_submit_button("➕ Add Semester Record & Sync")
                if add_sem_btn:
                    try:
                        database.add_semester(
                            student_id=student_id,
                            semester_no=new_sem_no,
                            academic_year=new_ac_year,
                            sgpa=new_sgpa,
                            cgpa=new_cgpa,
                            status="Completed",
                            remarks=new_remarks
                        )
                        st.success(f"Semester {new_sem_no} added successfully!")
                        sync_sheets()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding semester: {e}")

        # --- TAB: DELETE STUDENT (DELETE) ---
        with tab_delete:
            st.write(f"### Delete Student: `{student['roll_no']}` ({student['full_name']})")
            st.warning("⚠️ Warning: Deleting a student permanently removes their entire academic progression history, marks, and achievements via CASCADE delete.")
            if st.button("🗑️ Permanently Delete Student & Sync to Google Sheets", type="primary"):
                try:
                    database.delete_student(student_id)
                    st.success(f"Student '{student['full_name']}' permanently deleted!")
                    sync_sheets()
                    st.rerun()
                except Exception as e:
                    st.error(f"Deletion failed: {e}")

# ==========================================
# 4. REGISTER NEW STUDENT (CREATE)
# ==========================================
elif choice == "➕ Register Student":
    st.subheader("New Student Registration Form")
    with st.form("register_student_form"):
        col1, col2 = st.columns(2)
        with col1:
            roll_no = st.text_input("Roll Number *", placeholder="e.g. CE-2024-001")
            full_name = st.text_input("Full Name *", placeholder="e.g. Rajesh Kumar")
            email = st.text_input("Email", placeholder="e.g. rajesh@example.edu")
            phone = st.text_input("Phone", placeholder="+91 98765 43210")
        with col2:
            department = st.selectbox("Department", ["Computer Engineering", "Information Technology", "AI & Data Science", "Electronics & Communication"])
            admission_year = st.number_input("Admission Year *", min_value=2015, max_value=2030, value=2024)
            secondary_percent = st.number_input("10th Secondary Percentage (%)", min_value=0.0, max_value=100.0, value=85.0)
            higher_secondary_percent = st.number_input("12th Higher Secondary Percentage (%)", min_value=0.0, max_value=100.0, value=82.0)
            current_semester = st.number_input("Current Semester", min_value=1, max_value=8, value=1)
            current_status = st.selectbox("Status", ["Active", "Drop Year", "Graduated"])

        submitted = st.form_submit_button("Register Student & Sync to Google Sheets")
        if submitted:
            if not roll_no or not full_name:
                st.error("Roll Number and Full Name are mandatory.")
            else:
                try:
                    sid = database.create_student(
                        roll_no=roll_no.strip(),
                        full_name=full_name.strip(),
                        email=email.strip() or None,
                        phone=phone.strip() or None,
                        department=department,
                        admission_year=admission_year,
                        secondary_percent=secondary_percent,
                        higher_secondary_percent=higher_secondary_percent,
                        current_semester=current_semester,
                        current_status=current_status
                    )
                    st.success(f"Student '{full_name}' ({roll_no}) registered successfully!")
                    sync_sheets()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error registering student: {e}")

# ==========================================
# 5. GOOGLE SHEETS SYNC HUB
# ==========================================
elif choice == "☁️ Google Sheets Sync Hub":
    st.subheader("Google Sheets Synchronization Hub")
    st.write("Target Spreadsheet: **[STUDENT DATABASE - Google Sheets](https://docs.google.com/spreadsheets/d/14-FVo3H8LjybXtv_CWbphvgf46IZ1ahwf7mRlmwg29M/edit?gid=0#gid=0)**")
    
    if st.button("🚀 Trigger Instant Sync Now", type="primary"):
        with st.spinner("Pushing all 8 normalized database tables to Google Sheets..."):
            success, msg, count = sheets_sync.perform_sync(sync_type="Manual")
            if success:
                st.success(f"✅ {msg}")
            else:
                st.error(f"❌ Sync failed: {msg}")

    st.markdown("---")
    st.write("### Recent Synchronization Audit Log")
    logs = database.get_sync_logs()[:10]
    if logs:
        st.dataframe(pd.DataFrame([dict(l) for l in logs]), use_container_width=True)
