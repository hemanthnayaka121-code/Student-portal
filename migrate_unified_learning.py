"""
Safe Additive Database Migration for Unified Learning, OAuth Accounts, and Certificate Synchronization.
Preserves all existing placement data and creates a backup prior to execution.
"""

import os
import shutil
import sqlite3
import datetime
from app import app, db
from models import (
    Student, Course, WorkshopEvent, StudentAchievement,
    ExternalProviderAccount, CertificateSyncLog, StudentPreference
)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'placement.db')
BACKUP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'placement_backup_pre_unified.db')

def migrate():
    print(f"=== Starting Unified Learning Database Migration ===")
    
    # 1. Database Backup
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, BACKUP_PATH)
        print(f"[OK] Database backed up safely to: {BACKUP_PATH}")
    else:
        print("[WARN] No database file found at instance/placement.db; creating new database.")

    with app.app_context():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 2. Add columns to courses if missing
        cursor.execute("PRAGMA table_info(courses)")
        course_cols = [c[1] for c in cursor.fetchall()]
        if 'description' not in course_cols:
            cursor.execute("ALTER TABLE courses ADD COLUMN description TEXT")
            print("[OK] Added column 'description' to 'courses'")

        # 3. Add columns to student_achievements if missing
        cursor.execute("PRAGMA table_info(student_achievements)")
        ach_cols = [c[1] for c in cursor.fetchall()]
        if 'achievement_type' not in ach_cols:
            cursor.execute("ALTER TABLE student_achievements ADD COLUMN achievement_type VARCHAR(50) DEFAULT 'COURSE'")
            print("[OK] Added column 'achievement_type' to 'student_achievements'")
        if 'verification_method' not in ach_cols:
            cursor.execute("ALTER TABLE student_achievements ADD COLUMN verification_method VARCHAR(50) DEFAULT 'MANUAL_SUBMISSION'")
            print("[OK] Added column 'verification_method' to 'student_achievements'")
        if 'external_certificate_id' not in ach_cols:
            cursor.execute("ALTER TABLE student_achievements ADD COLUMN external_certificate_id VARCHAR(100)")
            print("[OK] Added column 'external_certificate_id' to 'student_achievements'")
        if 'description' not in ach_cols:
            cursor.execute("ALTER TABLE student_achievements ADD COLUMN description TEXT")
            print("[OK] Added column 'description' to 'student_achievements'")

        conn.commit()
        conn.close()

        # 4. Create newly declared tables (external_provider_accounts, certificate_sync_logs)
        db.create_all()
        print("[OK] All SQLAlchemy tables verified and created")

        # 5. Seed descriptions for existing courses if blank
        sample_descriptions = {
            "PY-CORE-101": "Master Python programming fundamentals, data structures, and object-oriented concepts with hands-on practice from Michigan faculty.",
            "DSA-ALGO-201": "Comprehensive exploration of algorithms, graph theory, sorting, recursion, and dynamic programming benchmarked for technical placement interviews.",
            "ML-STAND-301": "Foundational machine learning concepts, supervised regression, classification, neural networks, and model evaluation created by Andrew Ng.",
            "JAVA-OOP-102": "Core Java language syntax, inheritance, polymorphism, interfaces, and memory management for enterprise software engineering roles.",
            "WEB-REACT-202": "Modern frontend development using React components, hooks, state management, and responsive CSS for full-stack engineering interviews.",
            "CLOUD-GCP-101": "Cloud infrastructure fundamentals, compute engine, container orchestration, IAM, and networking essentials on Google Cloud.",
            "CYBER-ETH-101": "Network reconnaissance, vulnerabilities, defensive controls, and ethical hacking protocols for security analyst positions."
        }
        for cid, desc in sample_descriptions.items():
            course = Course.query.filter_by(course_id=cid).first()
            if course and not course.description:
                course.description = desc
        
        # 6. Seed Hackathons & Competitions into workshop_events
        hackathon_samples = [
            {
                "title": "Smart India Hackathon (SIH) — College Preliminary",
                "organizer": "Ministry of Education & MIT Mysore Innovation Cell",
                "domain": "Hackathon",
                "target_branches": "ALL",
                "event_type": "Hackathon",
                "city": "Mysuru",
                "venue_mode": "Hybrid",
                "venue_details": "MIT Mysore Auditorium & GitHub Submissions",
                "event_date": datetime.datetime(2026, 4, 10, 9, 0),
                "registration_deadline": datetime.datetime(2026, 4, 2, 23, 59),
                "is_free": True,
                "registration_fee": "Free of Cost",
                "certificate_available": True,
                "certificate_conditions": "Verified Participation Certificate & National Shortlist Eligibility",
                "official_registration_url": "https://www.sih.gov.in/",
                "is_verified": True
            },
            {
                "title": "VTU Inter-Collegiate Coding Contest & Hackathon",
                "organizer": "Visvesvaraya Technological University (VTU Belagavi)",
                "domain": "DSA",
                "target_branches": "IS,CS,EC",
                "event_type": "Competition",
                "city": "Belagavi",
                "venue_mode": "Online",
                "venue_details": "HackerRank Proctored Platform",
                "event_date": datetime.datetime(2026, 4, 18, 14, 0),
                "registration_deadline": datetime.datetime(2026, 4, 12, 18, 0),
                "is_free": True,
                "registration_fee": "Free of Cost",
                "certificate_available": True,
                "certificate_conditions": "Rank Certificate & Verifiable Credential for Top 10%",
                "official_registration_url": "https://vtu.ac.in/en/coding-contest-2026",
                "is_verified": True
            },
            {
                "title": "Karnataka Student Innovation & Startup Challenge",
                "organizer": "Karnataka Innovation and Technology Society (KITS)",
                "domain": "Full Stack",
                "target_branches": "ALL",
                "event_type": "Competition",
                "city": "Bengaluru",
                "venue_mode": "In-Person",
                "venue_details": "Bengaluru Tech Summit Campus, Palace Grounds",
                "event_date": datetime.datetime(2026, 5, 2, 10, 0),
                "registration_deadline": datetime.datetime(2026, 4, 20, 23, 59),
                "is_free": True,
                "registration_fee": "Free of Cost",
                "certificate_available": True,
                "certificate_conditions": "State Government Verified Certificate & Prototype Grant",
                "official_registration_url": "https://innovate.karnataka.gov.in/challenge-2026",
                "is_verified": True
            }
        ]

        for h in hackathon_samples:
            existing = WorkshopEvent.query.filter_by(title=h["title"]).first()
            if not existing:
                ev = WorkshopEvent(**h)
                db.session.add(ev)
                print(f"[OK] Seeded event/competition: {h['title']}")

        # 7. Seed verified sample achievements for demo student Alice Sharma
        alice_usn = "4MH24IS001"
        alice = Student.query.filter_by(usn=alice_usn).first()
        if alice:
            # Seed ExternalProviderAccount for Coursera
            ext_acc = ExternalProviderAccount.query.filter_by(student_usn=alice_usn, provider_name='Coursera').first()
            if not ext_acc:
                ext_acc = ExternalProviderAccount(
                    student_usn=alice_usn,
                    provider_name='Coursera',
                    external_account_id='coursera_learner_4mh24is001',
                    external_email=alice.email,
                    connection_status='CONNECTED',
                    last_synced_at=datetime.datetime.utcnow() - datetime.timedelta(hours=2)
                )
                db.session.add(ext_acc)
                print(f"[OK] Linked demo ExternalProviderAccount for {alice_usn}")

            # Ensure student preference reflects connection
            if not alice.preference:
                pref = StudentPreference(
                    student_usn=alice_usn,
                    coursera_email=alice.email,
                    coursera_connected=True,
                    coursera_connected_at=datetime.datetime.utcnow()
                )
                db.session.add(pref)
            else:
                alice.preference.coursera_connected = True
                alice.preference.coursera_email = alice.email

            # Seed a verified Hackathon achievement
            sih_ach = StudentAchievement.query.filter_by(student_usn=alice_usn, title="Smart India Hackathon 2025 Finalist").first()
            if not sih_ach:
                ach1 = StudentAchievement(
                    student_usn=alice_usn,
                    category='HACKATHON',
                    achievement_type='HACKATHON',
                    title="Smart India Hackathon 2025 Finalist",
                    provider_or_organizer="AICTE & Ministry of Education",
                    domain="Full Stack & AI",
                    completion_date=datetime.datetime(2025, 12, 20),
                    certificate_url="https://sih.gov.in/certificates/verify/SIH2025-MITM-042",
                    skills_acquired="Problem Solving, React, Flask, Teamwork",
                    verification_status="VERIFIED",
                    verification_method="ORGANIZER_VERIFIED",
                    verified_by="SIH Organising Committee",
                    verified_at=datetime.datetime(2025, 12, 22),
                    verification_notes="Official SIH national finalist certificate verified via AICTE portal.",
                    external_certificate_id="SIH2025-MITM-042",
                    description="Represented MIT Mysore in the National Grand Finale solving smart agriculture automation."
                )
                db.session.add(ach1)
                print("[OK] Seeded verified Hackathon achievement")

            # Seed a verified Coursera certificate
            py_ach = StudentAchievement.query.filter_by(student_usn=alice_usn, title="Programming for Everybody (Getting Started with Python)").first()
            if not py_ach:
                ach2 = StudentAchievement(
                    student_usn=alice_usn,
                    category='COURSE',
                    achievement_type='COURSE',
                    title="Programming for Everybody (Getting Started with Python)",
                    provider_or_organizer="Coursera / University of Michigan",
                    domain="Python",
                    completion_date=datetime.datetime(2026, 1, 15),
                    certificate_url="https://www.coursera.org/verify/9WXYZ789SAMPLE",
                    skills_acquired="Python Syntax, Data Structures, Algorithmic Thinking",
                    verification_status="VERIFIED",
                    verification_method="OAUTH_SYNC",
                    verified_by="Coursera Automated Verification",
                    verified_at=datetime.datetime(2026, 1, 15),
                    verification_notes="Verified directly through Coursera Provider OAuth Integration.",
                    external_certificate_id="COURSERA_9WXYZ789SAMPLE",
                    is_coursera_sync=True,
                    description="Official University of Michigan certification with verified credential code."
                )
                db.session.add(ach2)
                print("[OK] Seeded verified Coursera achievement")

        db.session.commit()
        print("\n=== Unified Learning Migration Completed Successfully! ===")

if __name__ == '__main__':
    migrate()
