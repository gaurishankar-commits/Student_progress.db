import sqlite3
import pymysql

lite = sqlite3.connect('student_progression.db')
lite.row_factory = sqlite3.Row

my = pymysql.connect(
    host='localhost',
    user='root',
    password='Gauri@2026',
    database='astudent_progress',
    autocommit=True
)

tables = [
    'activity_categories',
    'subjects',
    'students',
    'semesters',
    'semester_subject_marks',
    'seminars',
    'activities',
    'gap_years',
    'sync_log'
]

with my.cursor() as cur:
    cur.execute('SET FOREIGN_KEY_CHECKS = 0;')
    for tbl in tables:
        cur.execute(f'TRUNCATE TABLE `{tbl}`;')
        rows = lite.execute(f'SELECT * FROM {tbl}').fetchall()
        if not rows:
            continue
        cols = list(rows[0].keys())
        col_names = ', '.join([f'`{c}`' for c in cols])
        placeholders = ', '.join(['%s'] * len(cols))
        insert_sql = f'INSERT INTO `{tbl}` ({col_names}) VALUES ({placeholders})'
        data = [[row[c] for c in cols] for row in rows]
        cur.executemany(insert_sql, data)
        print(f'Migrated {len(data)} rows into {tbl}')
    cur.execute('SET FOREIGN_KEY_CHECKS = 1;')

print('DATA_MIGRATION_COMPLETE_SUCCESS')
