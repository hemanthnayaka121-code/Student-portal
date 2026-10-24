"""
Database Audit & Safe Cleanup Script for MIT Placement Portal
1. Backs up database
2. Identifies genuine vs test records
3. Safely removes confirmed dummy records and dependent rows
4. Deduplicates achievement records
5. Preserves all genuine students, placement history, and certificates
6. Reports records removed and retained
"""

import sqlite3
import shutil
import os
from datetime import datetime

def run_cleanup(db_path):
    print(f"\n==================================================")
    print(f"Starting Safe Database Cleanup on: {db_path}")
    print(f"==================================================")
    
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist. Skipping.")
        return

    # 1. Create timestamped backup
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.cleanup_backup_{timestamp}"
    shutil.copy2(db_path, backup_path)
    print(f"[Backup] Successfully created backup at: {backup_path}")

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    try:
        conn.execute("BEGIN TRANSACTION")

        # --- A. AUDIT STUDENTS ---
        c.execute("SELECT usn, name, email, mobile_number, department_id, placement_approval_status FROM students")
        all_students = c.fetchall()
        print(f"\n[Audit] Total students before cleanup: {len(all_students)}")

        # Confirmed dummy test students created by previous auto-provisioning or test runs
        dummy_usns = ['TEST_PENDING_01', '4MH24CSE402', '4MH24ISE385']
        
        # Check presence of dummy students
        c.execute(f"SELECT usn, name, email FROM students WHERE usn IN ({','.join(['?']*len(dummy_usns))})", dummy_usns)
        found_dummies = c.fetchall()
        print(f"[Audit] Identified {len(found_dummies)} confirmed dummy/test students to remove:")
        for d in found_dummies:
            print(f"   - {d[0]}: {d[1]} ({d[2]})")

        # Delete dependent records for dummy students
        removed_deps = 0
        for dummy_usn in dummy_usns:
            for table in [
                'performance_records', 'student_account_links', 'student_achievements',
                'quiz_attempts', 'mock_interview_sessions', 'student_notifications',
                'student_course_progress', 'student_event_actions', 'learning_recommendations',
                'youtube_lessons', 'student_preferences', 'external_provider_accounts',
                'certificate_sync_logs', 'audit_logs'
            ]:
                try:
                    c.execute(f"DELETE FROM {table} WHERE student_usn = ?", (dummy_usn,))
                    removed_deps += c.rowcount
                except sqlite3.OperationalError:
                    pass

        # Remove dummy students
        c.execute(f"DELETE FROM students WHERE usn IN ({','.join(['?']*len(dummy_usns))})", dummy_usns)
        students_deleted = c.rowcount
        print(f"[Cleanup] Removed {students_deleted} dummy students and {removed_deps} dependent test records.")

        # --- B. DEDUPLICATE FAKE/REPEATED ACHIEVEMENTS ---
        c.execute("SELECT id, title, provider_or_organizer, student_usn, verification_status, created_at FROM student_achievements ORDER BY id ASC")
        all_achievements = c.fetchall()
        print(f"\n[Audit] Total achievements before cleanup: {len(all_achievements)}")

        seen_achievements = set()
        achievements_to_delete = []
        achievements_to_keep = []

        # We keep the verified or earliest record of each unique (student_usn, title, provider)
        # For duplicates of "Kubernetes for Developers Test Submission" and "Applied Machine Learning in Python"
        for ach in all_achievements:
            ach_id, title, provider, student_usn, status, created_at = ach
            key = (student_usn, title.strip().lower(), provider.strip().lower())
            
            # If we haven't seen this achievement for this student, keep it
            if key not in seen_achievements:
                seen_achievements.add(key)
                achievements_to_keep.append(ach)
            else:
                # If current kept one is PENDING but this one is VERIFIED, swap to keep the verified one
                existing_kept = [k for k in achievements_to_keep if (k[3], k[1].strip().lower(), k[2].strip().lower()) == key]
                if existing_kept and existing_kept[0][4] != 'VERIFIED' and status == 'VERIFIED':
                    achievements_to_delete.append(existing_kept[0][0])
                    achievements_to_keep.remove(existing_kept[0])
                    achievements_to_keep.append(ach)
                else:
                    achievements_to_delete.append(ach_id)

        print(f"[Audit] Identified {len(achievements_to_delete)} duplicate/fake achievement submissions to remove.")
        if achievements_to_delete:
            c.execute(f"DELETE FROM student_achievements WHERE id IN ({','.join(['?']*len(achievements_to_delete))})", achievements_to_delete)
            print(f"[Cleanup] Deleted {c.rowcount} duplicate achievement entries.")

        # --- C. AUDIT & CLEANUP TEST ACCOUNT LINKS ---
        # Remove developer test links like 'direct_alice_is_mitm_ac_in' or orphaned links
        c.execute("SELECT id, student_usn, firebase_uid, email FROM student_account_links")
        all_links = c.fetchall()
        links_deleted = 0
        for link in all_links:
            lid, usn, f_uid, email = link
            # Check if student still exists
            c.execute("SELECT usn FROM students WHERE usn = ?", (usn,))
            if not c.fetchone():
                c.execute("DELETE FROM student_account_links WHERE id = ?", (lid,))
                links_deleted += 1
            elif f_uid.startswith('direct_') or f_uid.startswith('google_test_'):
                c.execute("DELETE FROM student_account_links WHERE id = ?", (lid,))
                links_deleted += 1
                print(f"[Cleanup] Removed test account link: {f_uid} for USN {usn}")

        conn.commit()
        print(f"[Success] Transaction committed successfully for {db_path}!")

        # --- D. VERIFICATION REPORT ---
        c.execute("SELECT COUNT(*) FROM students")
        retained_students = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM student_achievements")
        retained_achievements = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM student_account_links")
        retained_links = c.fetchone()[0]

        print(f"\n[Verification Report for {db_path}]")
        print(f"  Students retained: {retained_students} (removed {students_deleted})")
        print(f"  Achievements retained: {retained_achievements} (removed {len(achievements_to_delete)})")
        print(f"  Account links retained: {retained_links} (removed {links_deleted})")

        c.execute("SELECT usn, name, email, mobile_number FROM students")
        print("\n  Preserved Genuine Students:")
        for s in c.fetchall():
            print(f"    - {s[0]}: {s[1]} | Email: {s[2]} | Mobile: {s[3]}")

        c.execute("SELECT id, title, provider_or_organizer, student_usn, verification_status FROM student_achievements")
        print("\n  Preserved Genuine Achievements:")
        for a in c.fetchall():
            print(f"    - [{a[0]}] {a[1]} ({a[2]}) - {a[3]} [{a[4]}]")

    except Exception as e:
        conn.rollback()
        print(f"[Error] Transaction failed and rolled back: {e}")
        raise e
    finally:
        conn.close()

if __name__ == '__main__':
    for db_file in ['placement.db', 'instance/placement.db']:
        run_cleanup(db_file)
