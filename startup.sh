#!/usr/bin/env bash
# Initialize SQLite DB (if not present) and start Gunicorn
python -c "import database; database.init_db(seed=False)"
exec gunicorn app:app
