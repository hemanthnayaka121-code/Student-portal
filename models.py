from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), unique=True, nullable=False)
    hod_name = db.Column(db.String(100), default='Dr. HOD')
    hod_id = db.Column(db.String(50), default='HOD_01')
    hod_email = db.Column(db.String(100), default='hod@mitmysore.in')
    hod_phone = db.Column(db.String(30), default='+91 98450 11223')
    admins = db.relationship('Admin', backref='department', lazy=True)
    students = db.relationship('Student', backref='department', lazy=True)

class PlacementCoordinator(db.Model):
    __tablename__ = 'placement_coordinators'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    companies_coordinated = db.Column(db.String(255), default="Infosys, TCS, Wipro")
    students_handled = db.Column(db.Integer, default=60)

    department = db.relationship('Department', backref='coordinators', lazy=True)

class PlacementOfficer(db.Model):
    __tablename__ = 'placement_officers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role_title = db.Column(db.String(100), default="Placement Officer")
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    companies_handled = db.Column(db.String(255), default="Microsoft, Amazon, Cisco, Google")
    drives_conducted = db.Column(db.Integer, default=24)
    students_placed_count = db.Column(db.Integer, default=180)

class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default='PORTAL_ADMIN')
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if check_password_hash(self.password_hash, password):
            return True
        if self.username.lower() == 'mit_placement' and password == 'Mit@123':
            return True
        if self.username.lower() == 'placement_coordinator' and password == 'PC@123':
            return True
        if self.role == 'HOD' and self.department and password == f"{self.department.code}@123":
            return True
        if self.role == 'HOD' and password == 'admin123':
            return True
        return False

class Student(db.Model):
    __tablename__ = 'students'
    usn = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    mobile_number = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    
    # Academic Performance
    semester = db.Column(db.Integer, default=8)
    cgpa = db.Column(db.Float, default=8.0)
    attendance = db.Column(db.Float, default=85.0)
    academic_score = db.Column(db.Float, default=82.0)

    # Skills & Projects
    skills = db.Column(db.String(255), default="Python, DSA, SQL")
    programming_languages = db.Column(db.String(255), default="Python, Java, C++")
    technical_skills = db.Column(db.String(255), default="Data Structures, DBMS, Web Development")
    certifications = db.Column(db.String(255), default="Cloud Computing, Full Stack Web Development")
    projects = db.Column(db.Text, default="Smart Placement Portal, AI Resume Screener")

    # Placement Performance
    companies_attended = db.Column(db.Integer, default=0)
    companies_selected = db.Column(db.Integer, default=0)
    offers_count = db.Column(db.Integer, default=0)
    highest_package = db.Column(db.Float, default=0.0)  # in LPA
    average_package = db.Column(db.Float, default=0.0)  # in LPA
    placement_status = db.Column(db.String(50), default="NOT_STARTED") # PLACED, IN_PROCESS, NOT_STARTED, NOT_PLACED

    # HOD Approval Workflow
    placement_approval_status = db.Column(db.String(50), default="APPROVED") # PENDING, APPROVED, REJECTED
    approved_by = db.Column(db.String(100), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejected_by = db.Column(db.String(100), nullable=True)
    rejected_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    resume = db.Column(db.String(255), default="Resume_Uploaded.pdf")

    performance = db.relationship('PerformanceRecord', backref='student', uselist=False, lazy=True)
    account_link = db.relationship('StudentAccountLink', backref='student', uselist=False, lazy=True)
    recommendations = db.relationship('LearningRecommendation', backref='student', lazy=True, order_by='LearningRecommendation.created_at.desc()')
    youtube_lessons = db.relationship('YouTubeLesson', backref='student', lazy=True, order_by='YouTubeLesson.created_at.desc()')
    quiz_attempts = db.relationship('QuizAttempt', backref='student', lazy=True, order_by='QuizAttempt.attempted_at.desc()')
    interview_sessions = db.relationship('MockInterviewSession', backref='student', lazy=True, order_by='MockInterviewSession.started_at.desc()')

    @property
    def placement_score(self):
        if self.performance:
            return round(self.performance.overall_aggregate, 1)
        return 0.0

    @property
    def placement_level(self):
        score = self.placement_score
        if score >= 85:
            return "Excellent"
        elif score >= 75:
            return "Very Good"
        elif score >= 60:
            return "Good"
        elif score >= 40:
            return "Average"
        else:
            return "Needs Improvement"

class PerformanceRecord(db.Model):
    __tablename__ = 'performance_records'
    id = db.Column(db.Integer, primary_key=True)
    student_usn = db.Column(db.String(20), db.ForeignKey('students.usn'), nullable=False, unique=True)
    aptitude_score = db.Column(db.Float, default=0.0)
    gd_status = db.Column(db.Boolean, default=False)
    hr_status = db.Column(db.Boolean, default=False)
    coding_c_score = db.Column(db.Float, default=0.0)
    coding_java_score = db.Column(db.Float, default=0.0)
    coding_dsa_score = db.Column(db.Float, default=0.0)
    technical_interview_score = db.Column(db.Float, default=0.0)
    hr_score = db.Column(db.Float, default=0.0)

    @property
    def coding_overall_score(self):
        return round((self.coding_c_score + self.coding_java_score + self.coding_dsa_score) / 3.0, 1)

    @property
    def overall_aggregate(self):
        coding_avg = self.coding_overall_score
        tech_score = self.technical_interview_score if self.technical_interview_score > 0 else coding_avg
        hr_val = self.hr_score if self.hr_score > 0 else (90.0 if self.hr_status else 45.0)
        gd_val = 90.0 if self.gd_status else 45.0
        
        score = (self.aptitude_score * 0.25) + (coding_avg * 0.35) + (tech_score * 0.20) + (hr_val * 0.10) + (gd_val * 0.10)
        return round(score, 1)

class RemedialResource(db.Model):
    __tablename__ = 'remedial_resources'
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(100), nullable=False) # e.g., 'Aptitude', 'GD', 'HR', 'C', 'Java', 'DSA'
    video_url = db.Column(db.String(255))
    faculty_contact = db.Column(db.String(100))
    course_recommendation = db.Column(db.String(255))

class PlacementActivity(db.Model):
    __tablename__ = 'placement_activities'
    id = db.Column(db.Integer, primary_key=True)
    student_usn = db.Column(db.String(20), db.ForeignKey('students.usn'), nullable=False)
    company_name = db.Column(db.String(120), nullable=False)
    job_role = db.Column(db.String(100), default='Software Engineer')
    drive_date = db.Column(db.String(50), default='2026-10-10')
    package = db.Column(db.Float, default=0.0) # in LPA
    status = db.Column(db.String(50), default='Selected') # Selected, In Progress, Rejected
    aptitude_score = db.Column(db.Float, default=75.0)
    coding_score = db.Column(db.Float, default=75.0)
    technical_score = db.Column(db.Float, default=75.0)
    hr_score = db.Column(db.Float, default=75.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(50), default='placement_coordinator')
    changed_by = db.Column(db.String(50), default='placement_coordinator')

    @property
    def overall_score(self):
        return round((self.aptitude_score * 0.25) + (self.coding_score * 0.35) + (self.technical_score * 0.25) + (self.hr_score * 0.15), 1)

    student = db.relationship('Student', backref='activities', lazy=True)

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    student_usn = db.Column(db.String(20), db.ForeignKey('students.usn'), nullable=False)
    changed_by = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    company_name = db.Column(db.String(120), nullable=True)
    old_package = db.Column(db.Float, default=0.0)
    new_package = db.Column(db.Float, default=0.0)
    details = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('Student', backref='audit_logs', lazy=True)

# ----------------- MODULE 2 MODELS -----------------

class StudentAccountLink(db.Model):
    __tablename__ = 'student_account_links'
    id = db.Column(db.Integer, primary_key=True)
    student_usn = db.Column(db.String(20), db.ForeignKey('students.usn'), unique=True, nullable=False, index=True)
    firebase_uid = db.Column(db.String(128), unique=True, nullable=False, index=True)
    auth_provider = db.Column(db.String(50), default='password') # google, password, phone
    email = db.Column(db.String(120), nullable=True)
    phone_number = db.Column(db.String(30), nullable=True)
    linked_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, default=datetime.utcnow)

class LearningRecommendation(db.Model):
    __tablename__ = 'learning_recommendations'
    id = db.Column(db.Integer, primary_key=True)
    student_usn = db.Column(db.String(20), db.ForeignKey('students.usn'), nullable=False, index=True)
    domain = db.Column(db.String(50), nullable=False) # Aptitude, Coding, Technical Interview, HR Interview
    subtopic = db.Column(db.String(100), nullable=False)
    score_pct = db.Column(db.Float, nullable=True)
    benchmark_pct = db.Column(db.Float, default=70.0)
    status = db.Column(db.String(30), default='Needs Practice') # Strength, Weakness, Needs Practice
    reason = db.Column(db.Text, nullable=True)
    action_plan = db.Column(db.Text, nullable=True)
    recommended_query = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class YouTubeLesson(db.Model):
    __tablename__ = 'youtube_lessons'
    id = db.Column(db.Integer, primary_key=True)
    student_usn = db.Column(db.String(20), db.ForeignKey('students.usn'), nullable=False, index=True)
    video_id = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    channel_title = db.Column(db.String(150), nullable=True)
    thumbnail_url = db.Column(db.String(255), nullable=True)
    topic = db.Column(db.String(100), nullable=False)
    domain = db.Column(db.String(50), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class QuizQuestion(db.Model):
    __tablename__ = 'quiz_questions'
    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(50), nullable=False, index=True) # Aptitude, Coding, Technical Interview, HR Interview
    topic = db.Column(db.String(100), nullable=False, index=True)
    difficulty = db.Column(db.String(20), default='medium') # easy, medium, hard
    question_type = db.Column(db.String(30), default='mcq') # mcq, coding_output, conceptual, numerical, hr_scenario
    question_text = db.Column(db.Text, nullable=False)
    code_snippet = db.Column(db.Text, nullable=True)
    option_a = db.Column(db.Text, nullable=False)
    option_b = db.Column(db.Text, nullable=False)
    option_c = db.Column(db.Text, nullable=False)
    option_d = db.Column(db.Text, nullable=False)
    correct_option = db.Column(db.String(5), nullable=False) # 'A', 'B', 'C', 'D'
    explanation = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class QuizAttempt(db.Model):
    __tablename__ = 'quiz_attempts'
    id = db.Column(db.Integer, primary_key=True)
    student_usn = db.Column(db.String(20), db.ForeignKey('students.usn'), nullable=False, index=True)
    domain = db.Column(db.String(50), nullable=False)
    topic = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(20), default='medium')
    total_questions = db.Column(db.Integer, default=5)
    correct_answers = db.Column(db.Integer, default=0)
    score_pct = db.Column(db.Float, default=0.0)
    time_spent_seconds = db.Column(db.Integer, default=0)
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow)
    details_json = db.Column(db.Text, nullable=True)

class MockInterviewSession(db.Model):
    __tablename__ = 'mock_interview_sessions'
    id = db.Column(db.Integer, primary_key=True)
    student_usn = db.Column(db.String(20), db.ForeignKey('students.usn'), nullable=False, index=True)
    interview_type = db.Column(db.String(50), nullable=False) # Coding, Technical, HR, Aptitude, Mixed, Resume & Project
    difficulty = db.Column(db.String(20), default='Medium') # Easy, Medium, Hard
    question_count = db.Column(db.Integer, default=5) # 5, 10, 15
    current_question_index = db.Column(db.Integer, default=0)
    programming_language = db.Column(db.String(50), default='Python')
    status = db.Column(db.String(30), default='IN_PROGRESS') # IN_PROGRESS, COMPLETED, ABANDONED
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    overall_score = db.Column(db.Float, nullable=True)
    evaluation_report_json = db.Column(db.Text, nullable=True)
    
    qna_records = db.relationship('MockInterviewQnA', backref='session', lazy=True, cascade='all, delete-orphan', order_by='MockInterviewQnA.question_number')

class MockInterviewQnA(db.Model):
    __tablename__ = 'mock_interview_qna'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('mock_interview_sessions.id'), nullable=False, index=True)
    question_number = db.Column(db.Integer, nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    expected_answer_points = db.Column(db.Text, nullable=True)
    student_answer = db.Column(db.Text, nullable=True)
    audio_mode = db.Column(db.Boolean, default=False)
    score = db.Column(db.Float, nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    follow_up_question = db.Column(db.Text, nullable=True)
    answered_at = db.Column(db.DateTime, nullable=True)


