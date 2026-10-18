"""
==============================================================================
Student Academic Progression and Portfolio Management System
Google Sheets Synchronization Module (sheets_sync.py)
==============================================================================
Provides robust, safe, one-way database-to-spreadsheet synchronization.
- Reads configuration from environment variables or .env / config
- Gracefully handles missing service_account.json, missing sheet IDs,
  network timeouts, and API authentication errors
- Ensures database writes are NEVER blocked by Google Sheets downtime
- Logs every sync attempt (SUCCESS / FAILED) to the sync_log database table
"""

import os
import json
from datetime import datetime
import database

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CRED_FILE = os.path.join(BASE_DIR, "service_account.json")


def get_sync_configuration():
    """
    Returns current configuration status for Google Sheets.
    Does NOT reveal private keys or sensitive contents.
    Supports either Service Account or Apps Script Webhook.
    """
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
    appscript_url = os.environ.get("GOOGLE_APPS_SCRIPT_URL", "").strip()
    cred_path = os.environ.get("GOOGLE_CREDENTIALS_FILE", DEFAULT_CRED_FILE).strip()
    cred_exists = os.path.exists(cred_path)

    service_account_email = None
    if cred_exists:
        try:
            with open(cred_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                service_account_email = data.get("client_email")
        except Exception:
            service_account_email = "(Invalid JSON format)"

    is_configured = bool(appscript_url or (sheet_id and cred_exists and service_account_email and "@" in service_account_email))

    return {
        "sheet_id": sheet_id,
        "appscript_url": appscript_url,
        "cred_path": cred_path,
        "cred_exists": cred_exists,
        "service_account_email": service_account_email,
        "is_configured": is_configured,
        "mode": "Google Apps Script Webhook" if appscript_url else "Service Account"
    }


def perform_sync(sync_type="Manual"):
    """
    Synchronizes current student academic progression and profile records
    from SQLite into the Google Sheets worksheet named 'Progression'.

    Returns:
        tuple: (success: bool, message: str, records_synced: int)
    """
    config = get_sync_configuration()

    # 1. Check if Apps Script Webhook mode is enabled
    if config["appscript_url"]:
        try:
            import urllib.request
            tables_data = database.get_all_normalized_tables_data()
            payload = {
                "action": "sync_all_tables",
                "tables": tables_data
            }
            
            data_bytes = json.dumps(payload, default=str).encode("utf-8")
            req = urllib.request.Request(
                config["appscript_url"],
                data=data_bytes,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                resp_text = resp.read().decode("utf-8", errors="ignore")
                
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            total_records = sum(len(v) for v in tables_data.values())
            success_msg = f"Synchronized {total_records} records across 8 normalized tabs into Google Sheets at {now_str}."
            database.log_sync("SUCCESS", total_records, success_msg, sync_type)
            return True, success_msg, total_records
        except Exception as e:
            err_msg = f"Apps Script multi-tab sync error: {e}"
            database.log_sync("FAILED", 0, err_msg, sync_type)
            return False, err_msg, 0

    # 2. Check if libraries are importable (Service Account mode)
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as e:
        err_msg = (
            f"Google Sheets integration libraries missing ({e}). "
            "Please install dependencies with: pip install gspread google-auth"
        )
        database.log_sync("FAILED", 0, err_msg, sync_type)
        return False, err_msg, 0

    # 2. Check credentials file existence
    if not config["cred_exists"]:
        err_msg = (
            f"Google Cloud service account key not found at '{config['cred_path']}'. "
            "Please follow the Google Sheets Setup Guide in the documentation to place "
            "your service_account.json in the project directory."
        )
        database.log_sync("FAILED", 0, err_msg, sync_type)
        return False, err_msg, 0

    # 3. Check Google Sheet ID
    if not config["sheet_id"]:
        err_msg = (
            "GOOGLE_SHEET_ID environment variable is not configured. "
            "Please specify your target Google Spreadsheet ID in your environment or .env file."
        )
        database.log_sync("FAILED", 0, err_msg, sync_type)
        return False, err_msg, 0

    # 4. Attempt authentication & synchronization
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.readonly",
        ]
        creds = Credentials.from_service_account_file(config["cred_path"], scopes=scopes)
        client = gspread.authorize(creds)

        # Open spreadsheet
        spreadsheet = client.open_by_key(config["sheet_id"])

        # Fetch joined progression records from 3NF SQLite database
        rows = database.get_progression_export_data()

        # Prepare 2D matrix for worksheet
        headers = [
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
            "Last Synced At",
        ]

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data_matrix = [headers]

        for r in rows:
            data_matrix.append([
                r["roll_no"] or "",
                r["full_name"] or "",
                r["email"] or "",
                r["phone"] or "",
                r["department"] or "",
                r["admission_year"] or "",
                r["secondary_percent"] if r["secondary_percent"] is not None else "",
                r["higher_secondary_percent"] if r["higher_secondary_percent"] is not None else "",
                r["current_status"] or "",
                f"Semester {r['semester_no']}" if r["semester_no"] is not None else "No Semesters Yet",
                r["academic_year"] or "",
                r["sgpa"] if r["sgpa"] is not None else "",
                r["cgpa"] if r["cgpa"] is not None else "",
                r["semester_status"] or "",
                r["remarks"] or "",
                r["gap_years_summary"] or "None (Continuous Progression)",
                now_str,
            ])

        # Find or create 'Progression' worksheet
        existing_sheets = [ws.title for ws in spreadsheet.worksheets()]
        if "Progression" in existing_sheets:
            worksheet = spreadsheet.worksheet("Progression")
            worksheet.clear()
        else:
            worksheet = spreadsheet.add_worksheet(
                title="Progression",
                rows=max(100, len(data_matrix) + 20),
                cols=len(headers) + 2,
            )

        # Update cells in Google Sheet
        worksheet.update(data_matrix, "A1")

        # Try to format the header row with nice styling
        try:
            worksheet.format("A1:Q1", {
                "backgroundColor": {"red": 0.1, "green": 0.21, "blue": 0.36},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}},
                "horizontalAlignment": "CENTER",
            })
        except Exception:
            pass  # Formatting is optional visual polish

        record_count = len(rows)
        success_msg = (
            f"Successfully synchronized {record_count} student progression records to "
            f"Google Sheets tab 'Progression' at {now_str}."
        )
        database.log_sync("SUCCESS", record_count, success_msg, sync_type)
        return True, success_msg, record_count

    except Exception as e:
        err_str = str(e)
        if "API has not been used in project" in err_str:
            friendly_err = (
                "Google Sheets API or Google Drive API has not been enabled in your Google Cloud Console. "
                "Please enable both APIs in your project."
            )
        elif "SpreadsheetNotFound" in err_str or "404" in err_str:
            friendly_err = (
                f"Google Spreadsheet with ID '{config['sheet_id']}' was not found. "
                "Please verify your spreadsheet ID and ensure you shared the sheet with your "
                f"service account email ({config['service_account_email']}) as 'Editor'."
            )
        elif "Permission denied" in err_str or "403" in err_str:
            friendly_err = (
                f"Access denied to spreadsheet. Please open Google Sheets, click Share, "
                f"and add the service account email '{config['service_account_email']}' with 'Editor' permissions."
            )
        else:
            friendly_err = f"Google Sheets API synchronization error: {err_str}"

        database.log_sync("FAILED", 0, friendly_err, sync_type)
        return False, friendly_err, 0
