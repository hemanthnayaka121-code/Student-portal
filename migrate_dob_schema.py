"""
Database Migration Script: Student Date of Birth & Credentials Schema
Applies new security and date_of_birth columns to `students` table,
and safely populates initial dates of birth for existing student records.
Preserves all existing placement data across both placement.db and instance/placement.db.
"""

import sqlite3
import os
import shutil
from datetime import datetime

DEFAULT_STUDENT_DOBS = {
    "4MH24IS001": "2003-05-14",  # Alice Sharma
    "4MH24IS002": "2003-08-22",  # Bob Verma
    "4MH24IS003": "2003-11-10",  # Charlie Patel
    "4MH24IS004": "2004-01-18",  # Divya Reddy
    "4MH24IS005": "2004-03-25",  # Eshan Nair
    "4MH24CS001": "2003-02-15",  # Rahul Dravid
    "4MH24CS002": "2003-07-19",  # Sneha Kulkarni
    "4MH24CS003": "2003-10-04",  # Tarun Mehta
    "4MH24CS004": "2004-04-12",  # Ananya Hegde
    "4MH24CS005": "2003-12-30",  # Deepak Gowda
    "4MH24AI001": "2003-09-17",  # Kiran Kumar
    "4MH24AI002": "2004-02-28",  # Meera Joshi
    "4MH24AI003": "2003-06-05",  # Naveen Rao
    "4MH24EC001": "2003-03-11",  # Prasad Shenoy
    "4MH24EC002": "2003-11-23",  # Pooja Joshi
    "4MH24IT001": "2003-08-14",  # Rakesh Bhat
    "4MH24CV001": "2003-04-20",  # Vinay Kumar
    "4MH24ME001": "2003-01-15",  # Vikram Rathore
    "4MH24ME002": "2003-10-29",  # Suresh Gowda
    "4MH24IS033": "2003-06-12",  # Kavya Murthy (PENDING HOD APPROVAL)
    "4MH24CS033": "2003-07-25",  # Vikram Sen (PENDING HOD APPROVAL)
    "4MH24IS099": "2003-09-08",  # Sumanth Rao (REJECTED)
}

def migrate_database(db_path):
    print(f"\n[Migration] Checking and applying DOB schema to: {db_path}")
    if not os.path.exists(db_path):
        print(f"File {db_path} does not exist. Skipping.")
        return

    # Create backup before schema change
    backup_path = f"{db_path}.backup_dob_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"  Safely created backup at: {backup_path}")

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("PRAGMA table_info(students)")
    existing_cols = [r[1] for r in c.fetchall()]

    new_columns = [
        ("date_of_birth", "DATE"),
        ("password_hash", "VARCHAR(255)"),
        ("first_login_at", "DATETIME"),
        ("dob_login_count", "INTEGER DEFAULT 0"),
        ("failed_login_count", "INTEGER DEFAULT 0"),
        ("locked_until", "DATETIME"),
    ]

    for col_name, col_type in new_columns:
        if col_name not in existing_cols:
            print(f"  Adding column students.{col_name} ({col_type})")
            c.execute(f"ALTER TABLE students ADD COLUMN {col_name} {col_type}")

    # Seed DOBs for existing students
    c.execute("SELECT usn, date_of_birth FROM students")
    students = c.fetchall()
    updated_count = 0
    for usn, cur_dob in students:
        if not cur_dob:
            assigned_dob = DEFAULT_STUDENT_DOBS.get(usn, "2003-01-01")
            c.execute("UPDATE students SET date_of_birth = ? WHERE usn = ?", (assigned_dob, usn))
            updated_count += 1

    conn.commit()
    conn.close()
    print(f"  Updated {updated_count} students with initial DOB records.")
    print(f"[Migration] Successfully completed for: {db_path}")

if __name__ == '__main__':
    targets = ['placement.db', os.path.join('instance', 'placement.db')]
    for db_target in targets:
        migrate_database(db_target)
