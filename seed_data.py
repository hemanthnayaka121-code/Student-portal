from app import app, db
from models import Department, Admin, Student, PerformanceRecord, RemedialResource, PlacementActivity, AuditLog, PlacementCoordinator, PlacementOfficer
from datetime import datetime

def seed_data():
    with app.app_context():
        # Recreate tables to reflect updated schema
        db.drop_all()
        db.create_all()

        print("Seeding MIT Placement Portal (10 Departments, Roles, Officers, Coordinators)...")
        
        # 10 Departments with standardized codes and HOD profile info
        dept_definitions = [
            ("CSE", "Computer Science and Engineering", "Dr. Ramesh Kumar", "HOD_CSE_01", "ramesh.cse@mitmysore.in", "+91 98450 11001"),
            ("CE", "Computer Engineering", "Dr. Rajesh Deshmukh", "HOD_CE_01", "rajesh.ce@mitmysore.in", "+91 98450 11002"),
            ("AI", "Artificial Intelligence", "Dr. Priya Sharma", "HOD_AI_01", "priya.ai@mitmysore.in", "+91 98450 11003"),
            ("CSD", "Computer Science and Data Science", "Dr. Harish Hegde", "HOD_CSD_01", "harish.csd@mitmysore.in", "+91 98450 11004"),
            ("CSML", "Computer Science and Machine Learning", "Dr. Sandeep Verma", "HOD_CSML_01", "sandeep.csml@mitmysore.in", "+91 98450 11005"),
            ("ISE", "Information Science and Engineering", "Dr. Sunitha M.", "HOD_ISE_01", "sunitha.ise@mitmysore.in", "+91 98450 11006"),
            ("ECE", "Electronics and Communication Engineering", "Dr. Venkatesh Rao", "HOD_ECE_01", "venkatesh.ece@mitmysore.in", "+91 98450 11007"),
            ("IOT", "Internet of Things", "Dr. Manjunath Bhat", "HOD_IOT_01", "manjunath.iot@mitmysore.in", "+91 98450 11008"),
            ("CIVIL", "Civil Engineering", "Dr. Anand Swamy", "HOD_CIVIL_01", "anand.civil@mitmysore.in", "+91 98450 11009"),
            ("MECH", "Mechanical Engineering", "Dr. Praveen Gowda", "HOD_MECH_01", "praveen.mech@mitmysore.in", "+91 98450 11010")
        ]

        depts = {}
        for code, name, h_name, h_id, h_email, h_phone in dept_definitions:
            dept = Department(
                code=code,
                name=name,
                hod_name=h_name,
                hod_id=h_id,
                hod_email=h_email,
                hod_phone=h_phone
            )
            db.session.add(dept)
            depts[code] = dept
        db.session.commit()

        # 1. Main MIT Placement Portal Login (Mit_placement / Mit@123)
        mit_admin = Admin(username="Mit_placement", role="PLACEMENT_ADMIN", department_id=None)
        mit_admin.set_password("Mit@123")

        # 2. Placement Coordinator Account (placement_coordinator / PC@123)
        coordinator_admin = Admin(username="placement_coordinator", role="PLACEMENT_COORDINATOR", department_id=None)
        coordinator_admin.set_password("PC@123")

        admins = [mit_admin, coordinator_admin]

        # 3. HOD Accounts for each department (username: hod_<code.lower()>, password: <CODE>@123)
        for code, dept in depts.items():
            admin_user = Admin(username=f"hod_{code.lower()}", role="HOD", department_id=dept.id)
            admin_user.set_password(f"{code}@123")
            admins.append(admin_user)
        db.session.add_all(admins)
        db.session.commit()

        # 5. Placement Coordinators for each Department
        coordinators_data = [
            ("Prof. Sneha Jain", "CSE", "sneha.coord@mitmysore.in", "+91 98451 22001", "Microsoft, Amazon, Infosys", 120),
            ("Prof. Vijay K.", "CE", "vijay.coord@mitmysore.in", "+91 98451 22002", "Texas Instruments, Intel", 65),
            ("Prof. Abhishek Shenoy", "AI", "abhishek.coord@mitmysore.in", "+91 98451 22003", "NVIDIA, Adobe, Google", 80),
            ("Prof. Deepa Nayak", "CSD", "deepa.coord@mitmysore.in", "+91 98451 22004", "Morgan Stanley, Databricks", 75),
            ("Prof. Rohit Kulkarni", "CSML", "rohit.coord@mitmysore.in", "+91 98451 22005", "Qualcomm, MathWorks", 70),
            ("Prof. Anitha R.", "ISE", "anitha.coord@mitmysore.in", "+91 98451 22006", "Cisco, SAP Labs, TCS", 100),
            ("Prof. Suresh Babu", "ECE", "suresh.coord@mitmysore.in", "+91 98451 22007", "Intel, Qualcomm, Cadence", 90),
            ("Prof. Karthik N.", "IOT", "karthik.coord@mitmysore.in", "+91 98451 22008", "Bosch, Schneider Electric", 55),
            ("Prof. Girish M.", "CIVIL", "girish.coord@mitmysore.in", "+91 98451 22009", "L&T Construction, Tata Projects", 60),
            ("Prof. Mahesh Patil", "MECH", "mahesh.coord@mitmysore.in", "+91 98451 22010", "Mercedes-Benz R&D, Tata Motors", 85)
        ]

        for c_name, c_code, c_email, c_phone, c_comps, c_std in coordinators_data:
            coord = PlacementCoordinator(
                name=c_name,
                department_id=depts[c_code].id,
                email=c_email,
                phone=c_phone,
                companies_coordinated=c_comps,
                students_handled=c_std
            )
            db.session.add(coord)

        # 6. Central Placement Officers
        officers_data = [
            ("Dr. R. Manjunatha", "Head - Training & Placement", "tpo.head@mitmysore.in", "+91 98450 99001", "Microsoft, Amazon, Cisco, Google, TCS", 32, 280),
            ("Mr. Chethan Kumar", "Senior Placement Officer", "chethan.tpo@mitmysore.in", "+91 98450 99002", "SAP Labs, Oracle, Infosys, Accenture", 24, 195),
            ("Ms. Bhavya Shree", "Corporate Relations & Internship Lead", "bhavya.cr@mitmysore.in", "+91 98450 99003", "Morgan Stanley, Qualcomm, NVIDIA, Bosch", 18, 140)
        ]

        for o_name, o_role, o_email, o_phone, o_comps, o_drives, o_placed in officers_data:
            officer = PlacementOfficer(
                name=o_name,
                role_title=o_role,
                email=o_email,
                phone=o_phone,
                companies_handled=o_comps,
                drives_conducted=o_drives,
                students_placed_count=o_placed
            )
            db.session.add(officer)
        db.session.commit()

        # Seed students with rich profile, academic, and placement metrics
        students_data = [
            # ISE Students
            {
                "dept": "ISE", "usn": "4MH24IS001", "name": "Alice Sharma", "mobile": "9876543210", "email": "alice.is@mitm.ac.in",
                "sem": 8, "cgpa": 9.35, "att": 92.0, "acad_score": 92.0,
                "skills": "Python, Java, React, Docker, SQL", "prog": "Python, Java, JavaScript",
                "tech": "Distributed Systems, React, Docker, PostgreSQL", "certs": "AWS Certified Solutions Architect, LeetCode Top 5%",
                "projects": "Microservices Placement Platform, Real-time Fraud Detection Engine",
                "attended": 6, "selected": 3, "offers": 3, "highest": 14.5, "avg": 11.2, "status": "Placed",
                "apt": 92.0, "gd": True, "hr": True, "c": 95.0, "java": 92.0, "dsa": 90.0, "tech_score": 94.0, "hr_score": 95.0
            },
            {
                "dept": "ISE", "usn": "4MH24IS002", "name": "Bob Verma", "mobile": "8765432109", "email": "bob.is@mitm.ac.in",
                "sem": 8, "cgpa": 8.40, "att": 86.5, "acad_score": 84.0,
                "skills": "Java, Spring Boot, MySQL, REST APIs", "prog": "Java, C++, SQL",
                "tech": "Spring Boot, Hibernate, MySQL, Docker", "certs": "Oracle Certified Java Associate, Coursera Backend Specialization",
                "projects": "Enterprise Inventory Management, Campus Hostel Room Booking Portal",
                "attended": 5, "selected": 2, "offers": 2, "highest": 10.0, "avg": 8.5, "status": "Placed",
                "apt": 84.0, "gd": True, "hr": True, "c": 86.0, "java": 88.0, "dsa": 82.0, "tech_score": 86.0, "hr_score": 88.0
            },
            {
                "dept": "ISE", "usn": "4MH24IS003", "name": "Charlie Patel", "mobile": "7654321098", "email": "charlie.is@mitm.ac.in",
                "sem": 8, "cgpa": 7.90, "att": 82.0, "acad_score": 78.0,
                "skills": "C++, Python, DSA, SQLite", "prog": "C++, Python, C",
                "tech": "Data Structures, Algorithms, Linux, SQLite", "certs": "NPTEL Algorithms Master, HackerRank 5-Star Problem Solving",
                "projects": "Campus Graph Shortest-Path Router, Memory-Efficient Cache Simulator",
                "attended": 4, "selected": 2, "offers": 2, "highest": 8.0, "avg": 7.2, "status": "Placed",
                "apt": 78.0, "gd": True, "hr": True, "c": 82.0, "java": 76.0, "dsa": 80.0, "tech_score": 80.0, "hr_score": 82.0
            },
            {
                "dept": "ISE", "usn": "4MH24IS004", "name": "Divya Reddy", "mobile": "7654321099", "email": "divya.is@mitm.ac.in",
                "sem": 8, "cgpa": 7.45, "att": 79.0, "acad_score": 74.0,
                "skills": "Python, Django, PostgreSQL, HTML/CSS", "prog": "Python, JavaScript, SQL",
                "tech": "Django, HTML5, CSS3, PostgreSQL", "certs": "Python for Everybody (Coursera)",
                "projects": "Student Attendance Management, Online Alumni Directory",
                "attended": 4, "selected": 1, "offers": 1, "highest": 6.5, "avg": 6.5, "status": "Placed",
                "apt": 72.0, "gd": True, "hr": False, "c": 70.0, "java": 74.0, "dsa": 68.0, "tech_score": 72.0, "hr_score": 68.0
            },
            {
                "dept": "ISE", "usn": "4MH24IS005", "name": "Eshan Nair", "mobile": "7654321097", "email": "eshan.is@mitm.ac.in",
                "sem": 8, "cgpa": 6.80, "att": 73.0, "acad_score": 68.0,
                "skills": "C, HTML, CSS, JavaScript Basics", "prog": "C, JavaScript",
                "tech": "Frontend Basics, Git, Web Design", "certs": "Responsive Web Design Certification",
                "projects": "Personal Portfolio Website, Basic Weather Forecast App",
                "attended": 3, "selected": 0, "offers": 0, "highest": 0.0, "avg": 0.0, "status": "In Progress",
                "apt": 48.0, "gd": False, "hr": False, "c": 52.0, "java": 46.0, "dsa": 42.0, "tech_score": 46.0, "hr_score": 45.0
            },

            # CSE Students
            {
                "dept": "CSE", "usn": "4MH24CS001", "name": "Rahul Dravid", "mobile": "6543210987", "email": "rahul.cs@mitm.ac.in",
                "sem": 8, "cgpa": 9.60, "att": 95.0, "acad_score": 96.0,
                "skills": "C++, Go, Kubernetes, System Design, DSA", "prog": "C++, Go, Python",
                "tech": "Kubernetes, Redis, Kafka, Distributed Architecture", "certs": "Certified Kubernetes Administrator (CKA), LeetCode Guardian",
                "projects": "High-Throughput Distributed Messaging Broker, Raft Consensus Engine",
                "attended": 5, "selected": 4, "offers": 4, "highest": 24.0, "avg": 18.5, "status": "Placed",
                "apt": 96.0, "gd": True, "hr": True, "c": 98.0, "java": 94.0, "dsa": 98.0, "tech_score": 96.0, "hr_score": 98.0
            },
            {
                "dept": "CSE", "usn": "4MH24CS002", "name": "Sneha Kulkarni", "mobile": "6543210986", "email": "sneha.cs@mitm.ac.in",
                "sem": 8, "cgpa": 8.95, "att": 90.0, "acad_score": 90.0,
                "skills": "Python, PyTorch, FastAPI, PostgreSQL", "prog": "Python, SQL, TypeScript",
                "tech": "FastAPI, PyTorch, Vector DBs, Cloud Run", "certs": "DeepLearning.AI Deep Learning Specialization",
                "projects": "Automated Code Review Assistant, Semantic Search Engine",
                "attended": 5, "selected": 3, "offers": 3, "highest": 16.0, "avg": 13.0, "status": "Placed",
                "apt": 90.0, "gd": True, "hr": True, "c": 88.0, "java": 90.0, "dsa": 88.0, "tech_score": 90.0, "hr_score": 92.0
            },
            {
                "dept": "CSE", "usn": "4MH24CS003", "name": "Rohit Sharma", "mobile": "6543210985", "email": "rohit.cs@mitm.ac.in",
                "sem": 8, "cgpa": 8.10, "att": 84.0, "acad_score": 81.0,
                "skills": "Java, React, Node.js, MongoDB", "prog": "Java, JavaScript, TypeScript",
                "tech": "MERN Stack, REST APIs, TailwindCSS", "certs": "Meta Front-End Developer Professional Certificate",
                "projects": "Real-time Collaborative Whiteboard, Online Code Judge",
                "attended": 4, "selected": 2, "offers": 2, "highest": 9.5, "avg": 8.0, "status": "Placed",
                "apt": 80.0, "gd": True, "hr": True, "c": 82.0, "java": 85.0, "dsa": 78.0, "tech_score": 82.0, "hr_score": 85.0
            },
            {
                "dept": "CSE", "usn": "4MH24CS004", "name": "Ananya Rao", "mobile": "6543210984", "email": "ananya.cs@mitm.ac.in",
                "sem": 8, "cgpa": 7.20, "att": 76.0, "acad_score": 72.0,
                "skills": "Python, SQL, Tableau, Pandas", "prog": "Python, SQL",
                "tech": "Data Analytics, Tableau, MySQL", "certs": "Google Data Analytics Professional Certificate",
                "projects": "E-Commerce Customer Churn Analysis, Sales Dashboard",
                "attended": 3, "selected": 1, "offers": 1, "highest": 5.5, "avg": 5.5, "status": "Placed",
                "apt": 66.0, "gd": True, "hr": False, "c": 65.0, "java": 64.0, "dsa": 62.0, "tech_score": 65.0, "hr_score": 64.0
            },

            # AI Students
            {
                "dept": "AI", "usn": "4MH24AI001", "name": "Arjun Menon", "mobile": "9123456780", "email": "arjun.ai@mitm.ac.in",
                "sem": 8, "cgpa": 9.40, "att": 93.0, "acad_score": 94.0,
                "skills": "Python, TensorFlow, NLP, LLMs, LangChain", "prog": "Python, C++, SQL",
                "tech": "PyTorch, Transformers, LangChain, Pinecone", "certs": "AWS Certified Machine Learning - Specialty",
                "projects": "Domain-Specific Healthcare Chatbot, RAG Document Intelligence",
                "attended": 4, "selected": 3, "offers": 3, "highest": 20.0, "avg": 15.0, "status": "Placed",
                "apt": 94.0, "gd": True, "hr": True, "c": 90.0, "java": 88.0, "dsa": 92.0, "tech_score": 95.0, "hr_score": 96.0
            },
            {
                "dept": "AI", "usn": "4MH24AI002", "name": "Meera Iyer", "mobile": "9123456781", "email": "meera.ai@mitm.ac.in",
                "sem": 8, "cgpa": 8.65, "att": 88.0, "acad_score": 86.0,
                "skills": "Python, OpenCV, Scikit-learn, Computer Vision", "prog": "Python, C++",
                "tech": "YOLOv8, OpenCV, Flask, Docker", "certs": "Udacity Computer Vision Nanodegree",
                "projects": "Autonomous Traffic Violation Detection, Face Recognition Attendance System",
                "attended": 4, "selected": 2, "offers": 2, "highest": 12.0, "avg": 9.5, "status": "Placed",
                "apt": 86.0, "gd": True, "hr": True, "c": 84.0, "java": 82.0, "dsa": 85.0, "tech_score": 88.0, "hr_score": 86.0
            },

            # CSD Students
            {
                "dept": "CSD", "usn": "4MH24DS001", "name": "Tanvi Hegde", "mobile": "9123456782", "email": "tanvi.ds@mitm.ac.in",
                "sem": 8, "cgpa": 9.15, "att": 91.0, "acad_score": 92.0,
                "skills": "Python, SQL, Apache Spark, PowerBI, Big Data", "prog": "Python, Scala, SQL",
                "tech": "PySpark, Databricks, PostgreSQL, Snowflake", "certs": "Databricks Certified Associate Developer",
                "projects": "Real-time Financial Fraud Pipeline, Clickstream Analytics",
                "attended": 5, "selected": 3, "offers": 3, "highest": 15.0, "avg": 11.5, "status": "Placed",
                "apt": 88.0, "gd": True, "hr": True, "c": 85.0, "java": 85.0, "dsa": 86.0, "tech_score": 88.0, "hr_score": 90.0
            },

            # CSML Students
            {
                "dept": "CSML", "usn": "4MH24ML001", "name": "Varun Joshi", "mobile": "9123456783", "email": "varun.ml@mitm.ac.in",
                "sem": 8, "cgpa": 9.25, "att": 92.0, "acad_score": 93.0,
                "skills": "Python, PyTorch, CUDA, MLOps, Docker", "prog": "Python, C++, CUDA",
                "tech": "MLflow, Kubeflow, PyTorch Lightning, TensorRT", "certs": "Google Cloud Professional ML Engineer",
                "projects": "Distributed Deep Learning Model Optimization, Edge AI Inference",
                "attended": 4, "selected": 3, "offers": 3, "highest": 17.5, "avg": 13.0, "status": "Placed",
                "apt": 90.0, "gd": True, "hr": True, "c": 90.0, "java": 86.0, "dsa": 90.0, "tech_score": 92.0, "hr_score": 92.0
            },

            # CE Students
            {
                "dept": "CE", "usn": "4MH24CE001", "name": "Pranav Deshmukh", "mobile": "9123456784", "email": "pranav.ce@mitm.ac.in",
                "sem": 8, "cgpa": 8.70, "att": 89.0, "acad_score": 87.0,
                "skills": "C++, Embedded C, RTOS, Computer Architecture", "prog": "C, C++, Assembly",
                "tech": "FreeRTOS, STM32 Microcontrollers, SPI, I2C", "certs": "ARM Embedded System Architecture",
                "projects": "Automotive ECU Controller, Real-time Sensor Fusion Hub",
                "attended": 4, "selected": 2, "offers": 2, "highest": 11.0, "avg": 9.0, "status": "Placed",
                "apt": 82.0, "gd": True, "hr": True, "c": 92.0, "java": 80.0, "dsa": 82.0, "tech_score": 86.0, "hr_score": 88.0
            },

            # ECE Students
            {
                "dept": "ECE", "usn": "4MH24EC001", "name": "Karthik Sundaram", "mobile": "9123456785", "email": "karthik.ec@mitm.ac.in",
                "sem": 8, "cgpa": 8.80, "att": 89.0, "acad_score": 88.0,
                "skills": "Verilog, VLSI, C, SystemVerilog, FPGA", "prog": "Verilog, C, Python",
                "tech": "Vivado, ModelSim, FPGA Implementation, Synopsys Tools", "certs": "Cadence Certified VLSI Design",
                "projects": "Pipelined 32-bit RISC-V Processor Core on FPGA, AXI4 Bus Interconnect",
                "attended": 4, "selected": 2, "offers": 2, "highest": 12.0, "avg": 9.5, "status": "Placed",
                "apt": 86.0, "gd": True, "hr": True, "c": 88.0, "java": 78.0, "dsa": 80.0, "tech_score": 88.0, "hr_score": 88.0
            },
            {
                "dept": "ECE", "usn": "4MH24EC002", "name": "Pooja Joshi", "mobile": "9123456786", "email": "pooja.ec@mitm.ac.in",
                "sem": 8, "cgpa": 7.70, "att": 82.0, "acad_score": 77.0,
                "skills": "MATLAB, Digital Signal Processing, Embedded C", "prog": "MATLAB, C, Python",
                "tech": "Simulink, DSP Processors, GNU Radio", "certs": "MATLAB Associate Certification",
                "projects": "5G OFDM Channel Estimation & Equalization, Wireless Acoustic Sensor",
                "attended": 3, "selected": 1, "offers": 1, "highest": 7.0, "avg": 7.0, "status": "Placed",
                "apt": 74.0, "gd": True, "hr": True, "c": 75.0, "java": 70.0, "dsa": 72.0, "tech_score": 75.0, "hr_score": 76.0
            },

            # IOT Students
            {
                "dept": "IOT", "usn": "4MH24IT001", "name": "Rakesh Bhat", "mobile": "9123456787", "email": "rakesh.iot@mitm.ac.in",
                "sem": 8, "cgpa": 8.50, "att": 87.0, "acad_score": 85.0,
                "skills": "Embedded C, Python, MQTT, AWS IoT Core, ESP32", "prog": "C, Python, JavaScript",
                "tech": "AWS IoT, ESP32, LoRaWAN, Node-RED", "certs": "AWS Certified IoT Specialist",
                "projects": "Smart Campus Environmental Monitoring, Industrial Asset Tracker",
                "attended": 4, "selected": 2, "offers": 2, "highest": 10.5, "avg": 8.5, "status": "Placed",
                "apt": 82.0, "gd": True, "hr": True, "c": 88.0, "java": 78.0, "dsa": 80.0, "tech_score": 84.0, "hr_score": 85.0
            },

            # CIVIL Students
            {
                "dept": "CIVIL", "usn": "4MH24CV001", "name": "Vinay Kumar", "mobile": "9123456788", "email": "vinay.cv@mitm.ac.in",
                "sem": 8, "cgpa": 8.40, "att": 88.0, "acad_score": 84.0,
                "skills": "AutoCAD, STAAD Pro, Revit, BIM, Project Management", "prog": "Python, MATLAB",
                "tech": "STAAD Pro, ETABS, Revit Structure, Primavera P6", "certs": "Autodesk Certified Professional - Revit Structure",
                "projects": "Seismic Analysis of Multi-Storey RCC Structure, Green Concrete Mix Design",
                "attended": 4, "selected": 2, "offers": 2, "highest": 7.5, "avg": 6.2, "status": "Placed",
                "apt": 80.0, "gd": True, "hr": True, "c": 72.0, "java": 68.0, "dsa": 70.0, "tech_score": 82.0, "hr_score": 84.0
            },

            # MECH Students
            {
                "dept": "MECH", "usn": "4MH24ME001", "name": "Vikram Rathore", "mobile": "9123456789", "email": "vikram.me@mitm.ac.in",
                "sem": 8, "cgpa": 8.55, "att": 87.5, "acad_score": 85.0,
                "skills": "SolidWorks, ANSYS, GD&T, Thermal Simulation, Python", "prog": "Python, MATLAB",
                "tech": "ANSYS Fluent, SolidWorks Flow Simulation, CNC Programming", "certs": "CSWA - Certified SOLIDWORKS Associate",
                "projects": "Electric Vehicle Battery Liquid Cooling Jacket Design, Aerodynamic Wing Optimization",
                "attended": 4, "selected": 2, "offers": 2, "highest": 8.5, "avg": 7.0, "status": "Placed",
                "apt": 82.0, "gd": True, "hr": True, "c": 78.0, "java": 72.0, "dsa": 74.0, "tech_score": 84.0, "hr_score": 86.0
            },
            {
                "dept": "MECH", "usn": "4MH24ME002", "name": "Suresh Gowda", "mobile": "9123456790", "email": "suresh.me@mitm.ac.in",
                "sem": 8, "cgpa": 7.30, "att": 81.0, "acad_score": 73.0,
                "skills": "CATIA, AutoCAD, Robotics, Manufacturing Processes", "prog": "C, Python Basics",
                "tech": "CATIA V5, Mastercam, Robotics Kinematics", "certs": "Mastercam CAD/CAM Certification",
                "projects": "Pneumatic Quad-Gripper Pick-and-Place Robot, Gearbox Failure Analysis",
                "attended": 3, "selected": 1, "offers": 1, "highest": 5.0, "avg": 5.0, "status": "Placed",
                "apt": 70.0, "gd": True, "hr": True, "c": 65.0, "java": 60.0, "dsa": 62.0, "tech_score": 72.0, "hr_score": 75.0
            }
        ]

        for s_data in students_data:
            dept = depts[s_data["dept"]]
            student = Student(
                usn=s_data["usn"],
                name=s_data["name"],
                mobile_number=s_data["mobile"],
                email=s_data["email"],
                department_id=dept.id,
                semester=s_data["sem"],
                cgpa=s_data["cgpa"],
                attendance=s_data["att"],
                academic_score=s_data["acad_score"],
                skills=s_data["skills"],
                programming_languages=s_data["prog"],
                technical_skills=s_data["tech"],
                certifications=s_data["certs"],
                projects=s_data["projects"],
                companies_attended=s_data["attended"],
                companies_selected=s_data["selected"],
                offers_count=s_data["offers"],
                highest_package=s_data["highest"],
                average_package=s_data["avg"],
                placement_status=s_data["status"],
                placement_approval_status="APPROVED",
                approved_by=f"hod_{s_data['dept'].lower()}",
                approved_at=datetime.utcnow(),
                resume="Resume_Official.pdf"
            )
            db.session.add(student)
            
            perf = PerformanceRecord(
                student_usn=s_data["usn"],
                aptitude_score=s_data["apt"],
                gd_status=s_data["gd"],
                hr_status=s_data["hr"],
                coding_c_score=s_data["c"],
                coding_java_score=s_data["java"],
                coding_dsa_score=s_data["dsa"],
                technical_interview_score=s_data["tech_score"],
                hr_score=s_data["hr_score"]
            )
            db.session.add(perf)

        # 2 Sample Students Awaiting HOD Approval (Stage 1 of the workflow)
        pending_students = [
            Student(
                usn="4MH24IS033",
                name="Kavya Murthy",
                mobile_number="9845990033",
                email="kavya.is@mitm.ac.in",
                department_id=depts["ISE"].id,
                semester=8,
                cgpa=8.85,
                attendance=91.0,
                skills="Python, React, AWS, Node.js",
                placement_status="NOT_STARTED",
                placement_approval_status="PENDING",
                resume="Kavya_Resume.pdf"
            ),
            Student(
                usn="4MH24CS033",
                name="Vikram Sen",
                mobile_number="9845990034",
                email="vikram.cs@mitm.ac.in",
                department_id=depts["CSE"].id,
                semester=8,
                cgpa=8.50,
                attendance=87.0,
                skills="Java, Spring Boot, Microservices, Kubernetes",
                placement_status="NOT_STARTED",
                placement_approval_status="PENDING",
                resume="Vikram_Resume.pdf"
            ),
            Student(
                usn="4MH24IS099",
                name="Sumanth Rao",
                mobile_number="9845990099",
                email="sumanth.is@mitm.ac.in",
                department_id=depts["ISE"].id,
                semester=8,
                cgpa=6.10,
                attendance=68.0,
                skills="Basics of C, HTML",
                placement_status="NOT_STARTED",
                placement_approval_status="REJECTED",
                rejected_by="hod_ise",
                rejected_at=datetime.utcnow(),
                rejection_reason="Student has not met the department's placement eligibility criteria (CGPA < 6.5 & attendance < 75%).",
                resume="Sumanth_Resume.pdf"
            )
        ]
        db.session.add_all(pending_students)
        for ps in pending_students:
            db.session.add(PerformanceRecord(student_usn=ps.usn, aptitude_score=80.0, coding_c_score=82.0, coding_java_score=85.0, coding_dsa_score=80.0, technical_interview_score=82.0, hr_score=85.0))

        # Remedial Resources
        r1 = RemedialResource(topic="Aptitude", video_url="https://youtube.com/watch?v=aptitude", faculty_contact="Prof. Ramesh (ramesh@mitmysore.in)", course_recommendation="Quantitative Aptitude Masterclass by R.S. Aggarwal")
        r2 = RemedialResource(topic="GD", video_url="https://youtube.com/watch?v=gd", faculty_contact="Prof. Sunitha (sunitha@mitmysore.in)", course_recommendation="Effective Communication & Leadership Skills")
        r3 = RemedialResource(topic="HR", video_url="https://youtube.com/watch?v=hr", faculty_contact="Placement Officer (placement@mitmysore.in)", course_recommendation="Behavioral & HR Interview Ace Guide")
        r4 = RemedialResource(topic="DSA", video_url="https://youtube.com/watch?v=dsa", faculty_contact="Prof. Manjunath (manjunath@mitmysore.in)", course_recommendation="Data Structures and Algorithms LeetCode Intensive")
        
        db.session.add_all([r1, r2, r3, r4])

        # Seed Placement Activities and Audit History for Placed Students
        activities_data = [
            ("4MH24IS001", "Cisco Systems", "Software Engineer", "2026-09-18", 14.5, "Selected", 92.0, 95.0, 94.0, 95.0),
            ("4MH24IS001", "Infosys", "Specialist Programmer", "2026-09-02", 9.5, "Selected", 90.0, 92.0, 90.0, 92.0),
            ("4MH24IS002", "SAP Labs", "Associate Developer", "2026-09-22", 10.0, "Selected", 84.0, 86.0, 86.0, 88.0),
            ("4MH24IS003", "TCS Digital", "Systems Engineer", "2026-09-14", 8.0, "Selected", 78.0, 82.0, 80.0, 82.0),
            ("4MH24IS004", "Accenture", "Associate Software Engineer", "2026-09-28", 6.5, "Selected", 72.0, 70.0, 72.0, 68.0),
            ("4MH24CS001", "Microsoft", "Software Development Engineer (SDE-1)", "2026-09-15", 24.0, "Selected", 96.0, 98.0, 96.0, 98.0),
            ("4MH24CS001", "Amazon", "SDE-1", "2026-09-05", 19.5, "Selected", 94.0, 96.0, 95.0, 95.0),
            ("4MH24CS002", "Atlassian", "Software Engineer", "2026-09-20", 16.0, "Selected", 90.0, 88.0, 90.0, 92.0),
            ("4MH24CS003", "Oracle", "Server Technologies Analyst", "2026-09-25", 9.5, "Selected", 80.0, 82.0, 82.0, 85.0),
            ("4MH24CS004", "Deloitte", "Technology Analyst", "2026-09-30", 5.5, "Selected", 66.0, 65.0, 65.0, 64.0),
            ("4MH24AI001", "NVIDIA", "AI Research Engineer", "2026-09-12", 20.0, "Selected", 94.0, 90.0, 95.0, 96.0),
            ("4MH24AI002", "Adobe", "Computer Vision Engineer", "2026-09-24", 12.0, "Selected", 86.0, 84.0, 88.0, 86.0),
            ("4MH24DS001", "Morgan Stanley", "Data Platform Engineer", "2026-09-19", 15.0, "Selected", 88.0, 85.0, 88.0, 90.0),
            ("4MH24ML001", "Qualcomm", "Machine Learning Engineer", "2026-09-16", 17.5, "Selected", 90.0, 90.0, 92.0, 92.0),
            ("4MH24CE001", "Texas Instruments", "Embedded Firmware Engineer", "2026-09-21", 11.0, "Selected", 82.0, 92.0, 86.0, 88.0),
            ("4MH24EC001", "Intel", "Silicon Architecture Engineer", "2026-09-17", 12.0, "Selected", 86.0, 88.0, 88.0, 88.0),
            ("4MH24EC002", "Qualcomm", "Associate Hardware Engineer", "2026-09-26", 7.0, "Selected", 74.0, 75.0, 75.0, 76.0),
            ("4MH24IT001", "Bosch Global", "IoT Firmware Specialist", "2026-09-23", 10.5, "Selected", 82.0, 88.0, 84.0, 85.0),
            ("4MH24CV001", "L&T Construction", "Structural Planning Engineer", "2026-09-27", 7.5, "Selected", 80.0, 72.0, 82.0, 84.0),
            ("4MH24ME001", "Mercedes-Benz R&D", "CAE Thermal Simulation Engineer", "2026-09-18", 8.5, "Selected", 82.0, 78.0, 84.0, 86.0),
            ("4MH24ME002", "Tata Technologies", "Robotics & Automation Trainee", "2026-09-29", 5.0, "Selected", 70.0, 65.0, 72.0, 75.0),
        ]

        for usn, comp, role, d_date, pkg, stat, apt, cod, tech, hr in activities_data:
            act = PlacementActivity(
                student_usn=usn,
                company_name=comp,
                job_role=role,
                drive_date=d_date,
                package=pkg,
                status=stat,
                aptitude_score=apt,
                coding_score=cod,
                technical_score=tech,
                hr_score=hr,
                changed_by="placement_admin"
            )
            db.session.add(act)
            
            audit = AuditLog(
                student_usn=usn,
                changed_by="placement_admin",
                action="Registered Offer",
                company_name=comp,
                old_package=0.0,
                new_package=pkg,
                details=f"Selected for {role} at ₹{pkg} LPA."
            )
            db.session.add(audit)

        db.session.commit()
        print("Data seeded successfully for all 10 departments, Roles, and Activities!")

if __name__ == '__main__':
    seed_data()

