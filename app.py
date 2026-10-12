from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
from models import db, Department, Admin, Student, PerformanceRecord, RemedialResource, PlacementActivity, AuditLog, PlacementCoordinator, PlacementOfficer
import os
import json
import time
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey_mitm_secure_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=45)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

db.init_app(app)

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

@app.after_request
def add_security_headers(response):
    # Prevent caching of protected pages to protect sensitive student records after logout
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response

def get_current_admin():
    if 'admin_id' not in session:
        return None
    return db.session.get(Admin, session['admin_id'])

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
@app.route('/principal/dashboard')
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
def coordinator_register_student():
    if not session.get('coordinator_authenticated') and session.get('role') != 'PLACEMENT_COORDINATOR':
        return "403 Forbidden: Only authenticated Placement Coordinators are permitted to add students for placement.", 403

    name = request.form.get('name', '').strip()
    usn = request.form.get('usn', '').strip().upper()
    dept_id = request.form.get('department_id')
    semester = int(request.form.get('semester', 8))
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    cgpa = float(request.form.get('cgpa', 8.0))
    skills = request.form.get('skills', '').strip()
    resume = request.form.get('resume', 'Resume_Uploaded.pdf').strip()

    if not usn or not name or not dept_id:
        flash('Student Name, USN, and Department are required.', 'error')
        return redirect(url_for('coordinator_dashboard'))

    existing = Student.query.get(usn)
    if existing:
        flash(f'Student with USN {usn} already exists in the portal.', 'error')
        return redirect(url_for('coordinator_dashboard'))

    dept = Department.query.get_or_404(int(dept_id))

    # Student starts with PENDING status. Respective HOD must review and approve.
    new_student = Student(
        usn=usn,
        name=name,
        mobile_number=phone if phone else f"98450{usn[-5:]}",
        email=email if email else f"{usn.lower()}@mitm.ac.in",
        department_id=dept.id,
        semester=semester,
        cgpa=cgpa,
        skills=skills,
        resume=resume if resume else "Resume_Uploaded.pdf",
        placement_approval_status='PENDING',
        placement_status='NOT_STARTED',
        attendance=85.0,
        academic_score=round(cgpa * 9.5, 1)
    )
    db.session.add(new_student)

    # Initial performance record
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

    audit = AuditLog(
        student_usn=usn,
        changed_by=session.get('coordinator_username', 'placement_coordinator'),
        action="Registered for Placement",
        details=f"Created with status PENDING and automatically routed to {dept.name} HOD approval queue."
    )
    db.session.add(audit)
    db.session.commit()

    flash(f"Student {name} ({usn}) has been registered for placement and routed to {dept.name} ({dept.code}) HOD for approval (Status: PENDING).", 'success')
    return redirect(url_for('coordinator_dashboard'))

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
@app.route('/portal/activity/add', methods=['POST'])
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

# ----------------- 7. PRESERVED STUDENT PORTAL -----------------

@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        mobile = request.form['mobile'].strip()
        student = Student.query.filter_by(mobile_number=mobile).first()
        if student:
            session['student_usn'] = student.usn
            return redirect(url_for('student_dashboard'))
        flash('Invalid mobile number. Not found in records.', 'error')
    return render_template('student_login.html')

@app.route('/student/logout')
def student_logout():
    session.pop('student_usn', None)
    return redirect(url_for('index'))

@app.route('/student/dashboard')
def student_dashboard():
    if 'student_usn' not in session:
        return redirect(url_for('student_login'))
    
    student = Student.query.get(session['student_usn'])
    perf = student.performance
    
    weaknesses = []
    resources = []
    
    if perf:
        if perf.aptitude_score < 50:
            weaknesses.append("Aptitude")
        if not perf.gd_status:
            weaknesses.append("Group Discussion")
        if not perf.hr_status:
            weaknesses.append("HR Round")
        if perf.coding_c_score < 50 or perf.coding_java_score < 50 or perf.coding_dsa_score < 50:
            weaknesses.append("Coding / DSA")
            
        for w in weaknesses:
            topic_key = "DSA" if "Coding" in w else ("GD" if "Group" in w else ("HR" if "HR" in w else "Aptitude"))
            res = RemedialResource.query.filter_by(topic=topic_key).first()
            if res:
                resources.append(res)
                
    return render_template('student_dashboard.html', student=student, perf=perf, weaknesses=weaknesses, resources=resources)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
