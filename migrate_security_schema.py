"""
Database Migration Script: Security & Credentials Schema
Applies new security columns to `admins` and `students`,
and creates tables `student_otp_verifications`, `password_reset_tokens`, and `security_audit_logs`.
"""

import sqlite3
import os

def migrate_database(db_path):
    print(f"\n[Migration] Applying security schema to: {db_path}")
    if not os.path.exists(db_path):
        print(f"File {db_path} does not exist. Skipping.")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 1. Add new columns to `admins` table if not already present
    c.execute("PRAGMA table_info(admins)")
    admin_cols = [r[1] for r in c.fetchall()]

    new_admin_columns = [
        ("recovery_email", "VARCHAR(100)"),
        ("recovery_mobile", "VARCHAR(30)"),
        ("is_recovery_email_verified", "BOOLEAN DEFAULT 0"),
        ("is_recovery_mobile_verified", "BOOLEAN DEFAULT 0"),
        ("password_changed_at", "DATETIME"),
        ("last_login_at", "DATETIME"),
        ("failed_login_count", "INTEGER DEFAULT 0"),
        ("locked_until", "DATETIME"),
        ("session_version", "INTEGER DEFAULT 1")
    ]

    for col_name, col_type in new_admin_columns:
        if col_name not in admin_cols:
            print(f"  Adding column admins.{col_name} ({col_type})")
            c.execute(f"ALTER TABLE admins ADD COLUMN {col_name} {col_type}")

    # 2. Add new columns to `students` table if not already present
    c.execute("PRAGMA table_info(students)")
    student_cols = [r[1] for r in c.fetchall()]

    if "session_version" not in student_cols:
        print("  Adding column students.session_version (INTEGER DEFAULT 1)")
        c.execute("ALTER TABLE students ADD COLUMN session_version INTEGER DEFAULT 1")

    # 3. Create table `student_otp_verifications`
    c.execute("""
    CREATE TABLE IF NOT EXISTS student_otp_verifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        identifier VARCHAR(100) NOT NULL,
        student_usn VARCHAR(20),
        otp_hash VARCHAR(255) NOT NULL,
        purpose VARCHAR(50) DEFAULT 'STUDENT_LOGIN',
        attempts INTEGER DEFAULT 0,
        max_attempts INTEGER DEFAULT 3,
        expires_at DATETIME NOT NULL,
        is_used BOOLEAN DEFAULT 0,
        used_at DATETIME,
        ip_address VARCHAR(50),
        created_at DATETIME,
        FOREIGN KEY (student_usn) REFERENCES students(usn)
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_otp_identifier ON student_otp_verifications(identifier)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_otp_usn ON student_otp_verifications(student_usn)")

    # 4. Create table `password_reset_tokens`
    c.execute("""
    CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER NOT NULL,
        token_hash VARCHAR(255) NOT NULL,
        method VARCHAR(30) DEFAULT 'EMAIL',
        expires_at DATETIME NOT NULL,
        is_used BOOLEAN DEFAULT 0,
        used_at DATETIME,
        created_at DATETIME,
        FOREIGN KEY (admin_id) REFERENCES admins(id)
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_reset_admin_id ON password_reset_tokens(admin_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_reset_token_hash ON password_reset_tokens(token_hash)")

    # 5. Create table `security_audit_logs`
    c.execute("""
    CREATE TABLE IF NOT EXISTS security_audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_type VARCHAR(30) NOT NULL,
        user_identifier VARCHAR(100) NOT NULL,
        event_type VARCHAR(100) NOT NULL,
        status VARCHAR(30) DEFAULT 'SUCCESS',
        ip_address VARCHAR(50),
        details VARCHAR(255),
        timestamp DATETIME,
        FOREIGN KEY (user_identifier) REFERENCES admins(username)
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_sec_audit_timestamp ON security_audit_logs(timestamp)")

    conn.commit()
    conn.close()
    print(f"[Migration] Completed successfully for {db_path}!")

if __name__ == '__main__':
    for db_f in ['placement.db', 'instance/placement.db']:
        migrate_database(db_f)
