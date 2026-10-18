# StudentTrack DBMS Mini-Project

A runnable student academic progression and portfolio management web app built with **Python Flask + SQLite**, with a Google Sheets one-way sync option.

## Included features
- Student directory with search by name or roll number; create and delete records.
- Normalized relational schema: students, semesters, subjects, marks, activity types, activities, seminars, gap years and sync log.
- Primary keys, foreign keys, `ON DELETE CASCADE`, unique constraints, and `CHECK` constraints for percentages, SGPA/CGPA, marks and valid categories.
- Semester SGPA/CGPA progression chart and explicit gap-year indicators.
- Separate Internal/External seminar values and Co-curricular/Extra-curricular activity filters/categories.
- Theory and Lab subject catalogue with per-semester marks.
- CSV export and optional live DB-to-Google-Sheets sync.
- Sample record so the app is not empty on first launch. **Replace or delete sample data before your demonstration.**

## Run on Windows
1. Install Python 3.10+ from https://www.python.org/downloads/ and enable **Add Python to PATH**.
2. Extract this ZIP to a normal folder.
3. Double-click `run_windows.bat`. First run installs dependencies and starts the app.
4. Open http://127.0.0.1:5000 in Chrome/Edge.
5. Stop the server with `Ctrl+C` in the terminal.

Manual alternative:
```bash
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Google Sheets one-way sync (DB → Sheet)
The sync button is included, but Google requires your own account authorization. It cannot sync to your account until configured.

1. Open Google Cloud Console: https://console.cloud.google.com/
2. Create/select a project and enable **Google Sheets API** and **Google Drive API**.
3. Create a service account and download its JSON key. Save it in this project folder as `service_account.json` (keep it private; never commit/share it).
4. Create a Google spreadsheet and share it with the service account email shown in the JSON file as **Editor**.
5. Copy the spreadsheet ID from its URL (`/spreadsheets/d/SPREADSHEET_ID/edit`).
6. Set the environment variable in the same terminal before starting the app:
   ```bat
   set GOOGLE_SHEET_ID=your_spreadsheet_id_here
   python app.py
   ```
7. Click **Sync Google Sheets**. It creates/updates the `Progression` tab and replaces its contents with the current database snapshot. This is one-way sync, not two-way sync.

For convenient repeat use, set `GOOGLE_SHEET_ID` in Windows Environment Variables or add a local launch script. Do not put private credentials in a public repository.

### Important synchronization note
The app provides a **manual-triggered database-to-sheet sync**. It is not a continuously running background listener. For a strict automatic sync after every database mutation, add a queue/worker or call `push_to_google_sheets()` after each successful write. For a one-day project demonstration, click the sync button after changes and show the updated sheet. Do not claim two-way sync.

## Database / constraints
- `students`: unique roll number and email; percentages are 0–100; status is restricted to four allowed values.
- `semesters`: student FK cascades on deletion; semester number 1–12; one row per student/semester; SGPA and CGPA 0–10.
- `subjects`: unique subject code; type must be Theory or Lab.
- `marks`: semester and subject FKs cascade; marks must be nonnegative and not exceed maximum marks; one mark row per subject per semester.
- `activity_types`: category is unique and restricted to Co-curricular / Extra-curricular.
- `activities`: student FK cascades; activity type FK enforced.
- `seminars`: student FK cascades; organizer type restricted to Internal / External.
- `gap_years`: student FK cascades; end year cannot precede start year.
- `sync_log`: records sync result/time/message.
- Invalid values and duplicate unique values are rejected by the database and surfaced as flash messages in the GUI.

## Useful demo sequence
1. Add a student with roll number, name, department and marks percentages.
2. Open the student; add semester 1 and 2 with SGPA/CGPA.
3. Add a Theory subject and a Lab subject, then enter their marks for an existing semester.
4. Add an Internal seminar and an External seminar; add one activity in each category.
5. Add a gap year, then show the marker and the progression chart.
6. Click Export CSV. Configure Sheets and click Sync to demonstrate the sheet update.
7. During viva, explain the schema and why subject/category strings are separated into their own tables.

## Report outline
Use `REPORT.md` for the concise user and technical report. The SQLite file `student_progression.db` is created automatically on first run. To reset the demo database, stop the app and delete that file; it will be recreated with sample data on next start.
