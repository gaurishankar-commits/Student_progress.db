import sys
import os

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Initialize database if needed
import database
try:
    database.init_db(seed=True)
except Exception as e:
    print(f"[Vercel Init] {e}")

from app import app

# Vercel entrypoint
app.debug = False
