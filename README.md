# MIT Mysore — Student Placement Portal & AI Training Application

A comprehensive Student Placement Performance & AI Training Platform built with Python Flask, SQLite/SQLAlchemy, and modern web architecture. Features intelligent diagnostic benchmarking, real-time speech-powered AI mock interviews, interactive diagnostic quizzes, curated YouTube lesson integrations, and Firebase authentication.

---

## 🌟 Key Features

### 1. Student Placement Performance & Diagnostic Engine (Module 2)
- **12 Dedicated Student Portal Sections**: Dashboard, Placement Performance, Strengths & Weaknesses Analysis, Recommended Learning, YouTube Lessons, Practice Quizzes, AI Mock Interview, Interview Reports, Placement History, Profile, Account Security, and Logout.
- **Diagnostic Benchmarking**: Compares recorded aptitude, coding (C, Java, DSA), technical interview, and HR round marks against college hiring benchmarks ($\ge 70\%$).
- **Weakness Detection & Action Plans**: Identifies weakest concepts and automatically prescribes targeted remedial masterclasses.

### 2. Conversational AI Mock Interviews
- **Voice & Text Dual-Mode**: Real-time Web Speech Recognition and Speech Synthesis.
- **Hands-Free Silence Detection**: Speak answers naturally; a 2-second pause triggers automated evaluation without clicking buttons.
- **Code Mode**: Expandable monospace editor with syntax-ready layout for coding and DSA rounds.
- **Comprehensive Rubric Reports**: Scores technical accuracy, completeness, structured communication, strengths, and weaknesses.

### 3. Interactive Practice Quiz Bank
- 4 assessment tracks: Aptitude, Coding & DSA, Technical Core (OOP, DBMS, OS), and HR Situational.
- Timed and untimed modes with immediate feedback, detailed explanations, and `localStorage` answer preservation during network interruptions.

### 4. Curated YouTube Video Masterclasses
- Integrated YouTube learning catalog with domain-specific placement lessons, thumbnail previews, embedded 16:9 playback, and progress completion tracking.

### 5. Unified Portal Architecture
- Consistent monochrome design system across all roles (Placement Admin, Coordinator, HOD, and Student).
- Comprehensive 12-section sidebar navigation, dynamic breadcrumbs, and responsive data visualization powered by Plotly.js.

### 6. Institutional Role-Based Access Control (RBAC)
- **Placement Admin / Placement Officers**: Institution-wide placement control and analytics.
- **Placement Coordinators**: Record official student marks, packages, and drive attendance.
- **Heads of Department (HODs)**: Verify and approve student placement eligibility.
- **Strict Data Isolation**: Practice quizzes and AI mock interview scores are stored in dedicated training tables and strictly isolated from official coordinator records.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, Flask
- **Database**: SQLite / PostgreSQL via Flask-SQLAlchemy
- **Frontend**: Clean monochrome HTML5, CSS3, JavaScript (Vanilla ES6)
- **Authentication**: Firebase Authentication + Server-side session verification
- **AI & Speech**: Web Speech API, Text-to-Speech (TTS), Automated NLP evaluation heuristics
- **Visuals & Charts**: Plotly.js responsive graphs

---

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/hemanthnayaka121-code/Student-portal-and-training-application.git
cd Student-portal-and-training-application
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
