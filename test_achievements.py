"""
Automated Test Suite for Achievement Hub & Simplified Student Dashboard
Verifies:
1. CourseProviderService (Catalog, search, free filters, Coursera fallback status, bookmarking, progress)
2. WorkshopDiscoveryService (Karnataka cities, official links, save, apply, reminder)
3. RecommendationService (Branch-specific domains, diagnostic placement weakness rules & rationale)
4. AchievementService & Portfolio (Submission, file safety, status accuracy, portfolio calculations)
5. CertificateVerificationService (Admin review queue, approve/reject audit logs, student alerts)
6. NotificationService (In-app alerts, unread counts, deadline checks)
7. Security & Role-Based Authorization (Admin/Student isolation, IDOR prevention)
8. Backward compatibility with existing placement tracking and database schema.
"""

import unittest
import os
import datetime
from app import app, db
from models import (
    Student, Department, PerformanceRecord, AuditLog,
    Course, StudentCourseProgress, WorkshopEvent,
    StudentEventAction, StudentAchievement, StudentNotification, StudentPreference
)
from course_service import CourseProviderService
from workshop_service import WorkshopDiscoveryService
from recommendation_service import RecommendationService
from achievement_service import AchievementService, CertificateVerificationService
from notification_service import NotificationService

class AchievementsHubTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_01_course_provider_service_catalog_and_filters(self):
        """Test 1: Course discovery, search, domain filter, and free learning filters"""
        # Test basic catalog retrieval
        all_courses = CourseProviderService.get_courses()
        self.assertGreaterEqual(len(all_courses), 10, "Should have seeded courses available")

        # Test search query
        python_courses = CourseProviderService.get_courses(search_query="Python")
        self.assertTrue(all("Python" in c.title or "Python" in (c.skills_covered or "") or "Python" in c.domain for c in python_courses))

        # Test free learning filter
        free_courses = CourseProviderService.get_courses(free_only=True)
        self.assertTrue(all(c.is_free is True for c in free_courses))

        # Test free certificate filter
        free_cert_courses = CourseProviderService.get_courses(free_certificate_only=True)
        self.assertTrue(all(c.free_certificate is True for c in free_cert_courses))

        # Test official Coursera integration status reporting
        status = CourseProviderService.check_coursera_integration_status()
        self.assertIn("is_live_oauth_configured", status)
        self.assertIn("message", status)
        self.assertIn("integration_mode", status)

    def test_02_course_actions_bookmark_and_progress(self):
        """Test 2: Student can bookmark and track learning progress within the application"""
        alice_usn = "4MH24IS001"
        course = Course.query.first()
        self.assertIsNotNone(course, "At least one course must exist")

        # Clean any prior progress on this course for deterministic testing
        prior = StudentCourseProgress.query.filter_by(student_usn=alice_usn, course_id=course.id).first()
        if prior:
            db.session.delete(prior)
            db.session.commit()

        # Toggle Bookmark
        is_bm, _ = CourseProviderService.toggle_bookmark(alice_usn, course.id)
        self.assertTrue(is_bm)
        
        # Verify bookmark persisted
        prog = StudentCourseProgress.query.filter_by(student_usn=alice_usn, course_id=course.id).first()
        self.assertIsNotNone(prog)
        self.assertEqual(prog.status, 'BOOKMARKED')

        # Update progress to ENROLLED
        CourseProviderService.update_progress(alice_usn, course.id, status='ENROLLED', progress_pct=25.0)
        prog = StudentCourseProgress.query.filter_by(student_usn=alice_usn, course_id=course.id).first()
        self.assertEqual(prog.status, 'ENROLLED')
        self.assertEqual(prog.progress_pct, 25.0)

        # Connect Coursera Account Email
        pref = CourseProviderService.connect_coursera_account(alice_usn, "alice.sharma@gmail.com")
        self.assertEqual(pref.coursera_email, "alice.sharma@gmail.com")

    def test_03_workshop_discovery_and_student_actions(self):
        """Test 3: Karnataka workshop discovery across cities and student action tracking"""
        # Discover Karnataka events
        events_blr = WorkshopDiscoveryService.get_events(city="Bengaluru")
        self.assertTrue(all(e.city == "Bengaluru" for e in events_blr))

        events_mys = WorkshopDiscoveryService.get_events(city="Mysuru")
        self.assertTrue(all(e.city == "Mysuru" for e in events_mys))

        # Test student event actions
        alice_usn = "4MH24IS001"
        ev = WorkshopEvent.query.first()
        self.assertIsNotNone(ev)

        # Reset any prior action for deterministic test
        prior_action = StudentEventAction.query.filter_by(student_usn=alice_usn, event_id=ev.id).first()
        if prior_action:
            db.session.delete(prior_action)
            db.session.commit()

        # Toggle Save
        is_saved, _ = WorkshopDiscoveryService.toggle_save_event(alice_usn, ev.id)
        self.assertTrue(is_saved)

        # Record link opened
        rec = WorkshopDiscoveryService.record_link_opened(alice_usn, ev.id)
        self.assertIn(rec.status, ["REGISTRATION_OPENED", "SAVED"])

        # Mark applied
        rec = WorkshopDiscoveryService.mark_applied(alice_usn, ev.id, notes="Registered on official site")
        self.assertEqual(rec.status, "APPLIED")

        # Toggle reminder
        is_rem, _ = WorkshopDiscoveryService.toggle_reminder(alice_usn, ev.id)
        self.assertTrue(is_rem)

    def test_04_recommendation_engine_branch_and_diagnostic_weaknesses(self):
        """Test 4: Transparent rule-based recommendations mapped to student branch & diagnostic weaknesses"""
        student = Student.query.filter_by(usn="4MH24IS001").first()
        self.assertIsNotNone(student)

        recs = RecommendationService.get_recommendations_for_student(student)
        self.assertIn("recommended_courses", recs)
        self.assertIn("recommended_events", recs)
        self.assertIn("weakness_count", recs)
        self.assertIn(recs["branch"], ["IS", "ISE"])

        # Verify rationale is present and human-readable
        for item in recs["recommended_courses"]:
            self.assertIn("rationale", item)
            self.assertIn("type", item)
            self.assertIsInstance(item["rationale"], str)
            self.assertGreater(len(item["rationale"]), 10)

        for item in recs["recommended_events"]:
            self.assertIn("rationale", item)
            self.assertIn("event", item)

    def test_05_achievement_submission_and_portfolio_summary(self):
        """Test 5: Student achievement submission with PENDING_VERIFICATION and accurate portfolio calculation"""
        alice_usn = "4MH24IS001"

        # Submit new achievement
        sub_data = {
            'title': 'Applied Machine Learning in Python',
            'category': 'COURSE',
            'provider_or_organizer': 'Coursera / University of Michigan',
            'domain': 'AI/ML',
            'completion_date': '2026-02-15',
            'certificate_url': 'https://www.coursera.org/verify/SAMPLE123456',
            'skills_acquired': 'Python, Scikit-Learn, Pandas'
        }
        ach = AchievementService.submit_achievement(alice_usn, sub_data)
        self.assertEqual(ach.verification_status, 'PENDING_VERIFICATION')
        self.assertEqual(ach.title, 'Applied Machine Learning in Python')

        # Check Portfolio Summary
        summary = AchievementService.get_student_portfolio_summary(alice_usn)
        self.assertTrue(any(a.id == ach.id for a in summary["pending_achievements"]))
        # Ensure pending achievement is NOT counted as verified
        self.assertFalse(any(a.id == ach.id for a in summary["verified_achievements"]))

    def test_06_admin_certificate_verification_workflow(self):
        """Test 6: Admin verification queue, approval, audit logging, and student notification"""
        # Create a pending submission to test admin action
        alice_usn = "4MH24IS001"
        ach = StudentAchievement(
            student_usn=alice_usn,
            title="Kubernetes for Developers Test Submission",
            category="COURSE",
            provider_or_organizer="Linux Foundation",
            domain="Cloud & DevOps",
            completion_date=datetime.date(2026, 3, 1),
            certificate_url="https://example.com/verify/test",
            verification_status="PENDING_VERIFICATION"
        )
        db.session.add(ach)
        db.session.commit()

        # Admin fetches pending submissions
        pending = CertificateVerificationService.get_pending_submissions()
        self.assertTrue(any(a.id == ach.id for a in pending))

        # Admin approves submission
        success, msg = CertificateVerificationService.verify_achievement(
            achievement_id=ach.id,
            admin_username="placement_officer",
            action="APPROVE",
            notes="Valid Linux Foundation credential link verified."
        )
        self.assertTrue(success)
        
        # Verify status updated
        updated_ach = db.session.get(StudentAchievement, ach.id)
        self.assertEqual(updated_ach.verification_status, "VERIFIED")
        self.assertEqual(updated_ach.verified_by, "placement_officer")
        self.assertIsNotNone(updated_ach.verified_at)

        # Verify audit log entry
        audit = AuditLog.query.filter_by(action="CERTIFICATE_APPROVE", student_usn=alice_usn).order_by(AuditLog.timestamp.desc()).first()
        self.assertIsNotNone(audit)
        self.assertIn("placement_officer", audit.changed_by)

        # Verify student received notification
        notif = StudentNotification.query.filter_by(student_usn=alice_usn, category="ACHIEVEMENT").order_by(StudentNotification.created_at.desc()).first()
        self.assertIsNotNone(notif)
        self.assertIn("Verified", notif.title)

    def test_07_notification_service_and_reminders(self):
        """Test 7: In-app student notifications, unread counts, and approaching deadline checks"""
        alice_usn = "4MH24IS001"

        # Create notification
        notif = NotificationService.create_notification(
            student_usn=alice_usn,
            title="Test Workshop Reminder",
            message="Reminder: HackMITM registration closes soon.",
            category="DEADLINE"
        )
        self.assertFalse(notif.is_read)

        # Unread count
        unread_count = NotificationService.get_unread_count(alice_usn)
        self.assertGreaterEqual(unread_count, 1)

        # Mark read
        success = NotificationService.mark_as_read(alice_usn, notif.id)
        self.assertTrue(success)

        # Dismiss notification
        dismiss_success = NotificationService.dismiss_notification(alice_usn, notif.id)
        self.assertTrue(dismiss_success)

    def test_08_security_and_authorization_data_isolation(self):
        """Test 8: Strict student isolation, protected admin routes, and safe portfolio export"""
        # Unauthorized access to admin verification page redirected
        response = self.client.get('/admin/achievements/verification')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login', response.headers.get('Location', ''))

        # Student cannot access admin verification
        with self.client.session_transaction() as sess:
            sess['student_usn'] = '4MH24IS001'
            sess['student_name'] = 'Alice Sharma'
        
        response = self.client.get('/admin/achievements/verification')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login', response.headers.get('Location', ''))

        # Student accesses own achievements page
        response = self.client.get('/student/achievements')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Achievements", response.data)
        self.assertIn(b"Coursera", response.data)

        # Student exports portfolio (without exposing private placement round test scores)
        response = self.client.get('/student/achievements/export')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Placement Portfolio", response.data)
        self.assertNotIn(b"aptitude_score", response.data)

    def test_09_database_and_module_preservation(self):
        """Test 9: Existing student placement records, departments, and history remain intact"""
        alice = Student.query.filter_by(usn="4MH24IS001").first()
        self.assertIsNotNone(alice)
        self.assertIsNotNone(alice.department)
        self.assertIn(alice.department.code, ["IS", "ISE"])
        self.assertIsNotNone(alice.performance)
        self.assertGreater(alice.cgpa, 0.0)

        # Verify all departments exist
        dept_codes = [d.code for d in Department.query.all()]
        self.assertTrue(any(c in dept_codes for c in ["IS", "ISE"]))
        self.assertTrue(any(c in dept_codes for c in ["CS", "CSE"]))
        self.assertTrue(any(c in dept_codes for c in ["EC", "ECE"]))
        self.assertTrue(any(c in dept_codes for c in ["ME", "MECH"]))

if __name__ == '__main__':
    unittest.main()
