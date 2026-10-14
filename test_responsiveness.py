import unittest
import re
from app import app, db
from models import Student, MockInterviewSession

class TestMobileResponsiveness(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def test_student_login_page_renders_mobile_meta(self):
        resp = self.client.get('/student/login')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn('viewport', html)
        self.assertIn('width=device-width', html)
        self.assertIn('student-auth-card', html)

    def test_student_authenticated_views_render_mobile_navigation(self):
        with self.client.session_transaction() as sess:
            sess['student_id'] = 1
            sess['student_usn'] = '4MH24IS001'
            sess['student_name'] = 'Alice Sharma'
            sess['student_email'] = 'alice.is@mitm.ac.in'

        routes = [
            '/student/dashboard',
            '/student/performance',
            '/student/analysis',
            '/student/recommendations',
            '/student/youtube',
            '/student/quizzes',
            '/student/mock-interview',
            '/student/history',
            '/student/profile',
            '/student/security',
            '/student/interview-reports'
        ]

        for route in routes:
            resp = self.client.get(route)
            self.assertEqual(resp.status_code, 200, f"Route {route} failed with status {resp.status_code}")
            html = resp.get_data(as_text=True)
            
            # Check Mobile Viewport
            self.assertIn('viewport-fit=cover', html, f"Route {route} missing viewport-fit=cover")
            
            # Check Mobile Header & Bottom Navigation Bar
            self.assertIn('student-mobile-header', html, f"Route {route} missing mobile header")
            self.assertIn('student-mobile-bottom-nav', html, f"Route {route} missing bottom nav")
            self.assertIn('portal-sidebar-overlay', html, f"Route {route} missing mobile overlay")

            # Check that all tables have table-responsive wrapper
            table_matches = re.findall(r'<table class="portal-table', html)
            table_resp_matches = re.findall(r'class="table-responsive"', html)
            if table_matches:
                self.assertGreaterEqual(len(table_resp_matches), len(table_matches),
                    f"Route {route} has {len(table_matches)} tables but only {len(table_resp_matches)} table-responsive wrappers")

    def test_quiz_attempt_mobile_features(self):
        with self.client.session_transaction() as sess:
            sess['student_id'] = 1
            sess['student_usn'] = '4MH24IS001'
            sess['student_name'] = 'Alice Sharma'
            sess['student_email'] = 'alice.is@mitm.ac.in'

        resp = self.client.post('/student/quiz/start', data={
            'domain': 'Coding',
            'difficulty': 'medium',
            'count': '5',
            'is_timed': '1'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        # Check touch-friendly option cards
        self.assertIn('quiz-option-card', html)
        # Check duplicate submission prevention and localStorage autosave
        self.assertIn('handleQuizSubmit', html)
        self.assertIn('quizStorageKey', html)

    def test_mock_interview_mobile_features(self):
        with self.client.session_transaction() as sess:
            sess['student_id'] = 1
            sess['student_usn'] = '4MH24IS001'
            sess['student_name'] = 'Alice Sharma'
            sess['student_email'] = 'alice.is@mitm.ac.in'

        resp = self.client.post('/student/mock-interview/create', data={
            'interview_type': 'Technical',
            'difficulty': 'Medium',
            'question_count': '5',
            'programming_language': 'Python'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        # Check Code Mode toggle
        self.assertIn('toggleCodeEditor', html)
        # Check hands-free voice status bar
        self.assertIn('live-conversation-bar', html)
        # Check audio cleanup
        self.assertIn('beforeunload', html)

    def test_scope_isolation_admin_department_portals_unaffected(self):
        # Verify base.html remains clean for Admin and Department Coordinators
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            base_html = f.read()

        # base.html should NOT contain student mobile navigation elements
        self.assertNotIn('student-mobile-bottom-nav', base_html)
        self.assertNotIn('student-mobile-header', base_html)

    def test_css_contains_mobile_breakpoints(self):
        with open('static/css/style.css', 'r', encoding='utf-8') as f:
            css = f.read()

        # Check critical responsive media queries
        self.assertIn('@media (max-width: 991px)', css)
        self.assertIn('@media (max-width: 599px)', css)
        self.assertIn('@media (max-width: 359px)', css)

        # Check touch target sizes
        self.assertIn('44px', css)
        self.assertIn('48px', css)

        # Check iOS auto-zoom prevention
        self.assertIn('font-size: 16px', css)

        # Check safe-area inset
        self.assertIn('safe-area-inset-bottom', css)

if __name__ == '__main__':
    unittest.main()
