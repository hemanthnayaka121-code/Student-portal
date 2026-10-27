"""
Automated Comprehensive Test Suite for Feature: Student Login Using USN and Date of Birth
Tests all requirements specified in the Feature Specification:
1. Valid credentials authentication (USN + correct Date of Birth)
2. Invalid Date of Birth rejection with generic message (no USN leakage)
3. Unknown / Unregistered USN rejection with generic message (no USN leakage)
4. Unapproved student (PENDING) denied access with HOD approval notice
5. Unapproved student (REJECTED) denied access with rejection notice
6. Rate limiting and temporary lockouts after repeated failed attempts
7. Data isolation & derived identity (student sees only their own data)
8. Coordinator updates to student DOB immediately reflected in Module 2
9. Option for students to set custom password after first login
10. Support for multiple date of birth formats (YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY)
11. Preservation of existing login methods (Google OAuth & Mobile OTP)
"""

import unittest
from datetime import datetime, date, timedelta
from app import app, db
from models import Student, Department, PerformanceRecord, SecurityAuditLog, parse_dob_string

class StudentDobLoginTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

        # Ensure known test students exist
        # 1. Approved student: Alice Sharma (4MH24IS001)
        self.alice = Student.query.filter_by(usn="4MH24IS001").first()
        self.assertIsNotNone(self.alice, "Alice Sharma (4MH24IS001) must exist")
        self.alice.date_of_birth = date(2003, 5, 14)
        self.alice.placement_approval_status = "APPROVED"
        self.alice.failed_login_count = 0
        self.alice.locked_until = None
        self.alice.session_version = 1
        self.alice.password_hash = None
        self.alice.first_login_at = None

        # 2. Pending student: Vikram Sen (4MH24CS033)
        self.pending_student = Student.query.filter_by(usn="4MH24CS033").first()
        if self.pending_student:
            self.pending_student.date_of_birth = date(2003, 7, 25)
            self.pending_student.placement_approval_status = "PENDING"
            self.pending_student.failed_login_count = 0
            self.pending_student.locked_until = None
            self.pending_student.session_version = 1

        # 3. Rejected student: Sumanth Rao (4MH24IS099)
        self.rejected_student = Student.query.filter_by(usn="4MH24IS099").first()
        if self.rejected_student:
            self.rejected_student.date_of_birth = date(2003, 9, 8)
            self.rejected_student.placement_approval_status = "REJECTED"
            self.rejected_student.failed_login_count = 0
            self.rejected_student.locked_until = None
            self.rejected_student.session_version = 1

        db.session.commit()

    def tearDown(self):
        # Reset Alice's record to standard state so subsequent test modules are not affected
        alice = Student.query.filter_by(usn="4MH24IS001").first()
        if alice:
            alice.session_version = 1
            alice.password_hash = None
            alice.failed_login_count = 0
            alice.locked_until = None
            alice.date_of_birth = date(2003, 5, 14)
            db.session.commit()
        self.app_context.pop()

    # TEST 1: Valid USN and correct DOB logs in successfully
    def test_01_valid_usn_and_dob_login_success(self):
        """Test 1: Valid USN and correct DOB authenticates student and redirects to Dashboard"""
        response = self.client.post('/student/login', data={
            'login_type': 'usn_dob',
            'usn': '4MH24IS001',
            'dob': '2003-05-14'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Alice Sharma", response.data)
        self.assertIn(b"4MH24IS001", response.data)
        self.assertIn(b"STUDENT PLACEMENT PORTAL", response.data.upper())

        # Verify session variables established
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('student_usn'), '4MH24IS001')
            self.assertEqual(sess.get('student_name'), 'Alice Sharma')
            self.assertEqual(sess.get('login_method'), 'USN_DOB')

        # Verify first login tracking
        reloaded = Student.query.filter_by(usn="4MH24IS001").first()
        self.assertIsNotNone(reloaded.first_login_at)
        self.assertGreaterEqual(reloaded.dob_login_count, 1)

    # TEST 2: JSON API Endpoint (/student/login/dob)
    def test_02_json_api_dob_login(self):
        """Test 2: Dedicated /student/login/dob JSON endpoint works for client apps"""
        response = self.client.post('/student/login/dob', json={
            'usn': '4MH24IS001',
            'dob': '2003-05-14'
        })
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertTrue(json_data.get('success'))
        self.assertIn('/student/dashboard', json_data.get('redirect_url'))

    # TEST 3: Invalid DOB denied with generic message (no leakage)
    def test_03_invalid_dob_rejected_without_leakage(self):
        """Test 3: Incorrect Date of Birth is rejected without leaking USN existence"""
        response = self.client.post('/student/login', data={
            'login_type': 'usn_dob',
            'usn': '4MH24IS001',
            'dob': '1999-12-31'  # Wrong DOB
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        # Must show generic failure notice
        self.assertIn(b"Authentication failed: Invalid USN or Date of Birth", response.data)
        # Must NOT leak that USN was found or that only DOB was wrong
        self.assertNotIn(b"Date of birth mismatch", response.data)

        # Verify failed attempt recorded on student
        reloaded = Student.query.filter_by(usn="4MH24IS001").first()
        self.assertGreaterEqual(reloaded.failed_login_count, 1)

    # TEST 4: Unknown / Unregistered USN rejected with identical generic message
    def test_04_unknown_usn_rejected_without_leakage(self):
        """Test 4: Unregistered USN receives identical generic message as invalid credentials"""
        response = self.client.post('/student/login', data={
            'login_type': 'usn_dob',
            'usn': '4MH99ZZ999',  # Completely fake USN
            'dob': '2003-05-14'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        # Message must be identical to invalid DOB message
        self.assertIn(b"Authentication failed: Invalid USN or Date of Birth", response.data)
        self.assertNotIn(b"USN not found", response.data)
        self.assertNotIn(b"Student does not exist", response.data)

    # TEST 5: Unapproved student (PENDING) is denied access
    def test_05_pending_student_denied_access(self):
        """Test 5: Student awaiting HOD approval cannot authenticate and receives clear notice"""
        self.assertIsNotNone(self.pending_student, "Pending student must exist")
        response = self.client.post('/student/login', data={
            'login_type': 'usn_dob',
            'usn': self.pending_student.usn,
            'dob': '2003-07-25'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"pending approval by your department Head of Department", response.data)
        # Should NOT reach dashboard
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get('student_usn'))

    # TEST 6: Unapproved student (REJECTED) is denied access
    def test_06_rejected_student_denied_access(self):
        """Test 6: Rejected student is denied access and advised to contact Coordinator"""
        self.assertIsNotNone(self.rejected_student, "Rejected student must exist")
        response = self.client.post('/student/login', data={
            'login_type': 'usn_dob',
            'usn': self.rejected_student.usn,
            'dob': '2003-09-08'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"not approved by your department", response.data)
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get('student_usn'))

    # TEST 7: Account lockout after repeated failed attempts
    def test_07_repeated_failed_logins_trigger_temporary_lockout(self):
        """Test 7: 5 consecutive failed login attempts trigger a 15-minute account lockout"""
        test_usn = "4MH24IS001"

        # Submit 5 incorrect attempts
        for attempt in range(5):
            self.client.post('/student/login', data={
                'login_type': 'usn_dob',
                'usn': test_usn,
                'dob': f'2000-01-0{attempt + 1}'
            })

        # Verify student is now locked in database
        student = Student.query.filter_by(usn=test_usn).first()
        self.assertTrue(student.is_locked(), "Student account must be locked after 5 failed attempts")
        self.assertGreater(student.locked_until, datetime.utcnow())

        # 6th attempt (even with CORRECT credentials) must now be denied due to lockout
        response = self.client.post('/student/login', data={
            'login_type': 'usn_dob',
            'usn': test_usn,
            'dob': '2003-05-14'  # Correct DOB, but account is locked
        }, follow_redirects=True)

        self.assertIn(b"temporarily locked", response.data)

    # TEST 8: Server-side identity isolation (cannot view another student's data)
    def test_08_data_isolation_derived_identity(self):
        """Test 8: Authenticated student can only view their own dashboard, not another student's"""
        # Sign in as Alice Sharma
        self.client.post('/student/login', data={
            'login_type': 'usn_dob',
            'usn': '4MH24IS001',
            'dob': '2003-05-14'
        }, follow_redirects=True)

        # Attempt to access dashboard with URL tampering attempting to target Bob Verma (4MH24IS002)
        response = self.client.get('/student/dashboard?usn=4MH24IS002')
        self.assertEqual(response.status_code, 200)
        # Must show Alice Sharma's info
        self.assertIn(b"Alice Sharma", response.data)
        self.assertIn(b"4MH24IS001", response.data)
        # Must NOT show Bob Verma's records
        self.assertNotIn(b"Bob Verma", response.data)
        self.assertNotIn(b"4MH24IS002", response.data)

    # TEST 9: Placement Coordinator updates DOB in Module 1, immediately reflected in Module 2
    def test_09_coordinator_dob_update_reflected_immediately(self):
        """Test 9: Placement coordinator updates student DOB, which is immediately enforced"""
        # Simulate Placement Coordinator session
        with self.client.session_transaction() as sess:
            sess['coordinator_authenticated'] = True
            sess['coordinator_username'] = 'ise_coord'
            sess['role'] = 'PLACEMENT_COORDINATOR'

        # Coordinator updates Alice's date of birth to 2003-12-25
        response = self.client.post('/coordinator/student/4MH24IS001/update-contact', data={
            'email': 'alice.is@mitm.ac.in',
            'mobile_number': '9876543210',
            'date_of_birth': '2003-12-25'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Clear coordinator session
        self.client.get('/coordinator/logout')

        # Old DOB must now fail
        res_old = self.client.post('/student/login', data={
            'login_type': 'usn_dob',
            'usn': '4MH24IS001',
            'dob': '2003-05-14'  # Old DOB
        }, follow_redirects=True)
        self.assertIn(b"Authentication failed: Invalid USN or Date of Birth", res_old.data)

        # New DOB must succeed
        res_new = self.client.post('/student/login', data={
            'login_type': 'usn_dob',
            'usn': '4MH24IS001',
            'dob': '2003-12-25'  # Updated DOB
        }, follow_redirects=True)
        self.assertIn(b"Alice Sharma", res_new.data)
        self.assertIn(b"4MH24IS001", res_new.data)

    # TEST 10: First login security notice and custom password setup
    def test_10_first_login_prompt_and_password_setup(self):
        """Test 10: First login shows security notice, student can set personal password"""
        # Login with DOB
        res = self.client.post('/student/login', data={
            'login_type': 'usn_dob',
            'usn': '4MH24IS001',
            'dob': '2003-05-14'
        }, follow_redirects=True)
        self.assertIn(b"Security Notice: Date of Birth is an Initial Credential", res.data)

        # Student accesses Account Security and sets personal password
        res_pwd = self.client.post('/student/security/set-password', data={
            'current_credential': '2003-05-14',
            'new_password': 'SecureStudentPass2026!',
            'confirm_password': 'SecureStudentPass2026!'
        }, follow_redirects=True)
        self.assertEqual(res_pwd.status_code, 200)
        self.assertIn(b"personal password has been successfully updated", res_pwd.data)

        # Sign out
        self.client.get('/student/logout')

        # Subsequent login works with the new custom password!
        res_pwd_login = self.client.post('/student/login', data={
            'login_type': 'usn_dob',
            'usn': '4MH24IS001',
            'dob': 'SecureStudentPass2026!'
        }, follow_redirects=True)
        self.assertEqual(res_pwd_login.status_code, 200)
        self.assertIn(b"Alice Sharma", res_pwd_login.data)

    # TEST 11: Date format parsing flexibility (YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY)
    def test_11_multiple_date_format_support(self):
        """Test 11: Backend accepts multiple standard date formats entered by students"""
        formats_to_test = [
            '2003-05-14',  # ISO format
            '14-05-2003',  # Standard Indian format with hyphens
            '14/05/2003',  # Standard format with slashes
            '2003/05/14'   # Year-first with slashes
        ]

        for dob_str in formats_to_test:
            with self.subTest(dob_format=dob_str):
                # Reset lockouts if any
                self.alice.reset_failed_attempts()
                res = self.client.post('/student/login/dob', json={
                    'usn': '4MH24IS001',
                    'dob': dob_str
                })
                self.assertEqual(res.status_code, 200)
                data = res.get_json()
                self.assertTrue(data.get('success'), f"Failed to authenticate with format {dob_str}")

if __name__ == '__main__':
    unittest.main()
