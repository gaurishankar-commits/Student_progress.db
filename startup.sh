#!/usr/bin/env bash
# Initialize SQLite DB and start Gunicorn bound to Render's assigned port
python -c "import database; database.init_db(seed=True)"
exec gunicorn -b 0.0.0.0:${PORT:-5000} app:app
