"""
test_unified_learning.py — Comprehensive Test Suite for Unified Learning & Automatic Certificate Achievements
Covers:
1. Coursera OAuth 2.0 flow & CSRF state validation.
2. ExternalAccountService linking, status checking, and unlinking.
3. LearningProgressSyncService incremental sync, deduplication, and CertificateSyncLog auditing.
4. Workshop and Hackathon integration services (Method A automatic organizer verification).
5. Method B manual submission, admin verification, and duplicate rejection.
6. Server-side ownership validation and IDOR prevention on certificate endpoints.
7. Course catalog discovery, domain/pricing filters, and branch-tailored recommendations.
"""

import os
import unittest
from datetime import datetime, date
from app import app, db
from models import (
    Student, Department, Course, StudentCourseProgress,
    StudentAchievement, ExternalProviderAccount, CertificateSyncLog,
    WorkshopEvent, StudentEventAction, Admin
)
from external_account_service import ExternalAccountService
from coursera_service import CourseraIntegrationService
from sync_service import LearningProgressSyncService
from event_integration_service import WorkshopIntegrationService, HackathonIntegrationService
from achievement_service import AchievementService
from course_service import CourseDiscoveryService

class TestUnifiedLearning(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app
        self.client = app.test_client()
        self.s1_usn = "4MH24IS001"
        self.s2_usn = "4MH24IS002"
        self.created_ach_ids = []

    def tearDown(self):
        with app.app_context():
            # Clean up test accounts, achievements, sync logs
            ExternalProviderAccount.query.filter(ExternalProviderAccount.student_usn.in_([self.s1_usn, self.s2_usn])).delete()
            CertificateSyncLog.query.filter(CertificateSyncLog.student_usn.in_([self.s1_usn, self.s2_usn])).delete()
            if self.created_ach_ids:
                StudentAchievement.query.filter(StudentAchievement.id.in_(self.created_ach_ids)).delete()
            db.session.commit()

    # ---------------------------------------------------------
    # 1. Coursera Integration Service & OAuth Flow Tests
    # ---------------------------------------------------------
    def test_coursera_oauth_url_and_state_generation(self):
        """Verifies OAuth authorization URL builder and CSRF state generation."""
        state = CourseraIntegrationService.generate_oauth_state()
        self.assertTrue(len(state) >= 16)

        # When credentials configured
        os.environ['COURSERA_CLIENT_ID'] = 'test_partner_client_id'
        auth_res = CourseraIntegrationService.build_authorization_url(
            redirect_uri="http://localhost:5000/integrations/coursera/callback",
            state=state,
            user_email="alice@mitmysore.in"
        )
        self.assertTrue(auth_res["success"])
        self.assertIn("coursera.org/oauth2/v1/auth", auth_res["auth_url"])
        self.assertIn(f"state={state}", auth_res["auth_url"])
        self.assertIn("response_type=code", auth_res["auth_url"])
        self.assertIn("login_hint=alice%40mitmysore.in", auth_res["auth_url"])

    def test_coursera_token_exchange_test_mode(self):
        """Tests deterministic test code exchange and token payload."""
        token_res = CourseraIntegrationService.exchange_code_for_tokens(
            code="test_code_demo_123",
            redirect_uri="http://localhost:5000/integrations/coursera/callback"
        )
        self.assertTrue(token_res["success"])
        self.assertIn("access_token", token_res)
        self.assertEqual(token_res.get("token_type"), "Bearer")

    def test_coursera_profile_and_certificate_retrieval_test_mode(self):
        """Tests learner profile and certificate retrieval in test/mock mode."""
        profile = CourseraIntegrationService.fetch_learner_profile("mock_token_abc")
        self.assertTrue(profile["success"])
        self.assertIn("external_account_id", profile)
        self.assertIn("email", profile)

        certs = CourseraIntegrationService.fetch_verified_certificates("mock_token_abc")
        self.assertIsInstance(certs, list)
        self.assertTrue(len(certs) > 0)
        self.assertIn("external_certificate_id", certs[0])
        self.assertIn("title", certs[0])

    # ---------------------------------------------------------
    # 2. ExternalAccountService Tests
    # ---------------------------------------------------------
    def test_external_account_link_and_status(self):
        """Tests linking an external account and querying connection status."""
        with self.app.app_context():
            account = ExternalAccountService.link_account(
                student_usn=self.s1_usn,
                provider_name="coursera",
                external_account_id="crsa_user_alice_999",
                external_email="alice.tester@gmail.com",
                access_token="test_access_token_123",
                refresh_token="test_refresh_token_123"
            )
            self.assertIsNotNone(account)
            self.assertEqual(account.connection_status, "CONNECTED")
            self.assertEqual(account.external_email, "alice.tester@gmail.com")

            # Check status service
            status = ExternalAccountService.get_connection_status(self.s1_usn, "coursera")
            self.assertTrue(status["is_connected"])
            self.assertEqual(status["external_email"], "alice.tester@gmail.com")

            # Test Disconnect
            disconnected = ExternalAccountService.disconnect_account(self.s1_usn, "coursera")
            self.assertTrue(disconnected)

            status_after = ExternalAccountService.get_connection_status(self.s1_usn, "coursera")
            self.assertFalse(status_after["is_connected"])
            self.assertEqual(status_after["status"], "DISCONNECTED")

    # ---------------------------------------------------------
    # 3. LearningProgressSyncService Tests
    # ---------------------------------------------------------
    def test_sync_service_incremental_sync_and_deduplication(self):
        """Tests automated certificate sync, audit logging, and duplicate prevention."""
        with self.app.app_context():
            # First link an account
            ExternalAccountService.link_account(
                student_usn=self.s1_usn,
                provider_name="coursera",
                external_account_id="crsa_user_alice_999",
                external_email="alice.tester@gmail.com",
                access_token="test_access_token_sync"
            )

            # Run sync
            result = LearningProgressSyncService.sync_coursera_for_student(self.s1_usn)
            self.assertTrue(result["success"])
            self.assertGreater(result["certificates_synced"], 0)

            # Check CertificateSyncLog
            log = CertificateSyncLog.query.filter_by(student_usn=self.s1_usn).order_by(CertificateSyncLog.id.desc()).first()
            self.assertIsNotNone(log)
            self.assertEqual(log.sync_status, "SUCCESS")
            self.assertGreater(log.certificates_found, 0)

            # Check achievements created
            achievements = StudentAchievement.query.filter_by(student_usn=self.s1_usn, is_coursera_sync=True).all()
            self.assertGreater(len(achievements), 0)
            self.created_ach_ids.extend([a.id for a in achievements])
            first_ach = achievements[0]
            self.assertEqual(first_ach.verification_status, "VERIFIED")
            self.assertIn("Coursera", first_ach.provider_or_organizer)
            self.assertIsNotNone(first_ach.external_certificate_id)

            initial_count = len(achievements)

            # Re-running sync must NOT create duplicates (deduplication check)
            result2 = LearningProgressSyncService.sync_coursera_for_student(self.s1_usn)
            self.assertTrue(result2["success"])
            self.assertEqual(result2["certificates_synced"], 0)  # zero new, all existing skipped

            final_count = StudentAchievement.query.filter_by(student_usn=self.s1_usn, is_coursera_sync=True).count()
            self.assertEqual(initial_count, final_count)

    # ---------------------------------------------------------
    # 4. Workshop and Hackathon Integration Services (Method A & B)
    # ---------------------------------------------------------
    def test_method_a_automatic_workshop_and_hackathon_verification(self):
        """Tests Method A: Automatic verification via organizer API or webhook."""
        with self.app.app_context():
            # 1. Automatic workshop verification
            event = WorkshopEvent.query.first()
            self.assertIsNotNone(event)
            succ_w, msg_w = WorkshopIntegrationService.verify_workshop_completion(
                student_usn=self.s1_usn,
                event_id=event.id,
                certificate_url=f"https://mitmysore.in/verify/workshop/{event.id}",
                verifier_identity="AWS Educate Campus Lead"
            )
            self.assertTrue(succ_w)
            ach_w = StudentAchievement.query.filter_by(
                student_usn=self.s1_usn,
                title=event.title
            ).first()
            self.assertIsNotNone(ach_w)
            self.created_ach_ids.append(ach_w.id)
            self.assertEqual(ach_w.verification_status, "VERIFIED")
            self.assertEqual(ach_w.category, "WORKSHOP")

            # 2. Automatic hackathon verification
            succ_h, msg_h = HackathonIntegrationService.verify_hackathon_participation(
                student_usn=self.s1_usn,
                hackathon_title="National Coding League 2025 Test",
                organizer="MoE Innovation Cell & MITM",
                domain="AI & Competitive Coding",
                award_or_rank="1st Place Winner",
                certificate_url="https://sih.gov.in/verify/NCL-2025-MITM-001",
                verifier_identity="SIH Single Point of Contact"
            )
            self.assertTrue(succ_h)
            ach_h = StudentAchievement.query.filter_by(
                student_usn=self.s1_usn,
                title="National Coding League 2025 Test"
            ).first()
            self.assertIsNotNone(ach_h)
            self.created_ach_ids.append(ach_h.id)
            self.assertEqual(ach_h.verification_status, "VERIFIED")
            self.assertEqual(ach_h.category, "HACKATHON")
            self.assertIn("National Coding League", ach_h.title)

            # Check portfolio counts reflect workshops and hackathons
            portfolio = AchievementService.get_student_portfolio_summary(self.s1_usn)
            self.assertGreaterEqual(portfolio["workshops_attended"], 1)
            self.assertGreaterEqual(portfolio["hackathons_participated"], 1)

    def test_method_b_manual_submission_and_admin_approval(self):
        """Tests Method B: Manual certificate submission and admin approval flow."""
        with self.app.app_context():
            from achievement_service import CertificateVerificationService
            sub_data = {
                'title': "Deep Learning Specialization Test",
                'category': "COURSE",
                'provider_or_organizer': "deeplearning.ai",
                'domain': "AI/ML",
                'completion_date': "2025-02-01",
                'certificate_url': "https://coursera.org/verify/specialization/XYZ789",
                'skills_acquired': "Neural Networks, PyTorch",
                'description': "Completed 5-course specialization in deep learning"
            }
            # Student submits certificate
            ach = AchievementService.submit_achievement(
                student_usn=self.s1_usn,
                data=sub_data
            )
            self.assertIsNotNone(ach)
            self.created_ach_ids.append(ach.id)
            self.assertEqual(ach.verification_status, "PENDING_VERIFICATION")

            # Admin approves
            admin = Admin.query.first()
            succ, msg = CertificateVerificationService.verify_achievement(
                achievement_id=ach.id,
                admin_username=admin.username,
                action="APPROVE",
                notes="Verified on official portal"
            )
            self.assertTrue(succ)
            reloaded = StudentAchievement.query.get(ach.id)
            self.assertEqual(reloaded.verification_status, "VERIFIED")
            self.assertEqual(reloaded.verified_by, admin.username)

    # ---------------------------------------------------------
    # 5. Security & IDOR Prevention Tests
    # ---------------------------------------------------------
    def test_idor_protection_certificate_access(self):
        """
        Critical security test:
        Verifies that Student A (Bob) CANNOT view or download Student B's (Alice's) certificate.
        Must return 403 Forbidden.
        """
        with self.app.app_context():
            # Create a private certificate belonging to Alice
            alice_cert = StudentAchievement(
                student_usn=self.s1_usn,
                title="Alice Confidential Certificate",
                category="COURSE",
                achievement_type="COURSE",
                provider_or_organizer="Secret Provider",
                domain="Computer Science",
                completion_date=date(2025, 1, 1),
                certificate_url="https://secure.example.com/alice_cert",
                verification_status="VERIFIED"
            )
            db.session.add(alice_cert)
            db.session.commit()
            cert_id = alice_cert.id
            self.created_ach_ids.append(cert_id)

        # 1. Bob tries to access Alice's certificate via API/view
        with self.client.session_transaction() as sess:
            sess['student_usn'] = self.s2_usn  # Bob is logged in
            sess.pop('admin_id', None)

        resp_view = self.client.get(f'/student/achievements/certificate/{cert_id}/view')
        self.assertEqual(resp_view.status_code, 403, "Bob should get 403 when viewing Alice's certificate")

        resp_dl = self.client.get(f'/student/achievements/certificate/{cert_id}/download')
        self.assertEqual(resp_dl.status_code, 403, "Bob should get 403 when downloading Alice's certificate")

        # 2. Alice accesses her own certificate -> should succeed (redirects to external URL or serves file)
        with self.client.session_transaction() as sess:
            sess['student_usn'] = self.s1_usn  # Alice is logged in

        resp_alice = self.client.get(f'/student/achievements/certificate/{cert_id}/view')
        self.assertIn(resp_alice.status_code, [200, 302], "Alice should be permitted to view her own certificate")

    # ---------------------------------------------------------
    # 6. Filtering, Sorting, and Search Tests
    # ---------------------------------------------------------
    def test_filtered_achievements_search_and_sort(self):
        """Tests filtering achievements by category, status, keyword search, and sorting."""
        with self.app.app_context():
            # Add diverse achievements for Alice
            ach1 = StudentAchievement(
                student_usn=self.s1_usn,
                title="Advanced Data Structures in C++",
                category="COURSE",
                achievement_type="COURSE",
                provider_or_organizer="NPTEL",
                domain="Computer Science",
                completion_date=date(2024, 6, 1),
                verification_status="VERIFIED"
            )
            ach2 = StudentAchievement(
                student_usn=self.s1_usn,
                title="Machine Learning Bootcamp",
                category="WORKSHOP",
                achievement_type="WORKSHOP",
                provider_or_organizer="VTU Hub",
                domain="AI/ML",
                completion_date=date(2024, 11, 1),
                verification_status="PENDING_VERIFICATION"
            )
            ach3 = StudentAchievement(
                student_usn=self.s1_usn,
                title="Web3 Hackathon Finalist",
                category="HACKATHON",
                achievement_type="HACKATHON",
                provider_or_organizer="ETHGlobal",
                domain="Web3",
                completion_date=date(2025, 1, 15),
                verification_status="VERIFIED"
            )
            db.session.add_all([ach1, ach2, ach3])
            db.session.commit()
            self.created_ach_ids.extend([ach1.id, ach2.id, ach3.id])

            # Filter by Category WORKSHOP
            res_workshop = AchievementService.get_filtered_achievements(self.s1_usn, category="WORKSHOP")
            self.assertTrue(any(a.id == ach2.id for a in res_workshop))
            self.assertTrue(all(a.category == "WORKSHOP" for a in res_workshop))

            # Filter by Status VERIFIED
            res_verified = AchievementService.get_filtered_achievements(self.s1_usn, status="VERIFIED")
            self.assertTrue(all(a.verification_status == "VERIFIED" for a in res_verified))
            self.assertTrue(any(a.id == ach1.id for a in res_verified))
            self.assertTrue(any(a.id == ach3.id for a in res_verified))

            # Search by keyword "Web3"
            res_search = AchievementService.get_filtered_achievements(self.s1_usn, search_query="Web3")
            self.assertTrue(any(a.id == ach3.id for a in res_search))

            # Sort by oldest
            res_oldest = AchievementService.get_filtered_achievements(self.s1_usn, sort_by="oldest")
            self.assertGreaterEqual(len(res_oldest), 3)
            # Oldest should be on or before newest
            self.assertLessEqual(res_oldest[0].completion_date, res_oldest[-1].completion_date)

    # ---------------------------------------------------------
    # 7. Course Catalog Discovery & Domain Filters
    # ---------------------------------------------------------
    def test_course_discovery_filters(self):
        """Tests CourseDiscoveryService filters: free, paid, domain, and branch recommendations."""
        with self.app.app_context():
            # Filter free courses
            free_courses = CourseDiscoveryService.get_courses(free_only=True)
            self.assertTrue(all(c.is_free for c in free_courses))

            # Filter paid courses
            paid_courses = CourseDiscoveryService.get_courses(paid_only=True)
            self.assertTrue(all(not c.is_free for c in paid_courses))

            # Filter domain Python
            py_courses = CourseDiscoveryService.get_courses(domain="Python")
            self.assertTrue(all("python" in (c.domain or "").lower() or "python" in (c.title or "").lower() for c in py_courses))

            # Recommendations for ISE student
            student = Student.query.filter_by(usn=self.s1_usn).first()
            recs = CourseDiscoveryService.get_recommended_courses_for_student(student)
            self.assertIsInstance(recs, list)
            self.assertGreater(len(recs), 0)

if __name__ == '__main__':
    unittest.main()
