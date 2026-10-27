from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
import hmac

def parse_dob_string(dob_str):
    if not dob_str:
        return None
    if isinstance(dob_str, (date, datetime)):
        return dob_str.date() if isinstance(dob_str, datetime) else dob_str
    dob_str = str(dob_str).strip()
    formats = ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d', '%d.%m.%Y', '%Y.%m.%d', '%Y%m%d', '%d%m%Y']
    for fmt in formats:
        try:
            return datetime.strptime(dob_str, fmt).date()
        except (ValueError, TypeError):
            continue
    return None

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
    recovery_email = db.Column(db.String(100), nullable=True)
    recovery_mobile = db.Column(db.String(30), nullable=True)
    is_recovery_email_verified = db.Column(db.Boolean, default=False)
    is_recovery_mobile_verified = db.Column(db.Boolean, default=False)
    password_changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)
    failed_login_count = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    session_version = db.Column(db.Integer, default=1)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.password_changed_at = datetime.utcnow()
        self.session_version = (self.session_version or 0) + 1

    def check_password(self, password):
        if not self.password_hash or not password:
            return False
        return check_password_hash(self.password_hash, password)

class Student(db.Model):
    __tablename__ = 'students'
    usn = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    mobile_number = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    session_version = db.Column(db.Integer, default=1)

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
    course_progress = db.relationship('StudentCourseProgress', backref='student', lazy=True, cascade='all, delete-orphan', order_by='StudentCourseProgress.saved_at.desc()')
    event_actions = db.relationship('StudentEventAction', backref='student', lazy=True, cascade='all, delete-orphan', order_by='StudentEventAction.updated_at.desc()')
    achievements = db.relationship('StudentAchievement', backref='student', lazy=True, cascade='all, delete-orphan', order_by='StudentAchievement.completion_date.desc()')
    notifications = db.relationship('StudentNotification', backref='student', lazy=True, cascade='all, delete-orphan', order_by='StudentNotification.created_at.desc()')
    preference = db.relationship('StudentPreference', backref='student', uselist=False, lazy=True, cascade='all, delete-orphan')
    provider_accounts = db.relationship('ExternalProviderAccount', backref='student', lazy=True, cascade='all, delete-orphan', order_by='ExternalProviderAccount.created_at.desc()')
    sync_logs = db.relationship('CertificateSyncLog', backref='student', lazy=True, cascade='all, delete-orphan', order_by='CertificateSyncLog.sync_started_at.desc()')

    # Date of Birth & Credentials
    date_of_birth = db.Column(db.Date, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    first_login_at = db.Column(db.DateTime, nullable=True)
    dob_login_count = db.Column(db.Integer, default=0)
    failed_login_count = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.session_version = (self.session_version or 0) + 1

    def check_password(self, password):
        if not self.password_hash or not password:
            return False
        return check_password_hash(self.password_hash, password)

    def verify_dob(self, input_val):
        if not self.date_of_birth or not input_val:
            return False
        if isinstance(input_val, (datetime, date)):
            input_date = input_val.date() if isinstance(input_val, datetime) else input_val
        else:
            input_date = parse_dob_string(str(input_val))
        if not input_date:
            return False
        return hmac.compare_digest(self.date_of_birth.strftime('%Y-%m-%d'), input_date.strftime('%Y-%m-%d'))

    def is_locked(self):
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False

    def record_failed_attempt(self, max_attempts=5, lockout_minutes=15):
        self.failed_login_count = (self.failed_login_count or 0) + 1
        if self.failed_login_count >= max_attempts:
            self.locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)
        db.session.commit()

    def reset_failed_attempts(self):
        self.failed_login_count = 0
        self.locked_until = None
        db.session.commit()

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

# ----------------- MODULE 3: ACHIEVEMENT & WORKSHOP HUB MODELS -----------------

class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    provider = db.Column(db.String(100), default='Coursera', index=True)
    domain = db.Column(db.String(100), nullable=False, index=True)
    target_branches = db.Column(db.String(100), default='ALL') # 'IS,CS', 'EC', 'ME', 'ALL'
    difficulty = db.Column(db.String(50), default='Intermediate')
    skills_covered = db.Column(db.String(255), default='')
    duration = db.Column(db.String(50), default='4-6 Weeks')
    course_url = db.Column(db.String(500), nullable=False)
    thumbnail_url = db.Column(db.String(500), nullable=True)
    is_free = db.Column(db.Boolean, default=True, index=True)
    free_certificate = db.Column(db.Boolean, default=False, index=True)
    cost_info = db.Column(db.String(100), default='Free to Audit')
    certificate_info = db.Column(db.String(255), default='Shareable Certificate upon completion')
    rating = db.Column(db.Float, default=4.8)
    last_verified_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student_progress = db.relationship('StudentCourseProgress', backref='course', lazy=True, cascade='all, delete-orphan')

class StudentCourseProgress(db.Model):
    __tablename__ = 'student_course_progress'
    id = db.Column(db.Integer, primary_key=True)
    student_usn = db.Column(db.String(20), db.ForeignKey('students.usn'), nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False, index=True)
    status = db.Column(db.String(30), default='BOOKMARKED', index=True) # BOOKMARKED, ENROLLED, IN_PROGRESS, COMPLETED
    progress_pct = db.Column(db.Float, default=0.0)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)
    enrolled_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (db.UniqueConstraint('student_usn', 'course_id', name='uq_student_course'),)

class WorkshopEvent(db.Model):
    __tablename__ = 'workshop_events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    organizer = db.Column(db.String(150), nullable=False)
    domain = db.Column(db.String(100), nullable=False, index=True)
    target_branches = db.Column(db.String(100), default='ALL') # 'IS,CS', 'EC', 'ME', 'ALL'
    event_type = db.Column(db.String(50), default='Workshop') # Workshop, Hackathon, Technical Fest, Bootcamp
    city = db.Column(db.String(50), default='Bengaluru', index=True) # Bengaluru, Mysuru, Mangaluru, Hubballi, Belagavi, Online
    venue_mode = db.Column(db.String(50), default='In-Person') # In-Person, Online, Hybrid
    venue_details = db.Column(db.String(255), default='Campus Center')
    event_date = db.Column(db.DateTime, nullable=False)
    registration_deadline = db.Column(db.DateTime, nullable=False)
    is_free = db.Column(db.Boolean, default=True, index=True)
    registration_fee = db.Column(db.String(50), default='Free of Cost')
    certificate_available = db.Column(db.Boolean, default=True)
    certificate_conditions = db.Column(db.String(255), default='Certificate awarded upon completion')
    official_registration_url = db.Column(db.String(500), nullable=False)
    source_url = db.Column(db.String(500), nullable=True)
    is_verified = db.Column(db.Boolean, default=True)
    last_verified_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student_actions = db.relationship('StudentEventAction', backref='event', lazy=True, cascade='all, delete-orphan')

class StudentEventAction(db.Model):
    __tablename__ = 'student_event_actions'
    id = db.Column(db.Integer, primary_key=True)
    student_usn = db.Column(db.String(20), db.ForeignKey('students.usn'), nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('workshop_events.id'), nullable=False, index=True)
    status = db.Column(db.String(30), default='SAVED', index=True) # SAVED, REGISTRATION_OPENED, APPLIED, ATTENDED
    reminder_set = db.Column(db.Boolean, default=False)
    notes = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('student_usn', 'event_id', name='uq_student_event'),)

class StudentAchievement(db.Model):
    __tablename__ = 'student_achievements'
    id = db.Column(db.Integer, primary_key=True)
    student_usn = db.Column(db.String(20), db.ForeignKey('students.usn'), nullable=False, index=True)
    category = db.Column(db.String(50), default='COURSE') # COURSE, CERTIFICATE, WORKSHOP, HACKATHON, INTERNSHIP, COMPETITION, PROJECT, TRAINING
    achievement_type = db.Column(db.String(50), default='COURSE') # Normalized: COURSE, WORKSHOP, HACKATHON, INTERNSHIP, COMPETITION
    title = db.Column(db.String(255), nullable=False)
    provider_or_organizer = db.Column(db.String(150), nullable=False)
    domain = db.Column(db.String(100), nullable=False)
    completion_date = db.Column(db.DateTime, nullable=False)
    certificate_url = db.Column(db.String(500), nullable=True)
    evidence_file = db.Column(db.String(255), nullable=True)
    skills_acquired = db.Column(db.String(255), nullable=True)
    verification_status = db.Column(db.String(30), default='PENDING_VERIFICATION', index=True) # PENDING_VERIFICATION, VERIFIED, REJECTED
    verification_method = db.Column(db.String(50), default='MANUAL_SUBMISSION') # OAUTH_SYNC, ORGANIZER_VERIFIED, MANUAL_SUBMISSION, ADMIN_VERIFIED
    verified_by = db.Column(db.String(100), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    verification_notes = db.Column(db.String(255), nullable=True)
    external_certificate_id = db.Column(db.String(100), nullable=True, index=True)
    is_coursera_sync = db.Column(db.Boolean, default=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('student_usn', 'provider_or_organizer', 'external_certificate_id', name='uq_student_provider_cert'),
    )

class StudentNotification(db.Model):
    __tablename__ = 'student_notifications'
    id = db.Column(db.Integer, primary_key=True)
    student_usn = db.Column(db.String(20), db.ForeignKey('students.usn'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='WORKSHOP') # WORKSHOP, DEADLINE, COURSE, ACHIEVEMENT, RECOMMENDATION
    action_url = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False, index=True)
    is_dismissed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class StudentPreference(db.Model):
    __tablename__ = 'student_preferences'
    id = db.Column(db.Integer, primary_key=True)
    student_usn = db.Column(db.String(20), db.ForeignKey('students.usn'), unique=True, nullable=False, index=True)
    interested_domains = db.Column(db.String(255), default='DSA, Python, AI/ML')
    career_goal = db.Column(db.String(150), default='Software Development Engineer')
    notify_workshops = db.Column(db.Boolean, default=True)
    notify_deadlines = db.Column(db.Boolean, default=True)
    notify_free_courses = db.Column(db.Boolean, default=True)
    coursera_email = db.Column(db.String(120), nullable=True)
    coursera_connected = db.Column(db.Boolean, default=False)
    coursera_connected_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class ExternalProviderAccount(db.Model):
    __tablename__ = 'external_provider_accounts'
    id = db.Column(db.Integer, primary_key=True)
    student_usn = db.Column(db.String(20), db.ForeignKey('students.usn'), nullable=False, index=True)
    provider_name = db.Column(db.String(50), default='Coursera', nullable=False, index=True) # Coursera, NPTEL, edX, etc.
    external_account_id = db.Column(db.String(150), nullable=True) # e.g. Coursera user ID or sub
    external_email = db.Column(db.String(150), nullable=True)
    access_token = db.Column(db.Text, nullable=True) # Encrypted or protected
    refresh_token = db.Column(db.Text, nullable=True)
    token_expires_at = db.Column(db.DateTime, nullable=True)
    connection_status = db.Column(db.String(30), default='CONNECTED', index=True) # CONNECTED, DISCONNECTED, EXPIRED, CONFIG_REQUIRED
    last_synced_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('student_usn', 'provider_name', name='uq_student_provider_account'),)

class CertificateSyncLog(db.Model):
    __tablename__ = 'certificate_sync_logs'
    id = db.Column(db.Integer, primary_key=True)
    student_usn = db.Column(db.String(20), db.ForeignKey('students.usn'), nullable=False, index=True)
    provider_name = db.Column(db.String(50), default='Coursera', nullable=False)
    sync_started_at = db.Column(db.DateTime, default=datetime.utcnow)
    sync_completed_at = db.Column(db.DateTime, nullable=True)
    sync_status = db.Column(db.String(30), default='SUCCESS')
    certificates_found = db.Column(db.Integer, default=0)
    certificates_synced = db.Column(db.Integer, default=0)
    error_category = db.Column(db.String(50), nullable=True)
    error_message = db.Column(db.Text, nullable=True)

# ----------------- SECURITY & AUTHENTICATION MODELS -----------------

class StudentOtpVerification(db.Model):
    __tablename__ = 'student_otp_verifications'
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(100), nullable=False, index=True) # Normalized mobile number or email
    student_usn = db.Column(db.String(20), db.ForeignKey('students.usn'), nullable=True, index=True)
    otp_hash = db.Column(db.String(255), nullable=False) # Salted hash of OTP, never raw plaintext
    purpose = db.Column(db.String(50), default='STUDENT_LOGIN') # STUDENT_LOGIN, ADMIN_RECOVERY
    attempts = db.Column(db.Integer, default=0)
    max_attempts = db.Column(db.Integer, default=3)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    used_at = db.Column(db.DateTime, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('Student', backref='otp_verifications', lazy=True)

class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False, index=True)
    token_hash = db.Column(db.String(255), nullable=False, index=True)
    method = db.Column(db.String(30), default='EMAIL') # EMAIL, MOBILE_OTP, BOOTSTRAP
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    admin = db.relationship('Admin', backref='reset_tokens', lazy=True)

class SecurityAuditLog(db.Model):
    __tablename__ = 'security_audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.String(30), nullable=False) # ADMIN, COORDINATOR, HOD, STUDENT, SYSTEM
    user_identifier = db.Column(db.String(100), nullable=False) # username or usn
    event_type = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(30), default='SUCCESS') # SUCCESS, FAILED, BLOCKED
    ip_address = db.Column(db.String(50), nullable=True)
    details = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
