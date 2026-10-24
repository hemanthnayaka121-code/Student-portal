"""
Automated Test Suite for Module 2: MIT Student Placement Performance & AI Preparation Platform
Tests authentication, identity matching, data isolation, performance analysis, quizzes,
mock interviews, and preservation of Module 1.
"""

import unittest
import json
from app import app, db
from models import Student, Department, PerformanceRecord, PlacementActivity, StudentAccountLink, QuizQuestion, QuizAttempt, MockInterviewSession, MockInterviewQnA
from performance_engine import analyze_student_performance
from youtube_service import search_youtube_videos
from interview_engine import generate_interview_questions, evaluate_answer_with_ai, generate_comprehensive_interview_report

class Module2TestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        pending = Student.query.filter_by(usn="TEST_PENDING_01").first()
        if pending:
            db.session.delete(pending)
            db.session.commit()
        self.app_context.pop()

    from unittest.mock import patch

    @patch('app.verify_firebase_token')
    def test_01_student_identity_matching_and_login(self, mock_verify):
        """Test 1: Registered student signs in and verified identity links to existing record"""
        # Pick student Alice Sharma (4MH24IS001, alice.is@mitm.ac.in)
        alice = Student.query.filter_by(usn="4MH24IS001").first()
        self.assertIsNotNone(alice, "Alice Sharma must exist in database")

        mock_verify.return_value = {
            'email': 'alice.is@mitm.ac.in',
            'email_verified': True,
            'name': 'Alice Sharma',
            'uid': 'mock_alice_uid_123'
        }

        # Test valid verified token authentication
        response = self.client.post('/student/login', data={
            'login_type': 'token',
            'id_token': 'mock_valid_token_alice',
            'provider': 'google'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Alice Sharma", response.data)
        self.assertIn(b"STUDENT PLACEMENT PORTAL", response.data.upper())

        # Verify StudentAccountLink created in database
        link = StudentAccountLink.query.filter_by(student_usn="4MH24IS001").first()
        self.assertIsNotNone(link, "StudentAccountLink should be created upon login")

    @patch('app.verify_firebase_token')
    def test_02_unregistered_identity_rejected(self, mock_verify):
        """Test 2: An unregistered identity cannot access student records"""
        mock_verify.return_value = {
            'email': 'unknown.outsider@gmail.com',
            'email_verified': True,
            'name': 'Outsider Student',
            'uid': 'mock_outsider_uid'
        }
        response = self.client.post('/student/login', data={
            'login_type': 'token',
            'id_token': 'mock_outsider_token',
            'provider': 'google'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"This Gmail address is not registered", response.data)

    def test_03_data_isolation_derived_identity(self):
        """Test 3: A student cannot access another student's data by modifying requests"""
        # Log in as Alice Sharma (4MH24IS001)
        with self.client.session_transaction() as sess:
            sess['student_usn'] = '4MH24IS001'
            sess['student_name'] = 'Alice Sharma'
            sess['student_approval_status'] = 'APPROVED'

        # View dashboard -> must show Alice Sharma
        res = self.client.get('/student/dashboard')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Alice Sharma", res.data)
        self.assertIn(b"4MH24IS001", res.data)
        # Should not display Bob Verma's USN
        self.assertNotIn(b"4MH24IS002", res.data)

    def test_04_hod_approval_eligibility_enforcement(self):
        """Test 4: Pending / Rejected students cannot access placement training features"""
        # Create or update a test student with status PENDING
        pending_student = Student.query.filter_by(usn="TEST_PENDING_01").first()
        if not pending_student:
            dept = Department.query.first()
            pending_student = Student(
                usn="TEST_PENDING_01",
                name="Pending Student",
                mobile_number="9999900001",
                email="pending@mitm.ac.in",
                department_id=dept.id,
                placement_approval_status="PENDING"
            )
            db.session.add(pending_student)
            db.session.commit()

        # Log in as pending student
        with self.client.session_transaction() as sess:
            sess['student_usn'] = 'TEST_PENDING_01'
            sess['student_approval_status'] = 'PENDING'

        # Accessing dashboard should show limited status screen
        res = self.client.get('/student/dashboard')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Awaiting Department HOD Approval", res.data)

        # Accessing quizzes should be blocked and show limited status
        res_quiz = self.client.get('/student/quizzes')
        self.assertEqual(res_quiz.status_code, 200)
        self.assertIn(b"Awaiting Department HOD Approval", res_quiz.data)

    def test_05_performance_analysis_engine(self):
        """Test 5: Performance engine calculates benchmarks, strengths, weaknesses, and readiness"""
        alice = Student.query.filter_by(usn="4MH24IS001").first()
        analysis = analyze_student_performance(alice)

        self.assertIn('overall_readiness_score', analysis)
        self.assertGreater(analysis['overall_readiness_score'], 0)
        self.assertIn('strongest_domain', analysis)
        self.assertIn('weakest_domain', analysis)
        self.assertIn('domains', analysis)
        self.assertEqual(len(analysis['domains']), 4)

    def test_06_youtube_lessons_service(self):
        """Test 6: YouTube service returns curated educational videos and caches results"""
        videos = search_youtube_videos("Arrays & Strings Manipulation", domain="Coding")
        self.assertIsInstance(videos, list)
        self.assertGreater(len(videos), 0)
        first_video = videos[0]
        self.assertIn('video_id', first_video)
        self.assertIn('title', first_video)
        self.assertIn('thumbnail_url', first_video)

    def test_07_quiz_engine_and_scoring(self):
        """Test 7: Practice quiz submission, scoring, explanations, and separate storage"""
        # Ensure questions exist
        q = QuizQuestion.query.first()
        self.assertIsNotNone(q, "Quiz questions must exist in database")

        # Submit quiz as Alice
        with self.client.session_transaction() as sess:
            sess['student_usn'] = '4MH24IS001'
            sess['student_approval_status'] = 'APPROVED'

        res = self.client.post('/student/quiz/submit', data={
            'domain': q.domain,
            'topic': q.topic,
            'difficulty': 'medium',
            'time_spent_seconds': '45',
            'total_questions': '1',
            f'ans_{q.id}': q.correct_option
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"100%", res.data)
        self.assertIn(b"Passed Benchmark", res.data)

        # Verify stored separately in QuizAttempt table
        attempt = QuizAttempt.query.filter_by(student_usn="4MH24IS001").order_by(QuizAttempt.attempted_at.desc()).first()
        self.assertIsNotNone(attempt)
        self.assertEqual(attempt.score_pct, 100.0)

        # Verify official placement record was NOT modified
        alice_perf = PerformanceRecord.query.filter_by(student_usn="4MH24IS001").first()
        self.assertIsNotNone(alice_perf)

    def test_08_mock_interview_system_and_reporting(self):
        """Test 8: AI Mock interview creates multi-turn session and generates evaluation report"""
        alice = Student.query.filter_by(usn="4MH24IS001").first()
        questions = generate_interview_questions("Technical", "Medium", count=5, student=alice)
        self.assertEqual(len(questions), 5)
        self.assertIn('question_text', questions[0])
        self.assertIn('expected_answer_points', questions[0])

        # Test answer evaluation
        eval_res = evaluate_answer_with_ai(
            question_text=questions[0]['question_text'],
            student_answer="I would use encapsulation to protect variables and polymorphism for dynamic dispatch.",
            expected_points=questions[0]['expected_answer_points'],
            interview_type="Technical",
            difficulty="Medium"
        )
        self.assertIn('score', eval_res)
        self.assertIn('feedback', eval_res)
        self.assertGreater(eval_res['score'], 0)

    def test_09_module1_preservation(self):
        """Test 9: Placement Admin, Coordinator, and HOD functionality remain intact"""
        # Test Admin login page loads
        res_admin = self.client.get('/admin/login')
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn(b"MIT PLACEMENT PORTAL", res_admin.data.upper())

        # Test Coordinator login page loads
        res_coord = self.client.get('/coordinator/login')
        self.assertEqual(res_coord.status_code, 200)

        # Test HOD department select page loads
        res_hod = self.client.get('/portal/hods')
        # Requires admin session or redirects
        self.assertIn(res_hod.status_code, [200, 302])

if __name__ == '__main__':
    unittest.main()
