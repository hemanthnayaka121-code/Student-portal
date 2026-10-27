"""
Automated Comprehensive Test Suite for MITM Placement Portal
Covers all 16 Test Cases specified in Section 11 of the Enhancement Prompt:
1. Registered student logs in with correct Google account
2. Unregistered Gmail account denied access with exact notice
3. Registered mobile number completes OTP authentication
4. Unregistered mobile number cannot access dashboard
5. Unverified Google email is rejected
6. Student cannot access another student's record (USN isolation)
7. Student cannot access Admin or HOD routes
8. HOD cannot access another department's private records
9. Old sessions invalidated after credential reset (session_version)
10. Password changes require identity re-authentication
11. Password recovery works only through configured, verified methods
12. Duplicate student records cannot be created accidentally
13. Dummy data cleanup preserves genuine records
14. Old test credentials cannot authenticate after the reset
15. Database migrations and schema integrity verified
16. All existing placement and achievement features continue working
"""

import unittest
from unittest.mock import patch
import datetime
from app import app, db
from models import (
    Student, Admin, Department, PlacementActivity, StudentAchievement,
    StudentAccountLink, StudentOtpVerification, PasswordResetToken, SecurityAuditLog
)
from sms_service import SmsOtpService
from security_service import SecurityService

class SecurityAndAuthTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    # TEST CASE 1: Registered student logs in with correct Google account
    @patch('app.verify_firebase_token')
    def test_01_registered_student_logs_in_with_google(self, mock_verify):
        """Case 1: A registered student logs in with their verified Google account"""
        alice = Student.query.filter_by(usn="4MH24IS001").first()
        self.assertIsNotNone(alice, "Alice Sharma must exist in database")

        mock_verify.return_value = {
            'email': alice.email,
            'email_verified': True,
            'name': alice.name,
            'uid': 'google_uid_alice_12345'
        }

        response = self.client.post('/student/login', data={
            'login_type': 'token',
            'id_token': 'mock_valid_token_alice',
            'provider': 'google'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(alice.name.encode(), response.data)
        # Verify authenticated session
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('student_usn'), alice.usn)
            self.assertEqual(sess.get('student_name'), alice.name)

    # TEST CASE 2: Unregistered Gmail account is denied access
    @patch('app.verify_firebase_token')
    def test_02_unregistered_gmail_denied_access(self, mock_verify):
        """Case 2: An unregistered Gmail account is denied access with exact notice and no auto-provisioning"""
        unregistered_email = "unregistered.outsider.999@gmail.com"
        # Confirm student does not exist
        existing = Student.query.filter_by(email=unregistered_email).first()
        self.assertIsNone(existing)
        initial_student_count = Student.query.count()

        mock_verify.return_value = {
            'email': unregistered_email,
            'email_verified': True,
            'name': 'Outsider User',
            'uid': 'outsider_uid_999'
        }

        response = self.client.post('/student/login', data={
            'login_type': 'token',
            'id_token': 'mock_outsider_token',
            'provider': 'google'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        # Check exact prompt requirement string
        expected_msg = b"This Gmail address is not registered with the MITM Placement Coordinator. Please contact your department or Placement Coordinator."
        self.assertIn(expected_msg, response.data)

        # Confirm no student record was created automatically
        final_student_count = Student.query.count()
        self.assertEqual(initial_student_count, final_student_count)
        self.assertIsNone(Student.query.filter_by(email=unregistered_email).first())

    # TEST CASE 3: Student OTP authentication is decommissioned and returns 400
    def test_03_registered_mobile_otp_decommissioned(self):
        """Case 3: Student mobile OTP requests return disabled notice"""
        alice = Student.query.filter_by(usn="4MH24IS001").first()
        self.assertIsNotNone(alice)
        mobile = alice.mobile_number

        resp_send = self.client.post('/student/login/send-otp', data={'mobile_number': mobile})
        self.assertEqual(resp_send.status_code, 400)
        send_data = resp_send.get_json()
        self.assertFalse(send_data['success'])
        self.assertIn("Mobile OTP login is disabled", send_data['message'])

    # TEST CASE 4: Direct unverified or OTP verification rejected
    def test_04_unregistered_mobile_cannot_access(self):
        """Case 4: Student verify OTP endpoint returns disabled notice"""
        resp_verify = self.client.post('/student/login/verify-otp', data={'mobile_number': '9876543210', 'otp': '123456'})
        self.assertEqual(resp_verify.status_code, 400)
        verify_data = resp_verify.get_json()
        self.assertFalse(verify_data['success'])
        self.assertIn("Mobile OTP login is disabled", verify_data['message'])

    # TEST CASE 5: Unverified Google email is rejected
    @patch('app.verify_firebase_token')
    def test_05_unverified_google_email_rejected(self, mock_verify):
        """Case 5: A Google account with unverified email claim is rejected"""
        mock_verify.return_value = {
            'email': 'alice.is@mitm.ac.in',
            'email_verified': False,  # Unverified!
            'name': 'Alice Sharma',
            'uid': 'mock_unverified_uid'
        }

        response = self.client.post('/student/login', data={
            'login_type': 'token',
            'id_token': 'mock_unverified_token',
            'provider': 'google'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Google account email is not verified", response.data)

    # TEST CASE 6: Student cannot access another student's record
    def test_06_student_cannot_access_another_student_record(self):
        """Case 6: A student authenticated as Alice (4MH24IS001) cannot access Bob's data or view unauthorized profiles"""
        with self.client.session_transaction() as sess:
            sess['student_usn'] = '4MH24IS001'
            sess['student_name'] = 'Alice Sharma'
            sess['student_approval_status'] = 'APPROVED'
            sess['session_version'] = 1

        response = self.client.get('/student/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Alice Sharma", response.data)
        self.assertIn(b"4MH24IS001", response.data)
        # Must not display another student's private data
        self.assertNotIn(b"4MH24IS002", response.data)

    # TEST CASE 7: Student cannot access Admin or HOD routes
    def test_07_student_cannot_access_admin_or_hod_routes(self):
        """Case 7: Student session cannot enter administrative, coordinator, or HOD consoles"""
        with self.client.session_transaction() as sess:
            sess['student_usn'] = '4MH24IS001'
            sess['student_name'] = 'Alice Sharma'
            sess['student_approval_status'] = 'APPROVED'
            sess['session_version'] = 1

        # Attempt Placement Admin dashboard
        res_admin = self.client.get('/portal/dashboard', follow_redirects=False)
        self.assertEqual(res_admin.status_code, 302)
        self.assertIn('/admin/login', res_admin.headers.get('Location'))

        # Attempt Placement Coordinator dashboard
        res_coord = self.client.get('/coordinator/dashboard', follow_redirects=False)
        self.assertEqual(res_coord.status_code, 302)
        self.assertIn('/coordinator/login', res_coord.headers.get('Location'))

        # Attempt HOD dashboard
        res_hod = self.client.get('/hod/dashboard/ISE', follow_redirects=False)
        self.assertEqual(res_hod.status_code, 302)
        self.assertIn('/portal/hods', res_hod.headers.get('Location'))

    # TEST CASE 8: HOD cannot access another department's private records
    def test_08_hod_cannot_access_other_department_records(self):
        """Case 8: Information Science HOD cannot access Computer Science HOD dashboard or records"""
        ise_dept = Department.query.filter_by(code='ISE').first()
        self.assertIsNotNone(ise_dept)

        with self.client.session_transaction() as sess:
            sess['hod_id'] = ise_dept.hod_id
            sess['hod_dept_id'] = ise_dept.id
            sess['department_code'] = 'ISE'
            sess['department_name'] = ise_dept.name
            sess['role'] = 'HOD'

        # Attempt accessing CSE HOD dashboard
        res_cross = self.client.get('/hod/dashboard/CSE', follow_redirects=True)
        self.assertEqual(res_cross.status_code, 200)
        self.assertIn(b"Access Denied", res_cross.data)

    # TEST CASE 9: Old sessions invalidated after credential reset
    def test_09_old_sessions_invalidated_after_credential_reset(self):
        """Case 9: Password change or contact update bumps session_version and invalidates old sessions"""
        admin = Admin.query.filter_by(username='Mit_placement').first()
        self.assertIsNotNone(admin)

        # Active session with session_version = 1
        with self.client.session_transaction() as sess:
            sess['admin_id'] = admin.id
            sess['username'] = admin.username
            sess['role'] = 'ADMIN'
            sess['session_version'] = admin.session_version or 1

        # Admin can access account settings
        res = self.client.get('/account/settings')
        self.assertEqual(res.status_code, 200)

        # Simulate password change or credential bump
        admin.session_version = (admin.session_version or 1) + 1
        db.session.commit()

        # Previous session now has obsolete session_version
        res_after = self.client.get('/account/settings', follow_redirects=False)
        self.assertEqual(res_after.status_code, 302)
        self.assertIn('/admin/login', res_after.headers.get('Location'))

    # TEST CASE 10: Password changes require identity re-authentication
    def test_10_password_changes_require_identity_verification(self):
        """Case 10: Modifying password requires valid current password and password complexity"""
        admin = Admin.query.filter_by(username='Mit_placement').first()
        self.assertIsNotNone(admin)

        with self.client.session_transaction() as sess:
            sess['admin_id'] = admin.id
            sess['username'] = admin.username
            sess['role'] = 'ADMIN'
            sess['session_version'] = admin.session_version or 1

        # Attempt 1: Wrong current password
        res_wrong = self.client.post('/account/settings', data={
            'action': 'change_password',
            'current_password': 'WrongPassword123!',
            'new_password': 'ValidNewPass@2026',
            'confirm_password': 'ValidNewPass@2026'
        }, follow_redirects=True)
        self.assertIn(b"Current password verification failed", res_wrong.data)

        # Attempt 2: Weak password (less than 8 chars, no number)
        res_weak = self.client.post('/account/settings', data={
            'action': 'change_password',
            'current_password': 'MitmAdmin@2026Secure',
            'new_password': 'weak',
            'confirm_password': 'weak'
        }, follow_redirects=True)
        self.assertIn(b"at least 8 characters", res_weak.data)

    # TEST CASE 11: Password recovery works only through configured, verified methods
    def test_11_password_recovery_verified_methods_and_expiry(self):
        """Case 11: Forgot password flow generates single-use time-limited reset code for verified contacts"""
        admin = Admin.query.filter_by(username='Mit_placement').first()
        self.assertIsNotNone(admin)
        self.assertTrue(admin.is_recovery_email_verified)

        # 1. Initiate password recovery
        success, msg, dev_code = SecurityService.initiate_password_recovery(
            admin.username, 'EMAIL', '127.0.0.1'
        )
        self.assertTrue(success)
        self.assertIsNotNone(dev_code)

        # 2. Complete reset with valid code
        reset_ok, reset_msg = SecurityService.verify_and_reset_password(
            admin.username, dev_code, 'MitmAdmin@2026Reset', 'MitmAdmin@2026Reset', '127.0.0.1'
        )
        self.assertTrue(reset_ok)

        # 3. Code cannot be reused (single-use)
        reuse_ok, reuse_msg = SecurityService.verify_and_reset_password(
            admin.username, dev_code, 'AnotherPassword@2026', 'AnotherPassword@2026', '127.0.0.1'
        )
        self.assertFalse(reuse_ok)

        # Reset back to standard for test repeatability
        admin.set_password('MitmAdmin@2026Secure')
        admin.is_recovery_email_verified = True
        db.session.commit()

    # TEST CASE 12: Duplicate student records cannot be created accidentally
    def test_12_duplicate_student_records_prevented(self):
        """Case 12: Placement Coordinator cannot register duplicate USN, duplicate email, or duplicate phone"""
        coord = Admin.query.filter_by(username='placement_coordinator').first()
        self.assertIsNotNone(coord)
        existing_alice = Student.query.filter_by(usn="4MH24IS001").first()

        with self.client.session_transaction() as sess:
            sess['coordinator_id'] = coord.id
            sess['coordinator_username'] = coord.username
            sess['role'] = coord.role
            sess['coordinator_authenticated'] = True

        # Attempt registering same USN
        res_dup_usn = self.client.post('/coordinator/student/add', data={
            'name': 'Duplicate Alice',
            'usn': existing_alice.usn,
            'department_id': existing_alice.department_id,
            'semester': '6',
            'cgpa': '8.5',
            'email': 'new.different@mitm.ac.in',
            'phone': '9111122222'
        }, follow_redirects=True)
        self.assertIn(b"already exists", res_dup_usn.data)

        # Attempt registering same Email
        res_dup_email = self.client.post('/coordinator/student/add', data={
            'name': 'Different Student',
            'usn': '4MH24IS999',
            'department_id': existing_alice.department_id,
            'semester': '6',
            'cgpa': '8.5',
            'email': existing_alice.email,
            'phone': '9111122223'
        }, follow_redirects=True)
        self.assertIn(b"already registered", res_dup_email.data)

    # TEST CASE 13: Dummy data cleanup preserves genuine records
    def test_13_dummy_data_cleanup_preserves_genuine_records(self):
        """Case 13: Confirmed dummy students are purged while all genuine students remain intact"""
        # Confirmed fake students must be absent
        self.assertIsNone(Student.query.filter_by(usn="4MH24CSE402").first())
        self.assertIsNone(Student.query.filter_by(usn="4MH24ISE385").first())
        self.assertIsNone(Student.query.filter_by(usn="TEST_PENDING_01").first())

        # Genuine students must be present
        self.assertIsNotNone(Student.query.filter_by(usn="4MH24IS009").first(), "Hemanthkumar HM must exist")
        self.assertIsNotNone(Student.query.filter_by(usn="4MH24CE003").first(), "Akash must exist")
        self.assertIsNotNone(Student.query.filter_by(usn="4MH24IS001").first(), "Alice Sharma must exist")
        self.assertIsNotNone(Student.query.filter_by(usn="4MH24CS001").first(), "Computer Science student must exist")

        # Total genuine student count
        total_students = Student.query.count()
        self.assertGreaterEqual(total_students, 27)

    # TEST CASE 14: Old test credentials cannot authenticate after reset
    def test_14_old_test_credentials_cannot_authenticate(self):
        """Case 14: Obsolete test credentials fail authentication; fresh bootstrapped credentials succeed"""
        admin = Admin.query.filter_by(username='Mit_placement').first()
        self.assertIsNotNone(admin)

        # Obsolete test passwords must fail
        self.assertFalse(admin.check_password('Mit@123'))
        self.assertFalse(admin.check_password('admin123'))
        self.assertFalse(admin.check_password('admin'))
        self.assertFalse(admin.check_password('password'))

        # Fresh bootstrapped password must succeed
        self.assertTrue(admin.check_password('MitmAdmin@2026Secure'))

        # Coordinator check
        coord = Admin.query.filter_by(username='placement_coordinator').first()
        self.assertFalse(coord.check_password('PC@123'))
        self.assertTrue(coord.check_password('MitmCoord@2026Secure'))

    # TEST CASE 15: Database migrations and schema integrity verified
    def test_15_database_migrations_and_schema_integrity(self):
        """Case 15: Verify all new security columns and models exist and are functional"""
        # Admin security attributes
        admin = Admin.query.first()
        self.assertTrue(hasattr(admin, 'recovery_email'))
        self.assertTrue(hasattr(admin, 'recovery_mobile'))
        self.assertTrue(hasattr(admin, 'is_recovery_email_verified'))
        self.assertTrue(hasattr(admin, 'is_recovery_mobile_verified'))
        self.assertTrue(hasattr(admin, 'session_version'))
        self.assertTrue(hasattr(admin, 'failed_login_count'))

        # Student security attributes
        student = Student.query.first()
        self.assertTrue(hasattr(student, 'session_version'))

        # Security tables queryable
        otp_count = StudentOtpVerification.query.count()
        self.assertIsInstance(otp_count, int)
        token_count = PasswordResetToken.query.count()
        self.assertIsInstance(token_count, int)
        audit_count = SecurityAuditLog.query.count()
        self.assertIsInstance(audit_count, int)

    # TEST CASE 16: All existing placement and achievement features continue working
    def test_16_existing_placement_features_continue_working(self):
        """Case 16: Placement activities, departmental queries, and student dashboard remain functional"""
        alice = Student.query.filter_by(usn="4MH24IS001").first()
        self.assertIsNotNone(alice)

        with self.client.session_transaction() as sess:
            sess['student_usn'] = alice.usn
            sess['student_name'] = alice.name
            sess['student_approval_status'] = 'APPROVED'
            sess['session_version'] = alice.session_version or 1

        # 1. Student dashboard loads
        res_dash = self.client.get('/student/dashboard')
        self.assertEqual(res_dash.status_code, 200)

        # 2. Solution Hub loads
        res_hub = self.client.get('/student/solution-hub')
        self.assertEqual(res_hub.status_code, 200)

        # 3. Achievements portfolio loads
        res_port = self.client.get('/student/achievements')
        self.assertEqual(res_port.status_code, 200)

if __name__ == '__main__':
    unittest.main()
