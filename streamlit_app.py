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
    .metric-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; text-align: center; }
</style>
""", unsafe_allow_html=True)

# Ensure DB is initialized
database.init_db(seed=True)

st.markdown('<div class="main-title">🎓 Student Academic Progression & Portfolio DBMS</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Department of Computer Engineering &bull; Relational Database Management System</div>', unsafe_allow_html=True)

# Navigation
menu = ["📊 Dashboard", "👥 Student Directory", "📈 Progression & Profile", "➕ Register Student", "☁️ Google Sheets Sync"]
choice = st.sidebar.radio("Navigation Menu", menu)

stats = database.get_dashboard_stats()

if choice == "📊 Dashboard":
    st.subheader("System Performance & Academic Overview")
    
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
    st.subheader("Recent Registered Students")
    students = database.get_students()[:10]
    if students:
        df_students = pd.DataFrame([dict(s) for s in students])
        display_cols = ["roll_no", "full_name", "department", "admission_year", "current_semester", "current_status"]
        st.dataframe(df_students[display_cols], use_container_width=True)

elif choice == "👥 Student Directory":
    st.subheader("Student Directory & Filtering Hub")
    search = st.text_input("🔍 Search by Roll No or Student Name", "")
    status_filter = st.selectbox("Filter by Status", ["All", "Active", "Drop Year", "Graduated"])
    
    students = database.get_students(search_query=search, status_filter=status_filter)
    if students:
        df = pd.DataFrame([dict(s) for s in students])
        st.dataframe(df[["roll_no", "full_name", "email", "phone", "department", "admission_year", "secondary_percent", "higher_secondary_percent", "current_semester", "current_status"]], use_container_width=True)
    else:
        st.info("No matching student records found.")

elif choice == "📈 Progression & Profile":
    st.subheader("Student Academic Profile & Chart Progression")
    students = database.get_students()
    if students:
        student_options = {f"{s['roll_no']} - {s['full_name']}": s['id'] for s in students}
        selected_label = st.selectbox("Select Student Profile", list(student_options.keys()))
        student_id = student_options[selected_label]
        
        student = database.get_student_by_id(student_id)
        semesters = database.get_semesters_for_student(student_id)
        
        # Profile Header
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**Full Name:** {student['full_name']}")
            st.write(f"**Roll Number:** {student['roll_no']}")
        with col2:
            st.write(f"**Department:** {student['department']}")
            st.write(f"**Admission Year:** {student['admission_year']}")
        with col3:
            st.write(f"**10th Secondary:** {student['secondary_percent']}%")
            st.write(f"**12th Higher Secondary:** {student['higher_secondary_percent']}%")

        st.markdown("---")
        
        # Chart Progression
        if semesters:
            st.write("### 📈 SGPA & CGPA Academic Progression Curve")
            chart_df = pd.DataFrame({
                "Semester": [f"Sem {s['semester_no']}" for s in semesters],
                "SGPA": [s["sgpa"] for s in semesters],
                "CGPA": [s["cgpa"] for s in semesters]
            }).set_index("Semester")
            st.line_chart(chart_df)
            
            st.write("### 📝 Semester Records & Marks")
            sem_df = pd.DataFrame([dict(s) for s in semesters])
            st.dataframe(sem_df[["semester_no", "academic_year", "sgpa", "cgpa", "status", "remarks"]], use_container_width=True)
        else:
            st.warning("No semester records found for this student.")
    else:
        st.info("No students registered yet.")

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
            department = st.selectbox("Department", ["Computer Engineering", "Information Technology", "AI & Data Science"])
            admission_year = st.number_input("Admission Year *", min_value=2015, max_value=2030, value=2024)
            secondary_percent = st.number_input("10th Secondary Percentage (%)", min_value=0.0, max_value=100.0, value=85.0)
            higher_secondary_percent = st.number_input("12th Higher Secondary Percentage (%)", min_value=0.0, max_value=100.0, value=82.0)
            current_semester = st.number_input("Current Semester", min_value=1, max_value=8, value=1)
            current_status = st.selectbox("Status", ["Active", "Drop Year", "Graduated"])

        submitted = st.form_submit_button("Register Student & Sync")
        if submitted:
            if not roll_no or not full_name:
                st.error("Roll Number and Full Name are mandatory.")
            else:
                try:
                    sid = database.create_student(
                        roll_no=roll_no,
                        full_name=full_name,
                        email=email,
                        phone=phone,
                        department=department,
                        admission_year=admission_year,
                        secondary_percent=secondary_percent,
                        higher_secondary_percent=higher_secondary_percent,
                        current_semester=current_semester,
                        current_status=current_status
                    )
                    st.success(f"Student '{full_name}' ({roll_no}) registered successfully!")
                    # Auto sync to sheets
                    success, msg, _ = sheets_sync.perform_sync(sync_type="Auto")
                    if success:
                        st.info("📊 Automatically synchronized to Google Sheets!")
                except Exception as e:
                    st.error(f"Error registering student: {e}")

elif choice == "☁️ Google Sheets Sync":
    st.subheader("Google Sheets Synchronization Hub")
    st.write("Direct live connection to **Google Spreadsheet**.")
    
    if st.button("🚀 Trigger Instant Sync Now"):
        with st.spinner("Synchronizing all normalized tables to Google Sheets..."):
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
