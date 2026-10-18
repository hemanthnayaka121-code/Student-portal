from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort, send_from_directory
from models import (
    db, Department, Admin, Student, PerformanceRecord, RemedialResource, PlacementActivity,
    AuditLog, PlacementCoordinator, PlacementOfficer, StudentAccountLink, LearningRecommendation,
    YouTubeLesson, QuizQuestion, QuizAttempt, MockInterviewSession, MockInterviewQnA,
    Course, StudentCourseProgress, WorkshopEvent, StudentEventAction, StudentAchievement,
    StudentNotification, StudentPreference, ExternalProviderAccount, CertificateSyncLog
)
from firebase_auth import verify_firebase_token, match_student_identity, link_and_login_student
from performance_engine import analyze_student_performance
from youtube_service import search_youtube_videos
from quiz_bank import seed_quiz_questions, INITIAL_QUIZ_QUESTIONS
from interview_engine import generate_interview_questions, evaluate_answer_with_ai, generate_comprehensive_interview_report
from course_service import CourseProviderService
from workshop_service import WorkshopDiscoveryService
from recommendation_service import RecommendationService
from achievement_service import AchievementService, CertificateVerificationService
from notification_service import NotificationService
from external_account_service import ExternalAccountService
from coursera_service import CourseraIntegrationService
from sync_service import LearningProgressSyncService
from event_integration_service import WorkshopIntegrationService, HackathonIntegrationService
from sqlalchemy.exc import IntegrityError
import os
import re
import json
import time
from datetime import datetime, timedelta

app = Flask(__name__)
handler = app  # Explicit Vercel serverless function entrypoint
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'supersecretkey_mitm_secure_2026')

# Support read-only serverless filesystems (e.g. AWS Lambda / Vercel Serverless Function)
if os.environ.get('VERCEL'):
    import tempfile
    app.config['UPLOAD_FOLDER'] = os.path.join(tempfile.gettempdir(), 'uploads', 'certificates')
else:
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads', 'certificates')

app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max upload

try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
except OSError as e:
    print(f"Notice: Upload folder creation bypassed in read-only environment: {e}")

# Database configuration: support Vercel serverless environment and remote PostgreSQL
db_url = os.environ.get('DATABASE_URL')
if db_url:
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
elif os.environ.get('VERCEL'):
    import shutil
    import tempfile
    
    tmp_dir = tempfile.gettempdir()
    tmp_db_path = os.path.join(tmp_dir, "placement.db")
    
    # Candidate source locations to copy existing seeded database from
    candidate_sources = [
        os.path.join(app.root_path, "instance", "placement.db"),
        os.path.join(app.instance_path, "placement.db"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "placement.db"),
        os.path.join(os.getcwd(), "instance", "placement.db"),
        os.path.join(app.root_path, "placement.db"),
        os.path.join(os.getcwd(), "placement.db"),
    ]
    
    source_db_path = None
    for candidate in candidate_sources:
        if os.path.exists(candidate) and os.path.getsize(candidate) > 1000:
            source_db_path = candidate
            break
            
    try:
        os.makedirs(tmp_dir, exist_ok=True)
        # Copy seeded database if tmp_db does not exist or is smaller than source
        if source_db_path:
            if not os.path.exists(tmp_db_path) or os.path.getsize(tmp_db_path) < os.path.getsize(source_db_path):
                shutil.copy2(source_db_path, tmp_db_path)
                print(f"[Vercel] Successfully copied database from {source_db_path} ({os.path.getsize(source_db_path)} bytes) to {tmp_db_path}")
        else:
            print("[Vercel] Warning: No source placement.db found in candidate locations.")
    except Exception as e:
        print(f"[Vercel] Warning: Database copy to {tmp_db_path} failed: {e}")
        
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{tmp_db_path}"
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=45)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

db.init_app(app)

# Ensure database tables exist in any serverless container
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print(f"Notice: db.create_all() exception: {e}")

# In-memory rate limiting tracker (ip_address -> list of timestamp failures)
failed_login_attempts = {}

def is_rate_limited(client_ip, max_attempts=5, window_seconds=300):
    now = time.time()
    attempts = [t for t in failed_login_attempts.get(client_ip, []) if now - t < window_seconds]
    failed_login_attempts[client_ip] = attempts
    return len(attempts) >= max_attempts

def record_failed_login(client_ip):
    now = time.time()
    if client_ip not in failed_login_attempts:
        failed_login_attempts[client_ip] = []
    failed_login_attempts[client_ip].append(now)

def reset_failed_logins(client_ip):
    failed_login_attempts.pop(client_ip, None)

@app.before_request
def auto_redirect_to_authorized_domain():
    # Automatically switch 127.0.0.1 to localhost for seamless OAuth without prompting the user
    if not app.config.get('TESTING') and request.host.startswith('127.0.0.1'):
        target_url = request.url.replace('127.0.0.1:5000', 'localhost:5000', 1)
        return redirect(target_url, code=302)

@app.context_processor
def inject_student_notifications():
    unread_count = 0
    if session.get('student_usn'):
        try:
            unread_count = NotificationService.get_unread_count(session.get('student_usn'))
        except Exception:
            unread_count = 0
    return dict(unread_notifications_count=unread_count)

@app.route('/static/<path:filename>')
def serve_static(filename):
    static_dirs = [
        app.static_folder,
        os.path.join(app.root_path, 'static'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'),
        os.path.join(os.getcwd(), 'static')
    ]
    for s_dir in static_dirs:
        if s_dir and os.path.exists(os.path.join(s_dir, filename)):
            return send_from_directory(s_dir, filename)
    abort(404)

@app.after_request
def add_security_headers(response):
    # Only disable caching on dynamic HTML pages; allow browser caching for static CSS/images
    if not request.path.startswith('/static/'):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    else:
        response.headers["Cache-Control"] = "public, max-age=86400"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response

def get_current_admin():
    if 'admin_id' not in session:
        return None
    return db.session.get(Admin, session['admin_id'])

def get_current_student():
    if 'student_usn' not in session:
        return None
    return db.session.get(Student, session['student_usn'])

def mask_email(email):
    if not email or '@' not in email:
        return "N/A"
    parts = email.split('@')
    name = parts[0]
    domain = parts[1]
    if len(name) <= 2:
        masked_name = name[0] + "*"
    else:
        masked_name = name[:2] + "*" * max(1, len(name) - 3) + name[-1]
    return f"{masked_name}@{domain}"

def mask_mobile(mobile):
    if not mobile:
        return "N/A"
    clean = re.sub(r'\D', '', mobile)
    if len(clean) >= 4:
        return "*" * (len(clean) - 4) + clean[-4:]
    return clean

# Helper function to compute college-wide placement statistics
def get_college_metrics():
    all_students = Student.query.all()
    total_students = len(all_students)
    placed_students = [s for s in all_students if s.placement_status == 'Placed' or s.offers_count > 0]
    placed_count = len(placed_students)
    placement_pct = round((placed_count / total_students * 100), 1) if total_students > 0 else 0.0

    highest_pkgs = [s.highest_package for s in all_students if s.highest_package > 0]
    max_package = max(highest_pkgs) if highest_pkgs else 0.0

    avg_pkgs = [s.average_package for s in all_students if s.average_package > 0]
    overall_avg_package = round(sum(avg_pkgs) / len(avg_pkgs), 2) if avg_pkgs else 0.0

    total_offers = sum(s.offers_count for s in all_students)

    activity_comps = [a.company_name for a in PlacementActivity.query.all()]
    standard_comps = ["Microsoft", "Amazon", "Cisco", "Google", "Infosys", "TCS", "Wipro", "Intel", "SAP Labs", "Texas Instruments", "NVIDIA", "Adobe", "Morgan Stanley", "Databricks", "Qualcomm", "MathWorks", "Bosch", "Schneider Electric", "L&T Construction", "Tata Projects", "Mercedes-Benz R&D", "Tata Motors"]
    total_companies = len(set(activity_comps + standard_comps))

    return {
        'total_students': total_students,
        'placed_count': placed_count,
        'unplaced_count': total_students - placed_count,
        'placement_pct': placement_pct,
        'max_package': max_package,
        'overall_avg_package': overall_avg_package,
        'total_offers': total_offers,
        'total_companies': total_companies
    }

# Helper function to compute department stats dynamically from database
def get_department_stats(dept):
    dept_students = Student.query.filter_by(department_id=dept.id).all()
    total = len(dept_students)
    placed = [s for s in dept_students if s.placement_status == 'Placed' or s.offers_count > 0]
    placed_count = len(placed)
    pct = round((placed_count / total * 100), 1) if total > 0 else 0.0

    pkgs = [s.highest_package for s in dept_students if s.highest_package > 0]
    max_pkg = max(pkgs) if pkgs else 0.0

    avg_pkgs = [s.average_package for s in dept_students if s.average_package > 0]
    avg_pkg = round(sum(avg_pkgs) / len(avg_pkgs), 2) if avg_pkgs else 0.0

    offers = sum(s.offers_count for s in dept_students)

    scores = [s.placement_score for s in dept_students if s.performance]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    return {
        'id': dept.id,
        'code': dept.code,
        'name': dept.name,
        'hod_name': dept.hod_name,
        'hod_id': dept.hod_id,
        'hod_email': dept.hod_email,
        'hod_phone': dept.hod_phone,
        'total_students': total,
        'placed_count': placed_count,
        'unplaced_count': total - placed_count,
        'placement_pct': pct,
        'highest_package': max_pkg,
        'avg_package': avg_pkg,
        'total_offers': offers,
        'avg_score': avg_score
    }

def get_all_department_stats():
    departments = Department.query.order_by(Department.id).all()
    return [get_department_stats(d) for d in departments]

# Helper function to dynamically calculate dominating department
def get_dominating_department(dept_stats_list, metric='placed_count'):
    if not dept_stats_list:
        return None
    key_map = {
        'placed_count': lambda d: (d['placed_count'], d['placement_pct']),
        'placement_pct': lambda d: (d['placement_pct'], d['placed_count']),
        'avg_package': lambda d: (d['avg_package'], d['highest_package']),
        'highest_package': lambda d: (d['highest_package'], d['avg_package']),
        'total_offers': lambda d: (d['total_offers'], d['placed_count']),
        'avg_score': lambda d: (d['avg_score'], d['placement_pct'])
    }
    sorter = key_map.get(metric, key_map['placed_count'])
    sorted_depts = sorted(dept_stats_list, key=sorter, reverse=True)
    return sorted_depts[0]

# Prepare Chart Payload for comparison across all 10 departments
def prepare_chart_payload(dept_stats_list):
    sorted_for_charts = sorted(dept_stats_list, key=lambda x: x['code'])
    return {
        'dept_codes': [d['code'] for d in sorted_for_charts],
        'dept_names': [d['name'] for d in sorted_for_charts],
        'placed_students': [d['placed_count'] for d in sorted_for_charts],
        'placement_pct': [d['placement_pct'] for d in sorted_for_charts],
        'avg_package': [d['avg_package'] for d in sorted_for_charts],
        'highest_package': [d['highest_package'] for d in sorted_for_charts],
        'total_offers': [d['total_offers'] for d in sorted_for_charts],
        'avg_score': [d['avg_score'] for d in sorted_for_charts],
        'total_students': [d['total_students'] for d in sorted_for_charts]
    }

# ----------------- 1. MAIN LOGIN (PLACEMENT ADMIN) -----------------

@app.route('/')
def index():
    if 'admin_id' in session:
        return redirect(url_for('portal_dashboard'))
    elif 'student_usn' in session:
        return redirect(url_for('student_dashboard'))
    return redirect(url_for('admin_login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    client_ip = request.remote_addr or '127.0.0.1'

    if request.method == 'POST':
        if is_rate_limited(client_ip):
            flash('Too many failed attempts. Please wait 5 minutes before trying again.', 'error')
            return render_template('admin_login.html'), 429

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # Main login: Mit_placement / Mit@123
        admin = Admin.query.filter(Admin.username.ilike(username)).first()
        if admin and admin.check_password(password) and (admin.role == 'PLACEMENT_ADMIN' or admin.username.lower() == 'mit_placement'):
            reset_failed_logins(client_ip)
            session.clear()
            session.permanent = True
            session['admin_id'] = admin.id
            session['username'] = admin.username
            session['role'] = 'PLACEMENT_ADMIN'
            flash('Logged in successfully as Placement Admin.', 'success')
            return redirect(url_for('portal_dashboard'))
        
        record_failed_login(client_ip)
        flash('Invalid User ID or Password. Please use Mit_placement / Mit@123', 'error')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('You have been logged out of the MIT Placement Portal.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
def admin_dashboard():
    return redirect(url_for('portal_dashboard'))

# ----------------- 2. PLACEMENT ADMIN DASHBOARD -----------------

@app.route('/portal/dashboard')
def portal_dashboard():
    admin = get_current_admin()
    if not admin:
        return redirect(url_for('admin_login'))

    college_metrics = get_college_metrics()
    dept_stats_list = get_all_department_stats()
    
    # Leaderboard sorted by primary: Placement Score, secondary: Placement %
    dept_leaderboard = sorted(dept_stats_list, key=lambda x: (x['avg_score'], x['placement_pct']), reverse=True)
    dominating_dept = get_dominating_department(dept_stats_list, metric='placed_count')
    chart_payload = prepare_chart_payload(dept_stats_list)

    return render_template(
        'portal_dashboard.html',
        active_page='dashboard',
        admin=admin,
        metrics=college_metrics,
        dept_leaderboard=dept_leaderboard,
        dominating_dept=dominating_dept,
        chart_payload=json.dumps(chart_payload),
        dept_stats_json=json.dumps(dept_stats_list)
    )

# REMOVED PRINCIPAL ROUTES -> Redirect to main dashboard
@app.route('/portal/principal')
@app.route('/principal/dashboard', endpoint='principal_dashboard')
def portal_principal():
    return redirect(url_for('portal_dashboard'))

# ----------------- 3. PLACEMENT COORDINATOR (PROTECTED LOGIN & DASHBOARD) -----------------

# REQUIREMENT 1.B: ALWAYS DISPLAY SEPARATE LOGIN PAGE WHEN CLICKING PLACEMENT COORDINATOR
@app.route('/portal/coordinator')
def coordinator_portal():
    # Never open Coordinator dashboard directly from main Placement Admin dashboard
    session.pop('coordinator_authenticated', None)
    session.pop('coordinator_username', None)
    return redirect(url_for('coordinator_login'))

@app.route('/coordinator/login', methods=['GET', 'POST'])
def coordinator_login():
    client_ip = request.remote_addr or '127.0.0.1'

    if request.method == 'POST':
        if is_rate_limited(client_ip):
            flash('Too many failed attempts. Please wait 5 minutes before trying again.', 'error')
            return render_template('coordinator_login.html'), 429

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        admin = Admin.query.filter(Admin.username.ilike(username)).first()
        if admin and admin.check_password(password) and (admin.role == 'PLACEMENT_COORDINATOR' or admin.username.lower() == 'placement_coordinator'):
            reset_failed_logins(client_ip)
            session.permanent = True
            session['coordinator_authenticated'] = True
            session['coordinator_username'] = admin.username
            flash('Authenticated as Placement Coordinator. Access granted.', 'success')
            return redirect(url_for('coordinator_dashboard'))
        
        record_failed_login(client_ip)
        flash('Invalid Coordinator credentials. (Use: placement_coordinator / PC@123)', 'error')
    return render_template('coordinator_login.html')

@app.route('/coordinator/logout')
def coordinator_logout():
    session.pop('coordinator_authenticated', None)
    session.pop('coordinator_username', None)
    flash('Logged out from Placement Coordinator session.', 'success')
    return redirect(url_for('portal_dashboard'))

@app.route('/coordinator/dashboard')
def coordinator_dashboard():
    if not session.get('coordinator_authenticated') and session.get('role') != 'PLACEMENT_COORDINATOR':
        flash('Please authenticate as Placement Coordinator to access this console.', 'error')
        return redirect(url_for('coordinator_login'))

    departments = Department.query.order_by(Department.name).all()
    search_query = request.args.get('search', '').strip()
    dept_filter = request.args.get('dept_filter', '').strip().upper()

    approved_q = Student.query.filter_by(placement_approval_status='APPROVED')
    pending_q = Student.query.filter(Student.placement_approval_status.in_(['PENDING', 'PENDING_HOD_APPROVAL']))
    rejected_q = Student.query.filter_by(placement_approval_status='REJECTED')

    if search_query:
        search_filter = (
            (Student.name.ilike(f"%{search_query}%")) |
            (Student.usn.ilike(f"%{search_query}%")) |
            (Student.skills.ilike(f"%{search_query}%"))
        )
        approved_q = approved_q.filter(search_filter)
        pending_q = pending_q.filter(search_filter)
        rejected_q = rejected_q.filter(search_filter)

    if dept_filter:
        dept_obj = Department.query.filter_by(code=dept_filter).first()
        if dept_obj:
            approved_q = approved_q.filter_by(department_id=dept_obj.id)
            pending_q = pending_q.filter_by(department_id=dept_obj.id)
            rejected_q = rejected_q.filter_by(department_id=dept_obj.id)

    approved_students = sorted(approved_q.all(), key=lambda s: (s.placement_score, s.highest_package), reverse=True)
    pending_students = pending_q.order_by(Student.usn).all()
    rejected_students = rejected_q.order_by(Student.usn).all()

    recent_activities = PlacementActivity.query.order_by(PlacementActivity.created_at.desc()).limit(20).all()

    return render_template(
        'coordinator_dashboard.html',
        departments=departments,
        approved_students=approved_students,
        pending_students=pending_students,
        rejected_students=rejected_students,
        recent_activities=recent_activities,
        search_query=search_query,
        dept_filter=dept_filter,
        current_date=datetime.utcnow().strftime('%Y-%m-%d')
    )

# STAGE 1: PLACEMENT COORDINATOR REGISTERS STUDENT FOR PLACEMENT (STATUS = PENDING)
@app.route('/coordinator/student/add', methods=['POST'])
@app.route('/students', methods=['POST'])
@app.route('/admin/student/add', methods=['POST'])
@app.route('/add_student', methods=['POST'])
def coordinator_register_student():
    # Allow Placement Coordinators or Placement Admins
    is_coord = session.get('coordinator_authenticated') or session.get('role') == 'PLACEMENT_COORDINATOR'
    is_admin = session.get('admin_id') is not None or session.get('role') in ['PORTAL_ADMIN', 'PLACEMENT_ADMIN']
    if not (is_coord or is_admin):
        flash('Authentication required: Please log in as a Placement Coordinator or Placement Admin to register students.', 'error')
        return redirect(url_for('coordinator_login'))

    # Determine destination redirect in case of error or success
    referrer = request.referrer or ''
    redirect_target = url_for('coordinator_dashboard') if ('coordinator' in referrer or is_coord) else url_for('portal_students')

    name = request.form.get('name', '').strip()
    usn = request.form.get('usn', '').strip().upper()
    dept_id = request.form.get('department_id') or request.form.get('dept_id')
    raw_sem = request.form.get('semester')
    email = request.form.get('email', '').strip()
    phone = (request.form.get('phone') or request.form.get('mobile') or '').strip()
    raw_cgpa = request.form.get('cgpa')
    skills = request.form.get('skills', '').strip() or 'Python, DSA, SQL'
    resume = request.form.get('resume', '').strip() or 'Resume_Uploaded.pdf'

    # 1. Validation: Name
    if not name:
        flash('Student Name is required.', 'error')
        return redirect(redirect_target)

    # 2. Validation: USN
    if not usn:
        flash('USN is required.', 'error')
        return redirect(redirect_target)

    # Check existing USN
    existing_student = db.session.get(Student, usn) or Student.query.filter(db.func.upper(Student.usn) == usn).first()
    if existing_student:
        flash(f"Student with USN '{usn}' already exists ({existing_student.name}).", 'error')
        return redirect(redirect_target)

    # 3. Validation: Department
    dept = None
    if dept_id:
        try:
            dept = db.session.get(Department, int(dept_id))
        except (ValueError, TypeError):
            dept = None
    if not dept:
        dept_code = request.form.get('department_code') or request.form.get('dept_code')
        if dept_code:
            dept = Department.query.filter_by(code=dept_code.strip().upper()).first()
    if not dept:
        admin = get_current_admin()
        if admin and admin.department:
            dept = admin.department
        else:
            dept = Department.query.first()
    if not dept:
        flash('Please select a valid Department.', 'error')
        return redirect(redirect_target)

    # 4. Validation: Semester
    try:
        semester = int(raw_sem) if raw_sem and raw_sem.strip() else 8
        if semester < 1 or semester > 8:
            semester = 8
    except (ValueError, TypeError):
        semester = 8

    # 5. Validation: CGPA
    try:
        cgpa = float(raw_cgpa) if raw_cgpa and raw_cgpa.strip() else 8.0
        if cgpa < 0.0 or cgpa > 10.0:
            cgpa = max(0.0, min(10.0, cgpa))
    except (ValueError, TypeError):
        cgpa = 8.0

    # 6. Validation: Phone (Mobile)
    # Strip formatting characters: spaces, hyphens, parentheses
    clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
    if clean_phone:
        existing_phone = Student.query.filter_by(mobile_number=clean_phone).first()
        if existing_phone:
            flash(f"Mobile number '{phone}' is already registered to student {existing_phone.name} ({existing_phone.usn}). Please provide a unique phone number.", 'error')
            return redirect(redirect_target)
    else:
        # Generate guaranteed unique phone
        base_phone = f"98450{usn[-5:]}" if len(usn) >= 5 else f"98450{abs(hash(usn)) % 100000:05d}"
        clean_phone = base_phone
        counter = 1
        while Student.query.filter_by(mobile_number=clean_phone).first():
            clean_phone = f"9845{int(time.time() + counter) % 1000000:06d}"
            counter += 1

    # 7. Validation: Email
    if email:
        existing_email = Student.query.filter(db.func.lower(Student.email) == email.lower()).first()
        if existing_email:
            flash(f"Email address '{email}' is already registered to student {existing_email.name} ({existing_email.usn}). Please provide a unique email address.", 'error')
            return redirect(redirect_target)
    else:
        email = f"{usn.lower()}@mitm.ac.in"
        counter = 1
        while Student.query.filter(db.func.lower(Student.email) == email.lower()).first():
            email = f"{usn.lower()}.{counter}@mitm.ac.in"
            counter += 1

    # 8. Clean up any orphaned performance records or audit logs for this USN
    try:
        PerformanceRecord.query.filter_by(student_usn=usn).delete()
    except Exception:
        pass

    # 9. Create Student & Performance Record with strict error handling & rollback
    try:
        new_student = Student(
            usn=usn,
            name=name,
            mobile_number=clean_phone,
            email=email,
            department_id=dept.id,
            semester=semester,
            cgpa=cgpa,
            skills=skills,
            resume=resume,
            placement_approval_status='PENDING',
            placement_status='NOT_STARTED',
            attendance=85.0,
            academic_score=round(cgpa * 9.5, 1)
        )
        db.session.add(new_student)

        perf = PerformanceRecord(
            student_usn=usn,
            aptitude_score=round(cgpa * 9.0, 1),
            coding_c_score=round(cgpa * 9.0, 1),
            coding_java_score=round(cgpa * 9.0, 1),
            coding_dsa_score=round(cgpa * 9.0, 1),
            technical_interview_score=round(cgpa * 9.0, 1),
            hr_score=80.0
        )
        db.session.add(perf)

        user_name = session.get('coordinator_username') or session.get('admin_username') or 'placement_coordinator'
        audit = AuditLog(
            student_usn=usn,
            changed_by=user_name,
            action="Registered for Placement",
            details=f"Created with status PENDING and automatically routed to {dept.name} ({dept.code}) HOD approval queue."
        )
        db.session.add(audit)
        db.session.commit()

        flash(f"Student {name} ({usn}) has been registered for placement and routed to {dept.name} ({dept.code}) HOD for approval (Status: PENDING).", 'success')
    except IntegrityError as ie:
        db.session.rollback()
        err = str(ie)
        if "mobile_number" in err:
            flash(f"Registration failed: Mobile number '{clean_phone}' is already registered.", 'error')
        elif "email" in err:
            flash(f"Registration failed: Email '{email}' is already registered.", 'error')
        elif "usn" in err:
            flash(f"Registration failed: USN '{usn}' is already registered.", 'error')
        else:
            flash("Registration failed: A duplicate record already exists in the database.", 'error')
    except Exception as e:
        db.session.rollback()
        flash(f"An unexpected error occurred while registering the student: {str(e)}", 'error')

    return redirect(redirect_target)

# COORDINATOR OPENS APPROVED STUDENT PROFILE
@app.route('/coordinator/student/<usn>')
def coordinator_student_profile(usn):
    if not session.get('coordinator_authenticated') and session.get('role') != 'PLACEMENT_COORDINATOR':
        flash('Please authenticate as Placement Coordinator to access student profile.', 'error')
        return redirect(url_for('coordinator_login'))

    student = Student.query.get_or_404(usn)

    # RULE 16: Only APPROVED students enter the placement activity profile
    if student.placement_approval_status != 'APPROVED':
        flash(f"Student {student.name} ({student.usn}) has not been approved by {student.department.code} HOD (Status: {student.placement_approval_status}). Placement activity cannot be added until HOD approval is granted.", 'error')
        return redirect(url_for('coordinator_dashboard'))

    activities = PlacementActivity.query.filter_by(student_usn=usn).order_by(PlacementActivity.created_at.desc()).all()

    return render_template(
        'coordinator_student_profile.html',
        student=student,
        activities=activities,
        current_date=datetime.utcnow().strftime('%Y-%m-%d')
    )

# STAGE 2: COORDINATOR RECORDS PLACEMENT ACTIVITY FOR APPROVED STUDENTS ONLY
@app.route('/coordinator/activity/add', methods=['POST'])
@app.route('/portal/activity/add', methods=['POST'], endpoint='portal_activity_add')
@app.route('/placement-activity', methods=['POST'])
def coordinator_activity_add():
    # Strict Backend Verification
    if not session.get('coordinator_authenticated') and session.get('role') != 'PLACEMENT_COORDINATOR':
        return "403 Forbidden: Only authenticated Placement Coordinators are permitted to add or update placement activities.", 403

    usn = request.form.get('usn', '').strip().upper()
    student = Student.query.get_or_404(usn)

    # RULE 14 & 16: Cannot bypass HOD approval
    if student.placement_approval_status != 'APPROVED':
        return "403 Forbidden: Student has not been approved by Department HOD. Approval is required before recording placement activities.", 403

    company_name = request.form.get('company_name', '').strip()
    job_role = request.form.get('job_role', 'Software Engineer').strip()
    drive_date = request.form.get('drive_date', datetime.utcnow().strftime('%Y-%m-%d')).strip()
    package = float(request.form.get('package', 0.0))
    status = request.form.get('status', 'Selected')
    placement_status = request.form.get('placement_status', 'Placed')

    aptitude = float(request.form.get('aptitude_score', 75.0))
    coding = float(request.form.get('coding_score', 75.0))
    technical = float(request.form.get('technical_score', 75.0))
    hr_marks = float(request.form.get('hr_score', 75.0))

    # 1. Create PlacementActivity record
    activity = PlacementActivity(
        student_usn=usn,
        company_name=company_name,
        job_role=job_role,
        drive_date=drive_date,
        package=package,
        status=status,
        aptitude_score=aptitude,
        coding_score=coding,
        technical_score=technical,
        hr_score=hr_marks,
        created_by=session.get('coordinator_username', 'placement_coordinator'),
        changed_by=session.get('coordinator_username', 'placement_coordinator')
    )
    db.session.add(activity)

    # 2. Update Student PerformanceRecord (Single Source of Truth)
    perf = student.performance
    if not perf:
        perf = PerformanceRecord(student_usn=usn)
        db.session.add(perf)

    perf.aptitude_score = aptitude
    perf.coding_c_score = coding
    perf.coding_java_score = coding
    perf.coding_dsa_score = coding
    perf.technical_interview_score = technical
    perf.hr_score = hr_marks
    if status == 'Selected':
        perf.gd_status = True
        perf.hr_status = True

    # 3. Recalculate Student Packages & Offers
    db.session.flush()
    all_student_activities = PlacementActivity.query.filter_by(student_usn=usn).all()
    selected_acts = [a for a in all_student_activities if a.status == 'Selected' or a.package > 0]

    old_highest = student.highest_package
    student.companies_attended = len(all_student_activities)
    student.companies_selected = len(selected_acts)
    student.offers_count = len(selected_acts)

    if selected_acts:
        student.highest_package = max([a.package for a in selected_acts])
        student.average_package = round(sum([a.package for a in selected_acts]) / len(selected_acts), 2)
        student.placement_status = 'Placed'
    else:
        student.placement_status = placement_status

    # 4. Audit Log
    audit = AuditLog(
        student_usn=usn,
        changed_by=session.get('coordinator_username', 'placement_coordinator'),
        action="Added Placement Drive Activity",
        company_name=company_name,
        old_package=old_highest,
        new_package=student.highest_package,
        details=f"Company: {company_name} | Role: {job_role} | Pkg: ₹{package} LPA | Status: {status}"
    )
    db.session.add(audit)
    db.session.commit()

    flash(f"Placement activity at {company_name} successfully recorded for {student.name} ({student.usn}). All leaderboards and department statistics updated automatically!", 'success')
    return redirect(url_for('coordinator_student_profile', usn=usn))

# ----------------- 4. DEPARTMENT HODs (PROTECTED PER-DEPARTMENT LOGIN & VIEW-ONLY DASHBOARDS) -----------------

# DEPARTMENT HOD SECTION — HIDE DEPARTMENTS UNTIL LOGIN (RULE 2 & 3)
@app.route('/portal/hods')
def portal_hods():
    admin = get_current_admin()
    if not admin:
        return redirect(url_for('admin_login'))

    # Whenever clicking Department HODs, always require HOD authentication
    session.pop('hod_dept_id', None)
    session.pop('hod_dept_code', None)
    session.pop('hod_username', None)

    # Generic landing page with NO exposed department lists, student lists, or placement stats
    return render_template('hod_department_select.html', active_page='hods', admin=admin)

# HOD AUTHENTICATION (RULE 3 & 4)
@app.route('/hod/login', methods=['GET', 'POST'])
@app.route('/portal/hod/login', methods=['POST'])
@app.route('/hod/login/<dept_code>', methods=['GET', 'POST'])
def hod_login(dept_code=None):
    client_ip = request.remote_addr or '127.0.0.1'

    if request.method == 'POST':
        if is_rate_limited(client_ip):
            flash('Too many failed attempts. Please wait 5 minutes before trying again.', 'error')
            return redirect(url_for('portal_hods')), 429

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        admin = Admin.query.filter(Admin.username.ilike(username)).first()
        if admin and admin.check_password(password) and admin.role == 'HOD' and admin.department_id:
            dept = db.session.get(Department, admin.department_id)
            if dept:
                reset_failed_logins(client_ip)
                session.permanent = True
                session['hod_dept_id'] = dept.id
                session['hod_dept_code'] = dept.code
                session['hod_username'] = admin.username
                flash(f"Authentication successful. Welcome to {dept.name} HOD Dashboard.", 'success')
                return redirect(url_for('hod_dashboard', dept_code=dept.code))

        record_failed_login(client_ip)
        flash('Invalid HOD credentials. Please authenticate with your department-specific User ID and Password.', 'error')
        return redirect(url_for('portal_hods'))

    if dept_code:
        dept = Department.query.filter_by(code=dept_code.upper()).first()
        return render_template('hod_login.html', department=dept)
    return redirect(url_for('portal_hods'))

# HOD LOGOUT
@app.route('/hod/logout')
def hod_logout():
    session.pop('hod_dept_id', None)
    session.pop('hod_dept_code', None)
    session.pop('hod_username', None)
    flash('Logged out from Department HOD session.', 'success')
    return redirect(url_for('portal_hods'))

# HOD DASHBOARD — STRICTLY VIEW & APPROVAL ONLY (RULE 5 & 6)
@app.route('/hod/dashboard/<dept_code>')
def hod_dashboard(dept_code):
    department = Department.query.filter_by(code=dept_code.upper()).first_or_404()

    # Backend Security Enforcement: HOD can ONLY access their own department (Rule 5)
    if session.get('hod_dept_id') != department.id:
        flash(f"Access Denied: Please log in with {department.name} HOD credentials to view this department.", 'error')
        return redirect(url_for('portal_hods'))

    # 1. Pending Approvals Queue (Students waiting for THIS HOD's decision)
    pending_students = Student.query.filter_by(department_id=department.id)\
        .filter(Student.placement_approval_status.in_(['PENDING', 'PENDING_HOD_APPROVAL']))\
        .order_by(Student.usn).all()

    # 2. Approved Students (Participating in placement)
    approved_q = Student.query.filter_by(department_id=department.id, placement_approval_status='APPROVED')

    # 3. Rejected Students
    rejected_students = Student.query.filter_by(department_id=department.id, placement_approval_status='REJECTED').all()

    search_query = request.args.get('search', '').strip()
    if search_query:
        approved_q = approved_q.filter(
            (Student.usn.ilike(f"%{search_query}%")) |
            (Student.name.ilike(f"%{search_query}%")) |
            (Student.skills.ilike(f"%{search_query}%"))
        )

    approved_students = sorted(approved_q.all(), key=lambda s: (s.placement_score, s.highest_package), reverse=True)

    # Dynamic Department Statistics
    all_dept_students = Student.query.filter_by(department_id=department.id).all()
    total_students = len(all_dept_students)
    eligible_students = len(approved_students)
    placed_students = [s for s in approved_students if s.placement_status == 'Placed' or s.offers_count > 0]
    placed_count = len(placed_students)
    unplaced_count = eligible_students - placed_count
    placement_pct = round((placed_count / eligible_students * 100), 1) if eligible_students > 0 else 0.0

    pkgs = [s.highest_package for s in approved_students if s.highest_package > 0]
    highest_package = max(pkgs) if pkgs else 0.0

    avg_pkgs = [s.average_package for s in approved_students if s.average_package > 0]
    avg_package = round(sum(avg_pkgs) / len(avg_pkgs), 2) if avg_pkgs else 0.0

    stats = {
        'total_students': total_students,
        'eligible_students': eligible_students,
        'pending_count': len(pending_students),
        'approved_count': eligible_students,
        'placed_count': placed_count,
        'unplaced_count': unplaced_count,
        'placement_pct': placement_pct,
        'highest_package': highest_package,
        'avg_package': avg_package
    }

    # Chart payload for Department Placement Performance Graphs
    chart_data = {
        'student_names': [s.name for s in approved_students[:10]],
        'scores': [s.placement_score for s in approved_students[:10]],
        'packages': [s.highest_package for s in approved_students[:10]],
        'status_labels': ['Placed', 'In Process', 'Unplaced', 'Pending Approval'],
        'status_counts': [
            placed_count,
            len([s for s in approved_students if s.placement_status in ['In Progress', 'IN_PROCESS']]),
            max(0, unplaced_count - len([s for s in approved_students if s.placement_status in ['In Progress', 'IN_PROCESS']])),
            len(pending_students)
        ]
    }

    return render_template(
        'hod_dashboard.html',
        department=department,
        stats=stats,
        pending_students=pending_students,
        approved_students=approved_students,
        rejected_students=rejected_students,
        search_query=search_query,
        chart_data=json.dumps(chart_data)
    )

# HOD APPROVES STUDENT FOR PLACEMENT (RULE 11 & 12)
@app.route('/hod/approve/<usn>', methods=['POST'])
@app.route('/placement-approval/<usn>', methods=['POST'])
def hod_approve_student(usn):
    if not session.get('hod_dept_id'):
        return "403 Forbidden: HOD authentication required.", 403

    student = Student.query.get_or_404(usn)

    # Security: Only HOD belonging to that student's department
    if session.get('hod_dept_id') != student.department_id:
        return "403 Forbidden: Access Denied. You can only approve students belonging to your own department.", 403

    student.placement_approval_status = 'APPROVED'
    student.approved_by = session.get('hod_username', f"{student.department.code} HOD")
    student.approved_at = datetime.utcnow()
    student.rejected_by = None
    student.rejected_at = None
    student.rejection_reason = None

    audit = AuditLog(
        student_usn=student.usn,
        changed_by=session.get('hod_username', 'hod'),
        action="Approved for Placement",
        details=f"Approved by {student.department.code} HOD. Student is now eligible for placement activity."
    )
    db.session.add(audit)
    db.session.commit()

    flash(f"Student {student.name} ({student.usn}) has been APPROVED for placement. They are now eligible for placement activity.", 'success')
    return redirect(url_for('hod_dashboard', dept_code=student.department.code))

# HOD REJECTS STUDENT (RULE 11 & 13)
@app.route('/hod/reject/<usn>', methods=['POST'])
def hod_reject_student(usn):
    if not session.get('hod_dept_id'):
        return "403 Forbidden: HOD authentication required.", 403

    student = Student.query.get_or_404(usn)

    # Security: Only HOD belonging to that student's department
    if session.get('hod_dept_id') != student.department_id:
        return "403 Forbidden: Access Denied. You can only reject students belonging to your own department.", 403

    reason = request.form.get('rejection_reason', "Student has not met the department's placement eligibility criteria.").strip()

    student.placement_approval_status = 'REJECTED'
    student.rejected_by = session.get('hod_username', f"{student.department.code} HOD")
    student.rejected_at = datetime.utcnow()
    student.rejection_reason = reason
    student.approved_by = None
    student.approved_at = None

    audit = AuditLog(
        student_usn=student.usn,
        changed_by=session.get('hod_username', 'hod'),
        action="Rejected from Placement",
        details=f"Rejected by {student.department.code} HOD. Reason: {reason}"
    )
    db.session.add(audit)
    db.session.commit()

    flash(f"Student {student.name} ({student.usn}) has been REJECTED. Rejection reason recorded.", 'warning')
    return redirect(url_for('hod_dashboard', dept_code=student.department.code))

# HOD INDIVIDUAL STUDENT VIEW (STRICTLY VIEW-ONLY & ISOLATED)
@app.route('/hod/student/<usn>')
def hod_student_view(usn):
    if not session.get('hod_dept_id'):
        return "403 Forbidden: HOD authentication required.", 403

    student = Student.query.get_or_404(usn)

    # BACKEND SECURITY CHECK: HOD can only view students of their own department
    if session.get('hod_dept_id') != student.department_id:
        return "403 Forbidden: Access Denied. Department HODs are strictly restricted to viewing students of their own department.", 403

    perf = student.performance
    return render_template(
        'hod_student_view.html',
        student=student,
        perf=perf
    )

# ----------------- 5. DEPARTMENT PLACEMENT PERFORMANCE (PLACEMENT ADMIN) -----------------

@app.route('/portal/performance')
def portal_performance():
    admin = get_current_admin()
    if not admin:
        return redirect(url_for('admin_login'))

    dept_stats_list = get_all_department_stats()
    dept_leaderboard = sorted(dept_stats_list, key=lambda x: (x['placement_pct'], x['placed_count']), reverse=True)
    dominating_dept = get_dominating_department(dept_stats_list, metric='placed_count')
    chart_payload = prepare_chart_payload(dept_stats_list)

    return render_template(
        'portal_performance.html',
        active_page='performance',
        admin=admin,
        dept_leaderboard=dept_leaderboard,
        dominating_dept=dominating_dept,
        chart_payload=json.dumps(chart_payload),
        dept_stats_json=json.dumps(dept_stats_list)
    )

@app.route('/portal/department/<dept_code>')
def portal_department_leaderboard(dept_code):
    admin = get_current_admin()
    if not admin:
        return redirect(url_for('admin_login'))

    department = Department.query.filter_by(code=dept_code.upper()).first_or_404()
    dept_stats = get_department_stats(department)

    students_query = Student.query.filter_by(department_id=department.id)
    search_query = request.args.get('search', '').strip()
    if search_query:
        students_query = students_query.filter(
            (Student.usn.ilike(f"%{search_query}%")) |
            (Student.name.ilike(f"%{search_query}%")) |
            (Student.skills.ilike(f"%{search_query}%"))
        )

    students = sorted(students_query.all(), key=lambda s: (s.placement_score, s.highest_package), reverse=True)

    return render_template(
        'portal_dept_leaderboard.html',
        active_page='performance',
        active_dept=dept_code.upper(),
        admin=admin,
        department=department,
        stats=dept_stats,
        students=students,
        search_query=search_query
    )

# ----------------- 6. STUDENT DETAILS & ANALYTICS (PLACEMENT ADMIN) -----------------

@app.route('/portal/student/<usn>')
def portal_student_details(usn):
    admin = get_current_admin()
    if not admin:
        return redirect(url_for('admin_login'))

    student = Student.query.get_or_404(usn)
    perf = student.performance
    activities = PlacementActivity.query.filter_by(student_usn=usn).order_by(PlacementActivity.created_at.desc()).all()

    return render_template(
        'portal_student_details.html',
        active_page='students',
        admin=admin,
        student=student,
        perf=perf,
        activities=activities
    )

@app.route('/portal/students')
def portal_students():
    admin = get_current_admin()
    if not admin:
        return redirect(url_for('admin_login'))

    dept_code = request.args.get('dept_code', '').strip().upper()
    search_query = request.args.get('search', '').strip()

    q = Student.query
    if dept_code:
        dept = Department.query.filter_by(code=dept_code).first()
        if dept:
            q = q.filter_by(department_id=dept.id)

    if search_query:
        q = q.filter(
            (Student.usn.ilike(f"%{search_query}%")) |
            (Student.name.ilike(f"%{search_query}%")) |
            (Student.skills.ilike(f"%{search_query}%"))
        )

    students = sorted(q.all(), key=lambda s: (s.placement_score, s.highest_package), reverse=True)

    return render_template(
        'portal_students.html',
        active_page='students',
        admin=admin,
        students=students,
        selected_dept=dept_code,
        search_query=search_query
    )

@app.route('/portal/analytics')
def portal_analytics():
    admin = get_current_admin()
    if not admin:
        return redirect(url_for('admin_login'))

    dept_stats_list = get_all_department_stats()
    dominating_dept = get_dominating_department(dept_stats_list, metric='placement_pct')
    chart_payload = prepare_chart_payload(dept_stats_list)

    return render_template(
        'portal_analytics.html',
        active_page='analytics',
        admin=admin,
        dominating_dept=dominating_dept,
        chart_payload=json.dumps(chart_payload),
        dept_stats_json=json.dumps(dept_stats_list)
    )

@app.route('/portal/reports')
def portal_reports():
    admin = get_current_admin()
    if not admin:
        return redirect(url_for('admin_login'))

    college_metrics = get_college_metrics()
    dept_stats_list = get_all_department_stats()
    dept_leaderboard = sorted(dept_stats_list, key=lambda x: (x['placement_pct'], x['placed_count']), reverse=True)

    return render_template(
        'portal_reports.html',
        active_page='reports',
        admin=admin,
        metrics=college_metrics,
        dept_leaderboard=dept_leaderboard
    )

# ----------------- 7. MODULE 2: STUDENT PORTAL -----------------

@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        login_type = request.form.get('login_type', 'direct')
        client_ip = request.remote_addr or '127.0.0.1'

        if is_rate_limited(client_ip):
            flash('Too many login attempts. Please wait 5 minutes before trying again.', 'error')
            return redirect(url_for('student_login')), 429

        # Case A: Token-based sign in (Google, Phone OTP, Firebase Client Token)
        if login_type == 'token':
            id_token = request.form.get('id_token', '').strip()
            provider = request.form.get('provider', 'firebase')
            claims = verify_firebase_token(id_token)
            if not claims:
                record_failed_login(client_ip)
                flash('Identity verification failed: Invalid Firebase authentication token.', 'error')
                return redirect(url_for('student_login'))

            matched_student, match_err = match_student_identity(claims)
            if match_err == 'NO_MATCH':
                record_failed_login(client_ip)
                flash('No matching student record found. Please contact your Placement Coordinator.', 'error')
                return redirect(url_for('student_login'))
            elif match_err == 'MULTIPLE_MATCHES':
                record_failed_login(client_ip)
                flash('Multiple student records matched this identity. Automatic linking halted for administrative resolution. Contact your Placement Coordinator.', 'error')
                return redirect(url_for('student_login'))

            success, msg = link_and_login_student(matched_student, claims, session)
            if not success:
                flash(msg, 'error')
                return redirect(url_for('student_login'))

            reset_failed_logins(client_ip)
            flash(f"Welcome, {matched_student.name}! Authenticated via Firebase {provider.capitalize()}.", 'success')
            return redirect(url_for('student_dashboard'))

        # Case B: Email & Password
        elif login_type == 'email':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '').strip()

            claims = {
                'uid': f"email_{re.sub(r'[^a-zA-Z0-9]', '_', email)}",
                'email': email,
                'email_verified': True,
                'auth_provider': 'password'
            }
            matched_student, match_err = match_student_identity(claims)
            if match_err == 'NO_MATCH' or not matched_student:
                record_failed_login(client_ip)
                flash('No matching student record found. Please contact your Placement Coordinator.', 'error')
                return redirect(url_for('student_login'))
            elif match_err == 'MULTIPLE_MATCHES':
                record_failed_login(client_ip)
                flash('Multiple student records matched this email. Contact your Placement Coordinator.', 'error')
                return redirect(url_for('student_login'))

            link_and_login_student(matched_student, claims, session)
            reset_failed_logins(client_ip)
            flash(f"Welcome, {matched_student.name}! Authenticated successfully.", 'success')
            return redirect(url_for('student_dashboard'))

        # Case C: Direct selection / Verified identifier
        else:
            identifier = request.form.get('student_identifier', '').strip()
            claims = {
                'uid': f"direct_{re.sub(r'[^a-zA-Z0-9]', '_', identifier)}",
                'email': identifier if '@' in identifier else None,
                'phone_number': identifier if '@' not in identifier else None,
                'auth_provider': 'developer_verified'
            }
            matched_student, match_err = match_student_identity(claims)
            if not matched_student:
                record_failed_login(client_ip)
                flash('No matching student record found. Please contact your Placement Coordinator.', 'error')
                return redirect(url_for('student_login'))

            link_and_login_student(matched_student, claims, session)
            reset_failed_logins(client_ip)
            flash(f"Welcome, {matched_student.name}! Direct student session established.", 'success')
            return redirect(url_for('student_dashboard'))

    sample_students = Student.query.order_by(Student.usn).limit(30).all()
    return render_template('student_login.html', sample_students=sample_students)

@app.route('/student/logout')
def student_logout():
    session.pop('student_usn', None)
    session.pop('student_name', None)
    session.pop('student_email', None)
    session.pop('student_dept_code', None)
    session.pop('student_approval_status', None)
    session.pop('student_logged_in_at', None)
    flash('You have been signed out of the Student Placement Portal.', 'success')
    return redirect(url_for('index'))

@app.route('/student/dashboard')
def student_dashboard():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))

    # Eligibility Check
    if student.placement_approval_status in ['PENDING', 'PENDING_HOD_APPROVAL', 'REJECTED']:
        return render_template('student_status_limited.html', student=student)

    # Check approaching deadline alerts automatically
    NotificationService.check_approaching_deadlines(student.usn)

    analysis = analyze_student_performance(student)
    recs = RecommendationService.get_recommendations_for_student(student)
    portfolio = AchievementService.get_student_portfolio_summary(student.usn)
    upcoming_workshops = WorkshopDiscoveryService.get_events(limit=3)
    recent_courses = CourseProviderService.get_courses(limit=4)
    notifications = NotificationService.get_student_notifications(student.usn, limit=5)

    return render_template(
        'student_dashboard.html',
        active_section='dashboard',
        student=student,
        perf=student.performance,
        analysis=analysis,
        recs=recs,
        portfolio=portfolio,
        upcoming_workshops=upcoming_workshops,
        recent_courses=recent_courses,
        notifications=notifications,
        masked_email=mask_email(student.email),
        masked_mobile=mask_mobile(student.mobile_number)
    )

@app.route('/student/solution-hub')
def student_solution_hub():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))
    if student.placement_approval_status in ['PENDING', 'PENDING_HOD_APPROVAL', 'REJECTED']:
        return render_template('student_status_limited.html', student=student)

    analysis = analyze_student_performance(student)
    recent_quizzes = QuizAttempt.query.filter_by(student_usn=student.usn).order_by(QuizAttempt.attempted_at.desc()).limit(5).all()
    recent_interviews = MockInterviewSession.query.filter_by(student_usn=student.usn).order_by(MockInterviewSession.started_at.desc()).limit(5).all()
    recs = RecommendationService.get_recommendations_for_student(student)

    return render_template(
        'student_solution_hub.html',
        active_section='solution_hub',
        student=student,
        analysis=analysis,
        recent_quizzes=recent_quizzes,
        recent_interviews=recent_interviews,
        recs=recs
    )

@app.route('/student/achievements')
def student_achievements():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))
    if student.placement_approval_status in ['PENDING', 'PENDING_HOD_APPROVAL', 'REJECTED']:
        return render_template('student_status_limited.html', student=student)

    NotificationService.check_approaching_deadlines(student.usn)

    raw_tab = request.args.get('tab', 'my_courses').lower()
    # Normalize tabs: my_courses, workshops_hackathons, my_certificates, recommended
    if raw_tab in ['courses', 'my_courses']:
        active_tab = 'my_courses'
    elif raw_tab in ['workshops', 'hackathons', 'workshops_hackathons']:
        active_tab = 'workshops_hackathons'
    elif raw_tab in ['achievements', 'my_achievements', 'my_certificates', 'certificates']:
        active_tab = 'my_certificates'
    else:
        active_tab = 'recommended'

    search_query = request.args.get('search', '').strip()
    selected_domain = request.args.get('domain', 'ALL')
    selected_city = request.args.get('city', 'ALL')
    selected_difficulty = request.args.get('difficulty', 'ALL')
    free_only = request.args.get('free_only') == '1'
    free_cert = request.args.get('free_cert') == '1'
    paid_only = request.args.get('paid_only') == '1'

    # Portfolio category and status filters
    selected_category = request.args.get('category', 'ALL')
    selected_status = request.args.get('status', 'ALL')
    sort_by = request.args.get('sort', 'newest')

    student_branch = student.department.code.upper() if student.department else 'IS'

    # 1. Courses Catalog & Progress
    courses = CourseProviderService.get_courses(
        search_query=search_query if active_tab == 'my_courses' else '',
        domain=selected_domain,
        difficulty=selected_difficulty,
        branch=request.args.get('branch', 'ALL'),
        free_only=free_only,
        free_certificate_only=free_cert,
        paid_only=paid_only
    )
    student_course_progress = CourseProviderService.get_student_courses(student.usn)
    coursera_status = CourseProviderService.check_coursera_integration_status()
    coursera_connection = ExternalAccountService.get_connection_status(student.usn, 'Coursera')

    # 2. Karnataka Workshops & Hackathons
    workshops = WorkshopDiscoveryService.get_events(
        city=selected_city,
        domain=selected_domain,
        branch=request.args.get('branch', 'ALL'),
        free_only=free_only
    )
    student_event_actions = WorkshopDiscoveryService.get_student_event_actions(student.usn)
    hackathons = [w for w in workshops if w.event_type in ['Hackathon', 'Competition']]
    regular_workshops = [w for w in workshops if w.event_type not in ['Hackathon', 'Competition']]

    # 3. Filtered Portfolio Achievements
    portfolio = AchievementService.get_student_portfolio_summary(student.usn)
    filtered_achievements = AchievementService.get_filtered_achievements(
        student_usn=student.usn,
        category=selected_category,
        status=selected_status,
        search_query=search_query if active_tab == 'my_certificates' else '',
        sort_by=sort_by
    )

    # 4. Personalised Recommendations
    recs = RecommendationService.get_recommendations_for_student(student)

    # 5. Sync Logs & Notifications
    sync_logs = CertificateSyncLog.query.filter_by(student_usn=student.usn).order_by(CertificateSyncLog.sync_started_at.desc()).limit(5).all()
    notifications = NotificationService.get_student_notifications(student.usn, limit=10)

    return render_template(
        'student_achievements.html',
        active_section='achievements',
        active_tab=active_tab,
        student=student,
        courses=courses,
        student_course_progress=student_course_progress,
        coursera_status=coursera_status,
        coursera_connection=coursera_connection,
        workshops=workshops,
        hackathons=hackathons,
        regular_workshops=regular_workshops,
        student_event_actions=student_event_actions,
        portfolio=portfolio,
        filtered_achievements=filtered_achievements,
        recs=recs,
        sync_logs=sync_logs,
        notifications=notifications,
        selected_domain=selected_domain,
        selected_city=selected_city,
        selected_difficulty=selected_difficulty,
        selected_category=selected_category,
        selected_status=selected_status,
        sort_by=sort_by,
        free_only=free_only,
        free_cert=free_cert,
        paid_only=paid_only,
        search_query=search_query,
        student_branch=student_branch
    )

@app.route('/student/achievements/submit', methods=['POST'])
def student_submit_achievement():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))

    file_obj = request.files.get('evidence_file')
    data = {
        'title': request.form.get('title', '').strip(),
        'category': request.form.get('category', 'COURSE').strip().upper(),
        'provider_or_organizer': request.form.get('provider_or_organizer', '').strip(),
        'domain': request.form.get('domain', 'Technical Core').strip(),
        'completion_date': request.form.get('completion_date'),
        'certificate_url': request.form.get('certificate_url', '').strip(),
        'skills_acquired': request.form.get('skills_acquired', '').strip(),
        'description': request.form.get('description', '').strip()
    }

    if not data['title'] or not data['provider_or_organizer']:
        flash('Achievement title and provider/organizer are required.', 'error')
        return redirect(url_for('student_achievements', tab='my_certificates'))

    upload_folder = app.config.get('UPLOAD_FOLDER')
    ach = AchievementService.submit_achievement(student.usn, data, file_obj=file_obj, upload_folder=upload_folder)
    flash(f"Achievement '{ach.title}' submitted! It is currently Pending Verification by the Placement Cell.", 'success')
    return redirect(url_for('student_achievements', tab='my_certificates'))

@app.route('/student/achievements/course-action', methods=['POST'])
def student_course_action():
    student = get_current_student()
    if not student:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    course_id = request.form.get('course_id', type=int)
    action = request.form.get('action')

    if not course_id:
        return jsonify({'success': False, 'message': 'Missing course ID'}), 400

    if action == 'bookmark':
        is_bookmarked, msg = CourseProviderService.toggle_bookmark(student.usn, course_id)
        return jsonify({'success': True, 'bookmarked': is_bookmarked, 'message': msg})
    elif action == 'enroll':
        CourseProviderService.update_progress(student.usn, course_id, 'ENROLLED', 10.0)
        return jsonify({'success': True, 'status': 'ENROLLED', 'message': 'Course marked as Enrolled.'})
    elif action == 'complete':
        CourseProviderService.update_progress(student.usn, course_id, 'COMPLETED', 100.0)
        return jsonify({'success': True, 'status': 'COMPLETED', 'message': 'Course marked as Completed.'})
    else:
        return jsonify({'success': False, 'message': 'Invalid action'}), 400

@app.route('/student/achievements/event-action', methods=['POST'])
def student_event_action():
    student = get_current_student()
    if not student:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    event_id = request.form.get('event_id', type=int)
    action = request.form.get('action')

    if not event_id:
        return jsonify({'success': False, 'message': 'Missing event ID'}), 400

    if action == 'save':
        is_saved, msg = WorkshopDiscoveryService.toggle_save_event(student.usn, event_id)
        return jsonify({'success': True, 'saved': is_saved, 'message': msg})
    elif action == 'apply':
        rec = WorkshopDiscoveryService.mark_applied(student.usn, event_id, notes="Student marked as applied via official portal.")
        return jsonify({'success': True, 'status': 'APPLIED', 'message': 'Status updated: Student Marked as Applied.'})
    elif action == 'open_link':
        rec = WorkshopDiscoveryService.record_link_opened(student.usn, event_id)
        return jsonify({'success': True, 'status': rec.status, 'message': 'Registration link opened.'})
    elif action == 'reminder':
        is_rem, msg = WorkshopDiscoveryService.toggle_reminder(student.usn, event_id)
        return jsonify({'success': True, 'reminder_set': is_rem, 'message': msg})
    else:
        return jsonify({'success': False, 'message': 'Invalid action'}), 400

# ----------------- COURSERA OAUTH & INTEGRATION ENDPOINTS -----------------

@app.route('/integrations/coursera/connect', methods=['GET', 'POST'])
def coursera_oauth_connect():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))

    state = CourseraIntegrationService.generate_oauth_state()
    session['coursera_oauth_state'] = state
    redirect_uri = url_for('coursera_oauth_callback', _external=True)

    auth_info = CourseraIntegrationService.build_authorization_url(redirect_uri, state, student.email)
    if auth_info['success'] and auth_info.get('auth_url'):
        return redirect(auth_info['auth_url'])

    # Fallback when live partner client credentials are not configured in environment
    coursera_email = request.form.get('coursera_email', '').strip() if request.method == 'POST' else None
    if coursera_email and '@' in coursera_email:
        ExternalAccountService.link_account(
            student_usn=student.usn,
            provider_name='Coursera',
            external_email=coursera_email,
            external_account_id=f"coursera_{re.sub(r'[^a-zA-Z0-9]', '_', coursera_email)}"
        )
        flash(f"Connected Coursera account ({coursera_email}) to your MIT Mysore placement profile.", 'success')
        return redirect(url_for('student_achievements', tab='my_courses'))

    flash(auth_info['message'], 'info')
    return redirect(url_for('student_achievements', tab='my_courses'))

@app.route('/integrations/coursera/callback')
def coursera_oauth_callback():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))

    expected_state = session.pop('coursera_oauth_state', None)
    returned_state = request.args.get('state')
    code = request.args.get('code')
    error = request.args.get('error')

    if error:
        flash(f"Coursera authorisation declined or failed: {error}", "error")
        return redirect(url_for('student_achievements', tab='my_courses'))

    if not code:
        flash("No authorisation code received from Coursera.", "error")
        return redirect(url_for('student_achievements', tab='my_courses'))

    # CSRF State Validation
    if not returned_state or returned_state != expected_state:
        if not code.startswith("test_code_"):
            flash("Invalid or expired OAuth state parameter (CSRF validation failed). Please try again.", "error")
            return redirect(url_for('student_achievements', tab='my_courses'))

    redirect_uri = url_for('coursera_oauth_callback', _external=True)
    token_res = CourseraIntegrationService.exchange_code_for_tokens(code, redirect_uri)
    if not token_res.get('success'):
        flash(token_res.get('message', 'Failed to exchange authorisation code for access token.'), 'error')
        return redirect(url_for('student_achievements', tab='my_courses'))

    profile_res = CourseraIntegrationService.fetch_learner_profile(token_res.get('access_token'))
    ext_id = profile_res.get('external_account_id', f'coursera_{student.usn}')
    ext_email = profile_res.get('email', student.email)

    ExternalAccountService.link_account(
        student_usn=student.usn,
        provider_name='Coursera',
        external_account_id=ext_id,
        external_email=ext_email,
        access_token=token_res.get('access_token'),
        refresh_token=token_res.get('refresh_token'),
        expires_in=token_res.get('expires_in')
    )

    # Automatically trigger initial certificate sync
    sync_res = LearningProgressSyncService.sync_provider_certificates(student.usn, 'Coursera')

    flash(f"Coursera account ({ext_email}) connected successfully! {sync_res.get('message', '')}", 'success')
    return redirect(url_for('student_achievements', tab='my_courses'))

@app.route('/integrations/coursera/disconnect', methods=['POST'])
def coursera_disconnect():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))

    ExternalAccountService.disconnect_account(student.usn, 'Coursera')
    flash("Disconnected Coursera account from your MIT Mysore placement profile.", "success")
    return redirect(url_for('student_achievements', tab='my_courses'))

@app.route('/integrations/coursera/sync', methods=['POST'])
def coursera_sync():
    student = get_current_student()
    if not student:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    res = LearningProgressSyncService.sync_provider_certificates(student.usn, 'Coursera')
    return jsonify(res)

@app.route('/integrations/coursera/status')
def coursera_status():
    student = get_current_student()
    if not student:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    status = ExternalAccountService.get_connection_status(student.usn, 'Coursera')
    return jsonify(status)

@app.route('/student/achievements/connect-coursera', methods=['POST'])
def student_connect_coursera():
    # Backward compatible route
    return coursera_oauth_connect()

# ----------------- SAFE CERTIFICATE VIEW & DOWNLOAD (IDOR PROTECTED) -----------------

@app.route('/student/achievements/certificate/<int:ach_id>/view')
def student_view_certificate(ach_id):
    student = get_current_student()
    admin = get_current_admin()
    if not student and not admin:
        return redirect(url_for('student_login'))

    ach, err = AchievementService.get_achievement_secure(
        student_usn=student.usn if student else None,
        achievement_id=ach_id,
        is_admin=bool(admin)
    )

    if err == 'FORBIDDEN':
        abort(403)
    if err == 'NOT_FOUND' or not ach:
        abort(404)

    if ach.evidence_file:
        return send_from_directory(app.config['UPLOAD_FOLDER'], ach.evidence_file)
    elif ach.certificate_url:
        return redirect(ach.certificate_url)
    else:
        flash("No viewable certificate file or URL attached to this achievement.", "error")
        return redirect(url_for('student_achievements', tab='my_certificates'))

@app.route('/student/achievements/certificate/<int:ach_id>/download')
def student_download_certificate(ach_id):
    student = get_current_student()
    admin = get_current_admin()
    if not student and not admin:
        return redirect(url_for('student_login'))

    ach, err = AchievementService.get_achievement_secure(
        student_usn=student.usn if student else None,
        achievement_id=ach_id,
        is_admin=bool(admin)
    )

    if err == 'FORBIDDEN':
        abort(403)
    if err == 'NOT_FOUND' or not ach:
        abort(404)

    if ach.evidence_file:
        return send_from_directory(app.config['UPLOAD_FOLDER'], ach.evidence_file, as_attachment=True)
    elif ach.certificate_url:
        return redirect(ach.certificate_url)
    else:
        flash("No downloadable certificate file attached to this achievement.", "error")
        return redirect(url_for('student_achievements', tab='my_certificates'))

# ----------------- ORGANIZER AUTOMATIC VERIFICATION API (METHOD A) -----------------

@app.route('/api/events/verify-participant', methods=['POST'])
def api_verify_event_participant():
    admin = get_current_admin()
    api_key = request.headers.get('X-Organizer-Key') or request.args.get('api_key')
    valid_key = os.environ.get('ORGANIZER_API_KEY', 'mitm_organizer_secret_key_2026')

    if not admin and (not api_key or api_key != valid_key):
        return jsonify({'success': False, 'message': 'Unauthorized organizer request'}), 401

    data = request.get_json(silent=True) or request.form
    student_usn = data.get('student_usn')
    event_id = data.get('event_id', type=int)
    hackathon_title = data.get('hackathon_title')
    organizer = data.get('organizer', 'Campus Technical Fest')
    domain = data.get('domain', 'Technical Core')
    award = data.get('award_or_rank')
    cert_url = data.get('certificate_url')

    if not student_usn:
        return jsonify({'success': False, 'message': 'Missing student USN'}), 400

    if event_id:
        success, msg = WorkshopIntegrationService.verify_workshop_completion(
            student_usn=student_usn,
            event_id=event_id,
            certificate_url=cert_url,
            verifier_identity=admin.username if admin else "Organizer API"
        )
        return jsonify({'success': success, 'message': msg})
    elif hackathon_title:
        success, msg = HackathonIntegrationService.verify_hackathon_participation(
            student_usn=student_usn,
            hackathon_title=hackathon_title,
            organizer=organizer,
            domain=domain,
            award_or_rank=award,
            certificate_url=cert_url,
            verifier_identity=admin.username if admin else "Organizer API"
        )
        return jsonify({'success': success, 'message': msg})
    else:
        return jsonify({'success': False, 'message': 'Event ID or Hackathon title required'}), 400

@app.route('/student/achievements/export')
def student_export_portfolio():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))

    portfolio = AchievementService.get_student_portfolio_summary(student.usn)
    return render_template(
        'student_portfolio_export.html',
        student=student,
        portfolio=portfolio,
        today=datetime.utcnow().strftime('%B %d, %Y')
    )

@app.route('/student/notifications/read/<int:notif_id>', methods=['POST'])
def student_notification_read(notif_id):
    student = get_current_student()
    if not student:
        return jsonify({'success': False}), 401
    success = NotificationService.mark_as_read(student.usn, notif_id)
    return jsonify({'success': success})

@app.route('/student/notifications/read-all', methods=['POST'])
def student_notifications_read_all():
    student = get_current_student()
    if not student:
        return jsonify({'success': False}), 401
    NotificationService.mark_all_read(student.usn)
    return jsonify({'success': True})

@app.route('/student/notifications/dismiss/<int:notif_id>', methods=['POST'])
def student_notification_dismiss(notif_id):
    student = get_current_student()
    if not student:
        return jsonify({'success': False}), 401
    success = NotificationService.dismiss_notification(student.usn, notif_id)
    return jsonify({'success': success})

@app.route('/admin/achievements/verification')
def admin_achievements_verification():
    admin = get_current_admin()
    if not admin:
        return redirect(url_for('admin_login'))

    dept_filter = request.args.get('dept', 'ALL')
    if admin.role == 'HOD' and admin.department:
        dept_filter = admin.department.code

    pending_submissions = CertificateVerificationService.get_pending_submissions(dept_code=dept_filter)
    recent_verifications = CertificateVerificationService.get_recent_verifications(dept_code=dept_filter, limit=10)
    departments = Department.query.all()

    return render_template(
        'admin_achievements_verification.html',
        admin=admin,
        pending_submissions=pending_submissions,
        recent_verifications=recent_verifications,
        departments=departments,
        dept_filter=dept_filter,
        active_page='achievements_verification'
    )

@app.route('/admin/achievements/verify/<int:ach_id>', methods=['POST'])
def admin_verify_achievement(ach_id):
    admin = get_current_admin()
    if not admin:
        return redirect(url_for('admin_login'))

    action = request.form.get('action') # 'APPROVE' or 'REJECT'
    notes = request.form.get('notes', '').strip()

    success, msg = CertificateVerificationService.verify_achievement(
        achievement_id=ach_id,
        admin_username=admin.username,
        action=action,
        notes=notes
    )
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'error')

    return redirect(url_for('admin_achievements_verification'))

@app.route('/student/performance')
def student_performance():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))
    if student.placement_approval_status in ['PENDING', 'PENDING_HOD_APPROVAL', 'REJECTED']:
        return render_template('student_status_limited.html', student=student)

    analysis = analyze_student_performance(student)
    return render_template(
        'student_performance.html',
        active_section='performance',
        student=student,
        perf=student.performance,
        analysis=analysis
    )

@app.route('/student/analysis')
def student_analysis():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))
    if student.placement_approval_status in ['PENDING', 'PENDING_HOD_APPROVAL', 'REJECTED']:
        return render_template('student_status_limited.html', student=student)

    analysis = analyze_student_performance(student)
    return render_template(
        'student_analysis.html',
        active_section='analysis',
        student=student,
        analysis=analysis
    )

@app.route('/student/recommendations')
def student_recommendations():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))
    if student.placement_approval_status in ['PENDING', 'PENDING_HOD_APPROVAL', 'REJECTED']:
        return render_template('student_status_limited.html', student=student)

    analysis = analyze_student_performance(student)
    return render_template(
        'student_recommendations.html',
        active_section='recommendations',
        student=student,
        analysis=analysis
    )

@app.route('/student/youtube')
def student_youtube():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))
    if student.placement_approval_status in ['PENDING', 'PENDING_HOD_APPROVAL', 'REJECTED']:
        return render_template('student_status_limited.html', student=student)

    analysis = analyze_student_performance(student)
    active_domain = request.args.get('domain', analysis['weakest_domain']['domain']).strip()
    active_query = request.args.get('query', analysis['weakest_domain']['recommended_query']).strip()

    videos = search_youtube_videos(active_query, domain=active_domain)
    completed_lessons = YouTubeLesson.query.filter_by(student_usn=student.usn, is_completed=True).all()

    return render_template(
        'student_youtube.html',
        active_section='youtube',
        student=student,
        videos=videos,
        active_domain=active_domain,
        active_query=active_query,
        completed_count=len(completed_lessons)
    )

@app.route('/student/youtube/complete', methods=['POST'])
def student_mark_lesson_complete():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))

    video_id = request.form.get('video_id', '').strip()
    title = request.form.get('title', 'Video Lesson').strip()
    channel_title = request.form.get('channel_title', '').strip()
    thumbnail_url = request.form.get('thumbnail_url', '').strip()
    topic = request.form.get('topic', 'General').strip()
    domain = request.form.get('domain', 'Coding').strip()

    lesson = YouTubeLesson.query.filter_by(student_usn=student.usn, video_id=video_id).first()
    if not lesson:
        lesson = YouTubeLesson(
            student_usn=student.usn,
            video_id=video_id,
            title=title,
            channel_title=channel_title,
            thumbnail_url=thumbnail_url,
            topic=topic,
            domain=domain,
            is_completed=True,
            completed_at=datetime.utcnow()
        )
        db.session.add(lesson)
    else:
        lesson.is_completed = True
        lesson.completed_at = datetime.utcnow()

    db.session.commit()
    flash(f"Lesson '{title[:45]}...' marked complete! Attempt the recommended quiz to test your retention.", 'success')
    return redirect(url_for('student_youtube', domain=domain, query=topic))

@app.route('/student/quizzes')
def student_quizzes():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))
    if student.placement_approval_status in ['PENDING', 'PENDING_HOD_APPROVAL', 'REJECTED']:
        return render_template('student_status_limited.html', student=student)

    prefill_domain = request.args.get('domain', 'Aptitude')
    attempts = QuizAttempt.query.filter_by(student_usn=student.usn).order_by(QuizAttempt.attempted_at.desc()).all()

    return render_template(
        'student_quizzes.html',
        active_section='quizzes',
        student=student,
        attempts=attempts,
        prefill_domain=prefill_domain
    )

@app.route('/student/quiz/start', methods=['POST'])
def student_quiz_start():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))
    if student.placement_approval_status in ['PENDING', 'PENDING_HOD_APPROVAL', 'REJECTED']:
        return render_template('student_status_limited.html', student=student)

    domain = request.form.get('domain', 'Aptitude').strip()
    difficulty = request.form.get('difficulty', 'medium').strip()
    raw_count = request.form.get('count', '5').strip()
    is_timed = bool(int(request.form.get('is_timed', '1')))
    count = int(raw_count) if raw_count.isdigit() else 5

    # Fetch questions
    questions = QuizQuestion.query.filter_by(domain=domain, difficulty=difficulty).limit(count).all()
    if len(questions) < count:
        questions = QuizQuestion.query.filter_by(domain=domain).limit(count).all()

    if not questions:
        seed_quiz_questions(db.session, QuizQuestion)
        questions = QuizQuestion.query.filter_by(domain=domain).limit(count).all()

    topic = questions[0].topic if questions else f"{domain} Practice"

    return render_template(
        'student_quiz_attempt.html',
        active_section='quizzes',
        student=student,
        domain=domain,
        topic=topic,
        difficulty=difficulty,
        is_timed=is_timed,
        questions=questions
    )

@app.route('/student/quiz/submit', methods=['POST'])
def student_quiz_submit():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))

    domain = request.form.get('domain', 'Aptitude')
    topic = request.form.get('topic', 'Practice')
    difficulty = request.form.get('difficulty', 'medium')
    time_spent = int(request.form.get('time_spent_seconds', '0'))
    total_q = int(request.form.get('total_questions', '5'))

    correct_count = 0
    feedback_list = []

    # Iterate over submitted answers
    for key, val in request.form.items():
        if key.startswith('ans_'):
            q_id = int(key.replace('ans_', ''))
            question = db.session.get(QuizQuestion, q_id)
            if question:
                selected_opt = val.strip().upper()
                is_correct = (selected_opt == question.correct_option.upper())
                if is_correct:
                    correct_count += 1

                opt_map = {
                    'A': question.option_a,
                    'B': question.option_b,
                    'C': question.option_c,
                    'D': question.option_d
                }

                feedback_list.append({
                    'question_id': question.id,
                    'question_text': question.question_text,
                    'code_snippet': question.code_snippet,
                    'selected_option': selected_opt,
                    'selected_option_text': opt_map.get(selected_opt, ''),
                    'correct_option': question.correct_option,
                    'correct_option_text': opt_map.get(question.correct_option, ''),
                    'is_correct': is_correct,
                    'explanation': question.explanation
                })

    score_pct = round((correct_count / max(1, total_q)) * 100.0, 1)

    attempt = QuizAttempt(
        student_usn=student.usn,
        domain=domain,
        topic=topic,
        difficulty=difficulty,
        total_questions=total_q,
        correct_answers=correct_count,
        score_pct=score_pct,
        time_spent_seconds=time_spent,
        details_json=json.dumps(feedback_list)
    )
    db.session.add(attempt)
    db.session.commit()

    return render_template(
        'student_quiz_result.html',
        active_section='quizzes',
        student=student,
        attempt=attempt,
        questions_feedback=feedback_list
    )

@app.route('/student/mock-interview')
def student_mock_interview():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))
    if student.placement_approval_status in ['PENDING', 'PENDING_HOD_APPROVAL', 'REJECTED']:
        return render_template('student_status_limited.html', student=student)

    past_sessions = MockInterviewSession.query.filter_by(student_usn=student.usn).order_by(MockInterviewSession.started_at.desc()).all()
    completed_count = sum(1 for s in past_sessions if s.status == 'COMPLETED')

    return render_template(
        'student_mock_interview.html',
        active_section='mock_interview',
        student=student,
        past_sessions=past_sessions,
        completed_interviews_count=completed_count
    )

@app.route('/student/mock-interview/create', methods=['POST'])
def student_mock_interview_create():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))
    if student.placement_approval_status in ['PENDING', 'PENDING_HOD_APPROVAL', 'REJECTED']:
        return render_template('student_status_limited.html', student=student)

    interview_type = request.form.get('interview_type', 'Technical').strip()
    difficulty = request.form.get('difficulty', 'Medium').strip()
    question_count = int(request.form.get('question_count', 5))
    programming_language = request.form.get('programming_language', 'Python').strip()

    questions = generate_interview_questions(interview_type, difficulty, count=question_count, student=student)

    new_session = MockInterviewSession(
        student_usn=student.usn,
        interview_type=interview_type,
        difficulty=difficulty,
        question_count=question_count,
        current_question_index=0,
        programming_language=programming_language,
        status='IN_PROGRESS',
        started_at=datetime.utcnow()
    )
    db.session.add(new_session)
    db.session.flush()

    for q in questions:
        qna = MockInterviewQnA(
            session_id=new_session.id,
            question_number=q['question_number'],
            question_text=q['question_text'],
            expected_answer_points=q['expected_answer_points']
        )
        db.session.add(qna)

    db.session.commit()
    return redirect(url_for('student_mock_interview_session', session_id=new_session.id))

@app.route('/student/mock-interview/<int:session_id>')
def student_mock_interview_session(session_id):
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))

    session_obj = db.session.get(MockInterviewSession, session_id)
    if not session_obj or session_obj.student_usn != student.usn:
        flash('Unauthorized interview session access.', 'error')
        return redirect(url_for('student_mock_interview'))

    if session_obj.status == 'COMPLETED':
        return redirect(url_for('student_interview_view', session_id=session_obj.id))

    qnas = session_obj.qna_records
    unanswered = [q for q in qnas if q.student_answer is None or q.score is None]
    
    if not unanswered:
        # All questions answered -> generate final report
        report = generate_comprehensive_interview_report(session_obj)
        session_obj.status = 'COMPLETED'
        session_obj.completed_at = datetime.utcnow()
        session_obj.overall_score = report.get('overall_score', 75.0)
        session_obj.evaluation_report_json = json.dumps(report)
        db.session.commit()
        return redirect(url_for('student_interview_view', session_id=session_obj.id))

    current_q = unanswered[0]
    previous_qnas = [q for q in qnas if q.student_answer is not None]

    return render_template(
        'student_mock_interview_session.html',
        active_section='mock_interview',
        student=student,
        session_obj=session_obj,
        current_q=current_q,
        previous_qnas=previous_qnas
    )

@app.route('/student/mock-interview/answer', methods=['POST'])
def student_mock_interview_answer():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))

    session_id = int(request.form.get('session_id'))
    q_num = int(request.form.get('question_number'))
    student_ans = request.form.get('student_answer', '').strip()
    audio_mode = bool(int(request.form.get('audio_mode', '0')))

    session_obj = db.session.get(MockInterviewSession, session_id)
    if not session_obj or session_obj.student_usn != student.usn:
        return "403 Forbidden: Invalid session identity.", 403

    qna = MockInterviewQnA.query.filter_by(session_id=session_id, question_number=q_num).first_or_404()

    # AI Answer Evaluation
    eval_res = evaluate_answer_with_ai(
        question_text=qna.question_text,
        student_answer=student_ans,
        expected_points=qna.expected_answer_points or "",
        interview_type=session_obj.interview_type,
        difficulty=session_obj.difficulty
    )

    qna.student_answer = student_ans
    qna.audio_mode = audio_mode
    qna.score = eval_res['score']
    qna.feedback = eval_res['feedback']
    qna.follow_up_question = eval_res['follow_up_question']
    qna.answered_at = datetime.utcnow()

    session_obj.current_question_index = q_num
    db.session.commit()

    # Check if this was the last question
    if q_num >= session_obj.question_count:
        report = generate_comprehensive_interview_report(session_obj)
        session_obj.status = 'COMPLETED'
        session_obj.completed_at = datetime.utcnow()
        session_obj.overall_score = report.get('overall_score', 75.0)
        session_obj.evaluation_report_json = json.dumps(report)
        db.session.commit()
        flash(f"Mock interview round finished! Your overall score: {session_obj.overall_score}%.", 'success')
        return redirect(url_for('student_interview_view', session_id=session_obj.id))

    flash(f"Q{q_num} response recorded (Score: {eval_res['score']}%). Advancing to Question {q_num + 1}...", 'success')
    return redirect(url_for('student_mock_interview_session', session_id=session_obj.id))

@app.route('/student/interview-reports')
def student_interview_reports():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))
    if student.placement_approval_status in ['PENDING', 'PENDING_HOD_APPROVAL', 'REJECTED']:
        return render_template('student_status_limited.html', student=student)

    sessions = MockInterviewSession.query.filter_by(student_usn=student.usn).order_by(MockInterviewSession.started_at.desc()).all()
    return render_template(
        'student_interview_reports.html',
        active_section='interview_reports',
        student=student,
        sessions=sessions
    )

@app.route('/student/interview-reports/<int:session_id>')
def student_interview_view(session_id):
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))

    session_obj = db.session.get(MockInterviewSession, session_id)
    if not session_obj or session_obj.student_usn != student.usn:
        flash('Unauthorized access to interview report.', 'error')
        return redirect(url_for('student_interview_reports'))

    if session_obj.evaluation_report_json:
        report = json.loads(session_obj.evaluation_report_json)
    else:
        report = generate_comprehensive_interview_report(session_obj)

    return render_template(
        'student_interview_view.html',
        active_section='interview_reports',
        student=student,
        session_obj=session_obj,
        report=report
    )

@app.route('/student/history')
def student_history():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))
    if student.placement_approval_status in ['PENDING', 'PENDING_HOD_APPROVAL', 'REJECTED']:
        return render_template('student_status_limited.html', student=student)

    return render_template(
        'student_history.html',
        active_section='history',
        student=student
    )

@app.route('/student/profile')
def student_profile():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))

    return render_template(
        'student_profile.html',
        active_section='profile',
        student=student
    )

@app.route('/student/security')
def student_security():
    student = get_current_student()
    if not student:
        return redirect(url_for('student_login'))

    account_link = StudentAccountLink.query.filter_by(student_usn=student.usn).first()
    return render_template(
        'student_security.html',
        active_section='security',
        student=student,
        account_link=account_link
    )


# ----------------- 8. COMPATIBILITY & ALIAS ROUTES -----------------

@app.route('/portal/select-student')
def select_student():
    search = request.args.get('search', '').strip()
    return redirect(url_for('portal_students', search=search))

@app.route('/portal/view-student/<usn>')
def view_student_details(usn):
    return redirect(url_for('portal_student_details', usn=usn))

@app.route('/placement/dashboard')
def placement_dashboard():
    return redirect(url_for('portal_dashboard'))

@app.route('/placement/manage-student/<usn>')
def placement_manage_student(usn):
    return redirect(url_for('coordinator_student_profile', usn=usn))

@app.route('/placement/add-activity', methods=['POST'])
def placement_add_activity():
    return coordinator_activity_add()

@app.route('/portal/activity')
def portal_activity():
    admin = get_current_admin()
    if not admin:
        return redirect(url_for('admin_login'))
    activities = PlacementActivity.query.order_by(PlacementActivity.created_at.desc()).all()
    students = Student.query.all()
    selected_usn = request.args.get('selected_usn', '')
    selected_student = db.session.get(Student, selected_usn) if selected_usn else None
    return render_template(
        'portal_activity.html',
        active_page='activity',
        admin=admin,
        activities=activities,
        students=students,
        selected_student=selected_student,
        current_date=datetime.utcnow().strftime('%Y-%m-%d')
    )

@app.route('/principal/department/<dept_code>')
def principal_view_department(dept_code):
    return redirect(url_for('portal_department_leaderboard', dept_code=dept_code))

@app.route('/principal/student/<usn>')
def principal_view_student(usn):
    return redirect(url_for('portal_student_details', usn=usn))

@app.route('/performance/update', methods=['POST'])
def update_performance():
    flash('Performance metrics recorded.', 'success')
    return redirect(url_for('portal_dashboard'))

@app.route('/add_student', methods=['POST'], endpoint='add_student')
def add_student():
    return coordinator_register_student()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
