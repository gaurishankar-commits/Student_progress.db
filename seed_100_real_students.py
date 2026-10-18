"""
Seed 100 Realistic Indian Engineering Students with comprehensive 3NF relationships:
- Unique Indian full names & unique roll numbers (across CE, IT, AIDS, EXTC, MECH)
- Realistic 10th & 12th marks (60% to 98%)
- 1 to 8 Semesters with accurate SGPA and CGPA trends
- Subject marks (Theory and Lab) with grade points
- Academic gap/drop years (medical, preparation, drop)
- Technical hackathons, research papers, workshops, sports, cultural activities
- Internal & external seminars
"""

import random
import pymysql
import database
import sheets_sync

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Reyansh", "Muhammad", "Sai", "Arnav", "Ayaan",
    "Krishna", "Ishaan", "Shaurya", "Atharva", "Advik", "Pranav", "Advaith", "Aaryan", "Dhruv", "Kabir",
    "Ananya", "Diya", "Isha", "Riya", "Aadhya", "Pari", "Saanvi", "Aarohi", "Navya", "Kiara",
    "Avani", "Myra", "Sara", "Anika", "Kavya", "Khushi", "Aditi", "Ira", "Meera", "Tanvi",
    "Rohan", "Rahul", "Sameer", "Varun", "Karan", "Kunal", "Nikhil", "Gaurav", "Siddharth", "Manish",
    "Pooja", "Sneha", "Neha", "Simran", "Deepika", "Shreya", "Anjali", "Swati", "Rashmi", "Divya",
    "Harsh", "Yash", "Ayush", "Om", "Dev", "Alok", "Chirag", "Tushar", "Abhishek", "Mayank",
    "Priyanka", "Preeti", "Suman", "Vandana", "Meenakshi", "Sunita", "Reena", "Pallavi", "Kajal", "Komal",
    "Vikram", "Rajesh", "Suresh", "Mahesh", "Dinesh", "Ganesh", "Ramesh", "Mukesh", "Naresh", "Bhupesh",
    "Sakshi", "Bhavna", "Kritika", "Nidhi", "Garima", "Akanksha", "Monika", "Payal", "Rachna", "Ritu"
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Malhotra", "Bhatia", "Saxena", "Mehta", "Chopra", "Joshi", "Patel",
    "Shah", "Deshmukh", "Kulkarni", "Patil", "Pawar", "Shinde", "Jadhav", "More", "Gaekwad", "Chavan",
    "Singh", "Kumar", "Yadav", "Mishra", "Pandey", "Tiwari", "Dubey", "Shukla", "Tripathi", "Pathak",
    "Reddy", "Rao", "Nair", "Menon", "Pillai", "Iyer", "Iyengar", "Murthy", "Shetty", "Hegde",
    "Banerjee", "Chatterjee", "Mukherjee", "Dutta", "Ghosh", "Bose", "Das", "Sarkar", "Roy", "Sen"
]

DEPARTMENTS = [
    ("Computer Engineering", "CE"),
    ("Information Technology", "IT"),
    ("Artificial Intelligence & Data Science", "AI"),
    ("Electronics & Telecommunication", "EXTC"),
    ("Mechanical Engineering", "ME")
]

ACHIEVEMENT_LEVELS = ["Winner", "Runner-up", "Participant", "College Level", "State Level", "National Level", "International Level"]

def generate_100_students():
    print("[100_Students] Clearing previous demonstration records from MySQL...")
    with database.get_db() as conn:
        conn.execute("SET FOREIGN_KEY_CHECKS = 0;")
        for tbl in ['semester_subject_marks', 'semesters', 'seminars', 'activities', 'gap_years', 'students']:
            conn.execute(f"TRUNCATE TABLE `{tbl}`;")
        conn.execute("SET FOREIGN_KEY_CHECKS = 1;")

        # Fetch subjects and activity categories
        subjects = conn.execute("SELECT id, subject_code, default_max_marks FROM subjects").fetchall()
        categories = conn.execute("SELECT id, name, activity_type FROM activity_categories").fetchall()

        used_rolls = set()
        used_emails = set()

        print("[100_Students] Generating 100 realistic student academic portfolios...")
        
        for i in range(1, 101):
            fn = FIRST_NAMES[(i - 1) % len(FIRST_NAMES)]
            ln = LAST_NAMES[((i - 1) * 3 + 7) % len(LAST_NAMES)]
            full_name = f"{fn} {ln}"
            
            dept_name, dept_code = DEPARTMENTS[i % len(DEPARTMENTS)]
            
            # Admission year between 2020 and 2024
            adm_year = 2020 + (i % 5)
            
            # Roll number format: e.g. CE-2022-015
            roll_no = f"{dept_code}-{adm_year}-{i:03d}"
            while roll_no in used_rolls:
                roll_no = f"{dept_code}-{adm_year}-{random.randint(100, 999)}"
            used_rolls.add(roll_no)

            email_prefix = f"{fn.lower()}.{ln.lower()}{i}"
            email = f"{email_prefix}@viva-technology.edu"
            used_emails.add(email)

            phone = f"+91 {random.randint(70, 99)}{random.randint(1000, 9999)} {random.randint(1000, 9999)}"
            
            sec_percent = round(random.uniform(72.0, 98.5), 2)
            hsec_percent = round(min(sec_percent + random.uniform(-6.0, 4.0), 99.0), 2)

            # Determine semesters based on admission year
            # 2020 -> Graduated (Sem 8)
            # 2021 -> Sem 7 or 8
            # 2022 -> Sem 5 or 6
            # 2023 -> Sem 3 or 4
            # 2024 -> Sem 1 or 2
            current_sem = min(max(1, (2025 - adm_year) * 2), 8)
            status = "Graduated" if current_sem >= 8 and adm_year <= 2020 else ("Drop Year" if i in [14, 45, 78] else "Active")

            # 1. Insert Student
            cur = conn.execute("""
                INSERT INTO students (
                    roll_no, full_name, email, phone, department, admission_year,
                    secondary_percent, higher_secondary_percent, current_semester, current_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                roll_no, full_name, email, phone, dept_name, adm_year,
                sec_percent, hsec_percent, current_sem, status
            ))
            student_id = cur.lastrowid

            # 2. Insert Semesters & Marks for this student
            base_gpa = round(random.uniform(6.5, 9.4), 2)
            cum_points = 0.0

            for sem_no in range(1, current_sem + 1):
                # Small SGPA variation
                sgpa = round(min(10.0, max(5.0, base_gpa + random.uniform(-0.6, 0.6))), 2)
                cum_points += sgpa
                cgpa = round(cum_points / sem_no, 2)
                
                sem_year_start = adm_year + (sem_no - 1) // 2
                academic_year = f"{sem_year_start}-{sem_year_start + 1}"
                sem_status = "Completed" if sem_no < current_sem or status == "Graduated" else "Ongoing"

                sem_cur = conn.execute("""
                    INSERT INTO semesters (
                        student_id, semester_no, academic_year, sgpa, cgpa, status, remarks
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    student_id, sem_no, academic_year, sgpa, cgpa, sem_status, f"Semester {sem_no} performance recorded"
                ))
                semester_id = sem_cur.lastrowid

                # Add subject marks for each semester
                # Choose 2 theory and 1 lab subject from subjects list
                sub_sample = random.sample(subjects, min(3, len(subjects)))
                for sub in sub_sample:
                    max_m = float(sub["default_max_marks"])
                    # Marks proportional to SGPA
                    obtained = round(min(max_m, max(max_m * 0.45, (sgpa / 10.0) * max_m + random.uniform(-4, 4))), 1)
                    gp = round((obtained / max_m) * 10.0, 2)
                    
                    conn.execute("""
                        INSERT INTO semester_subject_marks (
                            semester_id, subject_id, marks_obtained, max_marks, grade_point
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (semester_id, sub["id"], obtained, max_m, gp))

            # 3. Add Drop / Gap Year for specific students (demonstrates gap year modeling)
            if i in [14, 45, 78]:
                gap_start = adm_year + 1
                conn.execute("""
                    INSERT INTO gap_years (
                        student_id, start_year, end_year, gap_type, reason
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    student_id, gap_start, gap_start + 1,
                    "Medical Leave" if i == 14 else ("Preparation / Transition" if i == 45 else "Academic Drop"),
                    "Underwent medical treatment and recuperated before rejoining the curriculum." if i == 14 else "Dedicated year for competitive entrance examination preparation."
                ))

            # 4. Add Activities (Every student gets 1 to 3 portfolio entries)
            num_activities = (i % 3) + 1
            for a_idx in range(num_activities):
                cat = random.choice(categories)
                ach_level = random.choice(ACHIEVEMENT_LEVELS)
                act_date = f"{adm_year + (a_idx % 3)}-{random.randint(1, 12):02d}-{random.randint(10, 28):02d}"
                conn.execute("""
                    INSERT INTO activities (
                        student_id, category_id, activity_name, description, activity_date, achievement_level, certificate_ref
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    student_id, cat["id"],
                    f"{cat['name']} Edition #{i+a_idx}",
                    f"Represented {dept_name} in {cat['name']} competition.",
                    act_date, ach_level, f"CERT-{dept_code}-{i:03d}-{a_idx+1}"
                ))

            # 5. Add Seminars (internal/external)
            if i % 2 == 0:
                conn.execute("""
                    INSERT INTO seminars (
                        student_id, title, seminar_type, seminar_date, organizer, certificate_url
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    student_id,
                    f"Emerging Trends in {dept_name} and Distributed Systems",
                    "External" if i % 4 == 0 else "Internal",
                    f"{adm_year + 1}-09-18",
                    "IEEE Student Branch & Department Technical Forum",
                    f"https://drive.google.com/cert/seminar-{roll_no}"
                ))

    print("[100_Students] SUCCESS: 100 students + all normalized relational records generated successfully!")

if __name__ == "__main__":
    generate_100_students()
    print("[100_Students] Synchronizing new 100 students dataset to Google Sheets...")
    success, msg, count = sheets_sync.perform_sync(sync_type="100-Students-Seed")
    print(f"[100_Students] Sheets Sync Status: {success} | Records: {count} | {msg}")
