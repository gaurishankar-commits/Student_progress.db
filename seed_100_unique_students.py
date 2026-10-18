import random
from faker import Faker
from datetime import datetime
import database
from app import trigger_auto_sync

# Use Indian locale for realistic data
fake = Faker('en_IN')
random.seed(0)

def random_roll_number():
    year = random.randint(2019, 2023)
    seq = random.randint(1, 999)
    return f"CE-{year}-{seq:03d}"

def generate_indian_students(count=5):
    rolls = set()
    emails = set()
    students = []
    while len(students) < count:
        roll = random_roll_number()
        email = fake.unique.email()
        if roll in rolls or email in emails:
            continue
        rolls.add(roll)
        emails.add(email)
        students.append({
            "roll_no": roll,
            "full_name": fake.name(),
            "email": email,
            "phone": fake.phone_number(),
            "department": "Computer Engineering",
            "admission_year": random.randint(2019, 2023),
            "secondary_percent": round(random.uniform(70, 100), 2),
            "higher_secondary_percent": round(random.uniform(70, 100), 2),
            "current_semester": random.randint(1, 8),
            "current_status": "Active",
        })
    return students

def seed_five_per_section():
    # 1️⃣ Students + one semester each
    students = generate_indian_students(5)
    for stu in students:
        try:
            sid = database.create_student(**stu)
            database.add_semester(
                student_id=sid,
                semester_no=1,
                academic_year=f"{stu['admission_year']}-{stu['admission_year']+1}",
                sgpa=round(random.uniform(6.0, 10.0), 2),
                cgpa=round(random.uniform(6.0, 10.0), 2),
                status="Completed",
                remarks="Initial semester",
            )
        except Exception as e:
            print(f"[seed] Student insert error {stu['roll_no']}: {e}")

    # 2️⃣ Subjects – 5 generic Indian‑style subjects
    example_subjects = [
        ("IN101", "Data Structures", "Theory", 4, 100.0),
        ("IN102", "Thermodynamics Lab", "Lab", 2, 50.0),
        ("IN201", "Database Systems", "Theory", 4, 100.0),
        ("IN202", "Operating Systems Lab", "Lab", 2, 50.0),
        ("IN301", "Machine Learning", "Theory", 4, 100.0),
    ]
    insert_sub_sql = (
        "INSERT IGNORE INTO subjects(subject_code, subject_name, subject_type, credits, default_max_marks) "
        "VALUES(?, ?, ?, ?, ?)"
    )
    with database.get_db() as conn:
        for sub in example_subjects:
            conn.execute(insert_sub_sql, sub)

    # 3️⃣ Activities – 5 entries
    example_activities = [
        ("Coding Competition", "Co-curricular"),
        ("Cultural Fest", "Extra-curricular"),
        ("Hackathon", "Co-curricular"),
        ("Sports Meet", "Extra-curricular"),
        ("Technical Seminar", "Co-curricular"),
    ]
    insert_act_sql = "INSERT IGNORE INTO activities(name, activity_type) VALUES(?, ?)"
    with database.get_db() as conn:
        for act in example_activities:
            conn.execute(insert_act_sql, act)

    # 4️⃣ Activity Categories – 5 entries
    example_cats = [
        ("Innovation", "Co-curricular"),
        ("Volunteer Work", "Extra-curricular"),
        ("Research", "Co-curricular"),
        ("Artistic Performance", "Extra-curricular"),
        ("Leadership", "Co-curricular"),
    ]
    insert_cat_sql = (
        "INSERT IGNORE INTO activity_categories(name, activity_type) VALUES(?, ?)"
    )
    with database.get_db() as conn:
        for cat in example_cats:
            conn.execute(insert_cat_sql, cat)

def main():
    print("[seed] Truncating all tables...")
    database.truncate_all_tables()
    print("[seed] Seeding 5 Indian datasets per section...")
    seed_five_per_section()
    print("[seed] Triggering Google Sheets sync...")
    trigger_auto_sync()
    print("[seed] Done.")

if __name__ == "__main__":
    main()
