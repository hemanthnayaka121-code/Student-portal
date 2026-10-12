# College Placement Tracking and Training Dashboard

An enterprise-grade, role-based College Placement & Training Management System built with Python Flask and SQLite / SQLAlchemy. Designed for educational institutions to monitor student readiness, manage placement drives, provide targeted remedial learning resources, and deliver actionable analytics across departments.

---

## 🌟 Key Features

### 1. Multi-Tier Role-Based Access Control (RBAC)
- **Placement Admin / Placement Officers**: Oversee college-wide placement drives, manage student records, coordinate company visits, review audit logs, and analyze institution-wide placement trends.
- **Placement Coordinators**: Track branch-specific candidates, monitor interview readiness, filter eligible students, and organize departmental drives.
- **Heads of Department (HODs)**: Monitor departmental student progress, batch statistics, identify low-performing students, and assign targeted interventions.
- **Principal / Management**: High-level institutional dashboard, inter-departmental leaderboards, and comparative placement conversion analytics.
- **Students**: Personal dashboard displaying assessment scores (Aptitude, GD, HR, Coding/DSA), eligibility status, and tailored remedial learning recommendations.

### 2. Comprehensive Performance Tracking
- **Aptitude Assessments**: Quantitative, logical, and verbal metrics.
- **Soft Skills**: Group Discussion (GD) and HR interview clearance tracking.
- **Technical Competencies**: Dedicated scoring across C, Java, and Data Structures & Algorithms (DSA).
- **Automated Weakness Detection**: Automatically identifies areas below benchmark thresholds and pairs students with remedial resources.

### 3. Training & Remedial Support
- Curated resource library for Aptitude, DSA, GD, and HR preparation.
- Direct recommendations mapped to student-specific weak areas.

### 4. Enterprise Security & Audit
- Secure password hashing using Werkzeug.
- In-memory rate limiting against brute-force login attempts.
- Security response headers (`Cache-Control`, `X-Content-Type-Options`, `X-Frame-Options`).
- Centralized audit trail for administrative actions.

---

## 🛠️ Tech Stack

- **Backend**: Python 3, Flask
- **ORM & Database**: Flask-SQLAlchemy, SQLite
- **Frontend**: Jinja2 Templates, HTML5, CSS3, JavaScript
- **Security**: Werkzeug Security Helpers, Session Management

---

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/hemanthnayaka121-code/college-placement-tracking-and-training-dashboard.git
cd college-placement-tracking-and-training-dashboard
```

### 2. Set Up a Virtual Environment (Recommended)
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize Database & Seed Sample Data
```bash
python seed_data.py
```

### 5. Run the Application
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🔑 Default Demo Accounts

| Role | Username / Identifier | Password | Access Details |
| :--- | :--- | :--- | :--- |
| **Placement Admin** | `Mit_placement` | `Mit@123` | Institutional placement control |
| **Placement Coordinator** | `placement_coordinator` | `PC@123` | Training & coordination |
| **HOD (CSE)** | `hod_cse` | `CSE@123` | Computer Science Department |
| **HOD (ISE)** | `hod_ise` | `ISE@123` | Information Science Department |
| **HOD (AI)** | `hod_ai` | `AI@123` | Artificial Intelligence Department |
| **Student** | USN (e.g. `4MH21CS001`) | DOB / Default | Individual student portal |

*(Additional HOD credentials follow the pattern `hod_<dept_code>` and `<DEPT_CODE>@123` for CE, CSD, CSML, ECE, IOT, CIVIL, MECH).*

---

## 📂 Project Structure

```
├── app.py                  # Core Flask application, routing, and controller logic
├── models.py               # Database schemas (Students, Departments, Logs, etc.)
├── seed_data.py            # Database initialization and sample data generator
├── requirements.txt        # Python package dependencies
├── .gitignore              # Files excluded from version control
├── static/
│   ├── css/style.css       # Core stylesheets
│   └── images/             # Visual assets and logos
└── templates/              # Jinja2 HTML templates for each portal & role
```

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
