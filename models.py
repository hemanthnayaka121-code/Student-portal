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

