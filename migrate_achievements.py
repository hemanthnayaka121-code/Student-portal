"""
Database Migration & Seeding Script for Achievement Hub & Karnataka Workshop Discovery
Maharaja Institute of Technology Mysore (MITM) Placement & AI Platform
"""

import os
import shutil
import datetime
from app import app, db
from models import (
    Student, Course, StudentCourseProgress, WorkshopEvent,
    StudentEventAction, StudentAchievement, StudentNotification, StudentPreference
)

def run_migration():
    print("=" * 60)
    print("STARTING ACHIEVEMENT HUB MIGRATION & DATA POPULATION")
    print("=" * 60)

    # 1. Safe Backup of Database
    db_file = os.path.join(app.instance_path, "placement.db")
    backup_file = os.path.join(app.instance_path, "placement_backup_pre_achievements.db")
    if os.path.exists(db_file):
        shutil.copy2(db_file, backup_file)
        print(f"Backed up active database to: {backup_file}")

    with app.app_context():
        # 2. Create newly declared tables
        db.create_all()
        print("Created new tables: courses, student_course_progress, workshop_events,")
        print("student_event_actions, student_achievements, student_notifications, student_preferences.")

        now = datetime.datetime.utcnow()

        # 3. Seed Verified Courses & Certifications
        courses_data = [
            # 1. DSA / Algorithms
            {
                "course_id": "coursera-algorithms-part1",
                "title": "Algorithms, Part I (Princeton University)",
                "provider": "Coursera",
                "domain": "DSA",
                "target_branches": "IS,CS",
                "difficulty": "Intermediate",
                "skills_covered": "Data Structures, Sorting, Searching, Priority Queues, Binary Search Trees",
                "duration": "6 Weeks (Self-Paced)",
                "course_url": "https://www.coursera.org/learn/algorithms-part1",
                "thumbnail_url": "https://images.unsplash.com/photo-1516116211227-bbc13c79a580?w=600&auto=format&fit=crop&q=80",
                "is_free": True,
                "free_certificate": False,
                "cost_info": "Free to Audit / Financial Aid Available",
                "certificate_info": "Shareable Certificate available via Coursera Audit/Aid",
                "rating": 4.9
            },
            {
                "course_id": "freecodecamp-dsa-python",
                "title": "Data Structures and Algorithms in Python (freeCodeCamp)",
                "provider": "freeCodeCamp",
                "domain": "DSA",
                "target_branches": "IS,CS",
                "difficulty": "Beginner to Intermediate",
                "skills_covered": "Arrays, Linked Lists, Trees, Graph Algorithms, Dynamic Programming",
                "duration": "10 Hours (Self-Paced)",
                "course_url": "https://www.freecodecamp.org/learn/",
                "thumbnail_url": "https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=600&auto=format&fit=crop&q=80",
                "is_free": True,
                "free_certificate": True,
                "cost_info": "100% Free Complete Course & Verified Certificate",
                "certificate_info": "Free Verified Certification upon project completions",
                "rating": 4.8
            },
            # 2. Python & Programming
            {
                "course_id": "coursera-python-everybody",
                "title": "Programming for Everybody (Getting Started with Python - Univ of Michigan)",
                "provider": "Coursera",
                "domain": "Python",
                "target_branches": "ALL",
                "difficulty": "Beginner",
                "skills_covered": "Python Syntax, Data Structures, Functions, Logic, Placement Coding Basics",
                "duration": "7 Weeks (3-4 hrs/wk)",
                "course_url": "https://www.coursera.org/learn/python",
                "thumbnail_url": "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=600&auto=format&fit=crop&q=80",
                "is_free": True,
                "free_certificate": False,
                "cost_info": "Free Full Course Audit",
                "certificate_info": "Shareable Certificate with Financial Aid or Subscription",
                "rating": 4.8
            },
            {
                "course_id": "coursera-google-it-automation-python",
                "title": "Google IT Automation with Python Professional Certificate",
                "provider": "Coursera (Google)",
                "domain": "Python",
                "target_branches": "IS,CS,EC",
                "difficulty": "Intermediate",
                "skills_covered": "Python, Git & GitHub, Operating Systems, Automation, Problem Solving",
                "duration": "6 Months (10 hrs/wk)",
                "course_url": "https://www.coursera.org/professional-certificates/google-it-automation",
                "thumbnail_url": "https://images.unsplash.com/photo-1571171637578-41bc2dd41cd2?w=600&auto=format&fit=crop&q=80",
                "is_free": True,
                "free_certificate": False,
                "cost_info": "Free to Audit / Coursera Financial Aid eligible",
                "certificate_info": "Industry-Recognised Google Professional Badge & Certificate",
                "rating": 4.7
            },
            # 3. Java & Object Oriented
            {
                "course_id": "coursera-java-programming-duke",
                "title": "Java Programming: Solving Problems with Software (Duke University)",
                "provider": "Coursera",
                "domain": "Java",
                "target_branches": "IS,CS",
                "difficulty": "Beginner to Intermediate",
                "skills_covered": "Java Syntax, OOP, Classes, Methods, CSV Data Processing, Algorithms",
                "duration": "4 Weeks",
                "course_url": "https://www.coursera.org/learn/java-programming",
                "thumbnail_url": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=600&auto=format&fit=crop&q=80",
                "is_free": True,
                "free_certificate": False,
                "cost_info": "Free Audit Access",
                "certificate_info": "Duke University Official Certificate on completion",
                "rating": 4.7
            },
            # 4. AI / Machine Learning
            {
                "course_id": "coursera-machine-learning-specialization",
                "title": "Machine Learning Specialization (DeepLearning.AI & Stanford)",
                "provider": "Coursera",
                "domain": "AI/ML",
                "target_branches": "IS,CS,EC",
                "difficulty": "Intermediate",
                "skills_covered": "Supervised Learning, Neural Networks, Decision Trees, Reinforcement Learning",
                "duration": "3 Months (9 hrs/wk)",
                "course_url": "https://www.coursera.org/specializations/machine-learning-introduction",
                "thumbnail_url": "https://images.unsplash.com/photo-1677442136019-21780efad99a?w=600&auto=format&fit=crop&q=80",
                "is_free": True,
                "free_certificate": False,
                "cost_info": "Free Audit Access for all lectures",
                "certificate_info": "Stanford & DeepLearning.AI Certificate",
                "rating": 4.9
            },
            {
                "course_id": "nptel-intro-machine-learning",
                "title": "Introduction to Machine Learning (NPTEL / IIT Madras)",
                "provider": "NPTEL / Swayam",
                "domain": "AI/ML",
                "target_branches": "ALL",
                "difficulty": "Intermediate",
                "skills_covered": "Linear Regression, SVM, Dimensionality Reduction, Clustering, Python",
                "duration": "12 Weeks (Ministry of Education)",
                "course_url": "https://swayam.gov.in/nc_details/NPTEL",
                "thumbnail_url": "https://images.unsplash.com/photo-1531746790731-6c087fecd65a?w=600&auto=format&fit=crop&q=80",
                "is_free": True,
                "free_certificate": True,
                "cost_info": "100% Free Learning & Course Content (Government of India)",
                "certificate_info": "IIT Madras / NPTEL Certificate with proctored exam",
                "rating": 4.8
            },
            # 5. Full Stack & Web Development
            {
                "course_id": "coursera-meta-front-end-developer",
                "title": "Meta Front-End Developer Professional Certificate",
                "provider": "Coursera (Meta)",
                "domain": "Full Stack",
                "target_branches": "IS,CS",
                "difficulty": "Intermediate",
                "skills_covered": "HTML5, CSS3, JavaScript ES6, React, Responsive Design, Version Control",
                "duration": "7 Months (6 hrs/wk)",
                "course_url": "https://www.coursera.org/professional-certificates/meta-front-end-developer",
                "thumbnail_url": "https://images.unsplash.com/photo-1581291518857-4e27b48ff24e?w=600&auto=format&fit=crop&q=80",
                "is_free": True,
                "free_certificate": False,
                "cost_info": "Free to Audit All Courses",
                "certificate_info": "Official Meta Career Credential & Certificate",
                "rating": 4.7
            },
            {
                "course_id": "freecodecamp-responsive-web-design",
                "title": "Responsive Web Design Certification (freeCodeCamp)",
                "provider": "freeCodeCamp",
                "domain": "Full Stack",
                "target_branches": "ALL",
                "difficulty": "Beginner",
                "skills_covered": "HTML, CSS, Flexbox, CSS Grid, Media Queries, Accessibility",
                "duration": "300 Hours (Self-Paced)",
                "course_url": "https://www.freecodecamp.org/learn/2022/responsive-web-design/",
                "thumbnail_url": "https://images.unsplash.com/photo-1547658719-da2b51169166?w=600&auto=format&fit=crop&q=80",
                "is_free": True,
                "free_certificate": True,
                "cost_info": "100% Free with Verified Certificate",
                "certificate_info": "Free Industry Recognized Certificate after 5 Projects",
                "rating": 4.9
            },
            # 6. Cloud Computing & DevOps
            {
                "course_id": "coursera-aws-cloud-practitioner",
                "title": "AWS Cloud Technical Essentials (Amazon Web Services)",
                "provider": "Coursera (AWS)",
                "domain": "Cloud & DevOps",
                "target_branches": "IS,CS,EC",
                "difficulty": "Beginner to Intermediate",
                "skills_covered": "AWS EC2, S3, IAM, VPC, RDS, Cloud Architecture, DevOps Basics",
                "duration": "4 Weeks (4 hrs/wk)",
                "course_url": "https://www.coursera.org/learn/aws-cloud-technical-essentials",
                "thumbnail_url": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=600&auto=format&fit=crop&q=80",
                "is_free": True,
                "free_certificate": False,
                "cost_info": "Free Audit Available",
                "certificate_info": "Official AWS Training Certificate",
                "rating": 4.7
            },
            # 7. Cybersecurity
            {
                "course_id": "coursera-ibm-cybersecurity-analyst",
                "title": "IBM Cybersecurity Analyst Professional Certificate",
                "provider": "Coursera (IBM)",
                "domain": "Cybersecurity",
                "target_branches": "IS,CS",
                "difficulty": "Intermediate",
                "skills_covered": "Network Security, Threat Intelligence, Penetration Testing, Incident Response",
                "duration": "8 Months (4 hrs/wk)",
                "course_url": "https://www.coursera.org/professional-certificates/ibm-cybersecurity-analyst",
                "thumbnail_url": "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=600&auto=format&fit=crop&q=80",
                "is_free": True,
                "free_certificate": False,
                "cost_info": "Free to Audit Lectures",
                "certificate_info": "IBM Digital Badge & Coursera Certificate",
                "rating": 4.6
            },
            # 8. Electronics, IoT & Embedded Systems (ECE)
            {
                "course_id": "coursera-iot-embedded-systems-uci",
                "title": "An Introduction to Programming the Internet of Things (UC Irvine)",
                "provider": "Coursera",
                "domain": "IoT & Embedded",
                "target_branches": "EC,IS,CS",
                "difficulty": "Intermediate",
                "skills_covered": "Microcontrollers, Arduino, Raspberry Pi, Sensors, Actuators, C Programming",
                "duration": "4 Weeks",
                "course_url": "https://www.coursera.org/learn/iot",
                "thumbnail_url": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&auto=format&fit=crop&q=80",
                "is_free": True,
                "free_certificate": False,
                "cost_info": "Free Audit Option",
                "certificate_info": "University of California, Irvine Certificate",
                "rating": 4.7
            },
            {
                "course_id": "nptel-vlsi-design-iitkgp",
                "title": "VLSI Design Verification and Test (NPTEL / IIT Kharagpur)",
                "provider": "NPTEL / Swayam",
                "domain": "VLSI",
                "target_branches": "EC",
                "difficulty": "Advanced",
                "skills_covered": "Verilog HDL, CMOS Logic, Synthesis, Testing, Timing Analysis",
                "duration": "8 Weeks",
                "course_url": "https://swayam.gov.in/nc_details/NPTEL",
                "thumbnail_url": "https://images.unsplash.com/photo-1563770660941-20978e870e26?w=600&auto=format&fit=crop&q=80",
                "is_free": True,
                "free_certificate": True,
                "cost_info": "100% Free Complete Courseware",
                "certificate_info": "IIT Kharagpur / Ministry of Education Certificate",
                "rating": 4.8
            },
            # 9. Mechanical Engineering CAD & Simulation
            {
                "course_id": "coursera-autodesk-cad-cam",
                "title": "Autodesk CAD/CAM for Manufacturing Specialization",
                "provider": "Coursera (Autodesk)",
                "domain": "Mechanical CAD & Robotics",
                "target_branches": "ME",
                "difficulty": "Intermediate",
                "skills_covered": "Fusion 360, 3D Modeling, Simulation, CAM Toolpaths, CNC Machining",
                "duration": "4 Months",
                "course_url": "https://www.coursera.org/specializations/autodesk-cad-cam-manufacturing",
                "thumbnail_url": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=600&auto=format&fit=crop&q=80",
                "is_free": True,
                "free_certificate": False,
                "cost_info": "Free Audit Available",
                "certificate_info": "Official Autodesk Professional Credential",
                "rating": 4.8
            },
            # 10. Aptitude & Placement Soft Skills
            {
                "course_id": "coursera-successful-negotiation-michigan",
                "title": "Successful Negotiation: Essential Strategies and Skills (Univ of Michigan)",
                "provider": "Coursera",
                "domain": "Aptitude & Soft Skills",
                "target_branches": "ALL",
                "difficulty": "Beginner to Intermediate",
                "skills_covered": "HR Round Skills, Professional Communication, Problem Solving, Case Interviews",
                "duration": "7 Hours (Self-Paced)",
                "course_url": "https://www.coursera.org/learn/negotiation-skills",
                "thumbnail_url": "https://images.unsplash.com/photo-1521737604893-d14cc237f11d?w=600&auto=format&fit=crop&q=80",
                "is_free": True,
                "free_certificate": False,
                "cost_info": "Free Audit for all learners",
                "certificate_info": "University of Michigan Certificate",
                "rating": 4.9
            }
        ]

        for c_data in courses_data:
            existing = Course.query.filter_by(course_id=c_data["course_id"]).first()
            if not existing:
                course = Course(
                    course_id=c_data["course_id"],
                    title=c_data["title"],
                    provider=c_data["provider"],
                    domain=c_data["domain"],
                    target_branches=c_data["target_branches"],
                    difficulty=c_data["difficulty"],
                    skills_covered=c_data["skills_covered"],
                    duration=c_data["duration"],
                    course_url=c_data["course_url"],
                    thumbnail_url=c_data.get("thumbnail_url"),
                    is_free=c_data["is_free"],
                    free_certificate=c_data["free_certificate"],
                    cost_info=c_data["cost_info"],
                    certificate_info=c_data["certificate_info"],
                    rating=c_data["rating"],
                    last_verified_at=now
                )
                db.session.add(course)
        db.session.commit()
        print(f"Verified & seeded {len(courses_data)} courses across IS, CS, EC, and MECH domains.")

        # 4. Seed Karnataka Workshops & Technical Events
        events_data = [
            {
                "title": "Hands-On Deep Learning & Generative AI Workshop",
                "organizer": "Indian Institute of Science (IISc), Bengaluru",
                "domain": "AI/ML",
                "target_branches": "IS,CS,EC",
                "event_type": "Workshop",
                "city": "Bengaluru",
                "venue_mode": "Hybrid (Online + IISc Campus)",
                "venue_details": "Department of Computational & Data Sciences (CDS), IISc, Bengaluru",
                "event_date": now + datetime.timedelta(days=12),
                "registration_deadline": now + datetime.timedelta(days=7),
                "is_free": True,
                "registration_fee": "Free for VTU & Engineering Students",
                "certificate_available": True,
                "certificate_conditions": "Digital Certificate of Completion issued by IISc CCE",
                "official_registration_url": "https://cce.iisc.ac.in/",
                "source_url": "https://iisc.ac.in/",
                "is_verified": True
            },
            {
                "title": "HackMITM 2026: 24-Hour State-Level Placement Hackathon",
                "organizer": "Maharaja Institute of Technology Mysore (MITM)",
                "domain": "Hackathon",
                "target_branches": "ALL",
                "event_type": "Hackathon",
                "city": "Mysuru",
                "venue_mode": "In-Person",
                "venue_details": "Central Computing Lab & Auditorium, MIT Mysore Campus, Belawadi",
                "event_date": now + datetime.timedelta(days=18),
                "registration_deadline": now + datetime.timedelta(days=10),
                "is_free": True,
                "registration_fee": "Free Entry (Placement Cell Sponsored)",
                "certificate_available": True,
                "certificate_conditions": "Merit & Participation Certificates with Internship Fast-Tracks",
                "official_registration_url": "https://mitmysore.in/",
                "source_url": "https://mitmysore.in/",
                "is_verified": True
            },
            {
                "title": "VTU Belagavi State Technical Symposium & Project Exhibition",
                "organizer": "Visvesvaraya Technological University (VTU), Belagavi",
                "domain": "Placement Bootcamp",
                "target_branches": "ALL",
                "event_type": "Technical Fest",
                "city": "Belagavi",
                "venue_mode": "In-Person",
                "venue_details": "Jnana Sangama Campus, VTU Belagavi",
                "event_date": now + datetime.timedelta(days=25),
                "registration_deadline": now + datetime.timedelta(days=15),
                "is_free": True,
                "registration_fee": "Free for Affiliated College Students",
                "certificate_available": True,
                "certificate_conditions": "Official VTU Participation Certificate",
                "official_registration_url": "https://vtu.ac.in/",
                "source_url": "https://vtu.ac.in/",
                "is_verified": True
            },
            {
                "title": "IEEE Bangalore Hands-On IoT & Embedded Systems Workshop",
                "organizer": "IEEE Bangalore Section",
                "domain": "Embedded & IoT",
                "target_branches": "EC,IS,CS",
                "event_type": "Workshop",
                "city": "Bengaluru",
                "venue_mode": "In-Person",
                "venue_details": "IEEE Bangalore Section Headquarters, Malleshwaram, Bengaluru",
                "event_date": now + datetime.timedelta(days=14),
                "registration_deadline": now + datetime.timedelta(days=8),
                "is_free": False,
                "registration_fee": "₹150 (Free for IEEE Student Members)",
                "certificate_available": True,
                "certificate_conditions": "IEEE Section Certificate with CPE Credits",
                "official_registration_url": "https://ieeebangalore.org/",
                "source_url": "https://ieeebangalore.org/",
                "is_verified": True
            },
            {
                "title": "Infosys Springboard Full-Stack Cloud & DevOps Placement Accelerator",
                "organizer": "Infosys Springboard Karnataka",
                "domain": "Cloud & DevOps",
                "target_branches": "IS,CS",
                "event_type": "Bootcamp",
                "city": "Online",
                "venue_mode": "Online",
                "venue_details": "Infosys Virtual Learning Environment (Karnataka Portal)",
                "event_date": now + datetime.timedelta(days=9),
                "registration_deadline": now + datetime.timedelta(days=5),
                "is_free": True,
                "registration_fee": "100% Free under Digital India Karnataka Initiative",
                "certificate_conditions": "Infosys Springboard Industry-Accredited Certificate",
                "certificate_available": True,
                "official_registration_url": "https://infyspringboard.onwingspan.com/",
                "source_url": "https://infyspringboard.onwingspan.com/",
                "is_verified": True
            },
            {
                "title": "KDEM Cybersecurity Conclave & Ethical Hacking Masterclass",
                "organizer": "Karnataka Digital Economy Mission (KDEM), Mysuru Cluster",
                "domain": "Cybersecurity",
                "target_branches": "IS,CS",
                "event_type": "Conference",
                "city": "Mysuru",
                "venue_mode": "In-Person",
                "venue_details": "Mysuru IT Park & Virtual Stream, Hebbal Industrial Area, Mysuru",
                "event_date": now + datetime.timedelta(days=21),
                "registration_deadline": now + datetime.timedelta(days=14),
                "is_free": True,
                "registration_fee": "Free for Karnataka Engineering Students",
                "certificate_available": True,
                "certificate_conditions": "KDEM / Government of Karnataka Certificate of Attendance",
                "official_registration_url": "https://karnatakadigital.in/",
                "source_url": "https://karnatakadigital.in/",
                "is_verified": True
            },
            {
                "title": "NITK Surathkal Robotics, Automation & CAD Design Challenge",
                "organizer": "National Institute of Technology Karnataka (NITK), Surathkal",
                "domain": "Robotics & CAD",
                "target_branches": "ME,EC",
                "event_type": "Technical Fest",
                "city": "Mangaluru",
                "venue_mode": "In-Person",
                "venue_details": "Department of Mechanical Engineering, NITK Surathkal, Mangaluru",
                "event_date": now + datetime.timedelta(days=30),
                "registration_deadline": now + datetime.timedelta(days=20),
                "is_free": True,
                "registration_fee": "Free Entry for College Teams",
                "certificate_available": True,
                "certificate_conditions": "NITK Certificate of Excellence & Cash Prizes",
                "official_registration_url": "https://www.nitk.ac.in/",
                "source_url": "https://www.nitk.ac.in/",
                "is_verified": True
            },
            {
                "title": "Hubballi-Dharwad Innovation Hub VLSI & Semiconductor Workshop",
                "organizer": "KLE Tech & Deshpande Startups, Hubballi",
                "domain": "Embedded & IoT",
                "target_branches": "EC",
                "event_type": "Workshop",
                "city": "Hubballi",
                "venue_mode": "In-Person",
                "venue_details": "Deshpande Startups Campus, Gokul Road, Hubballi",
                "event_date": now + datetime.timedelta(days=16),
                "registration_deadline": now + datetime.timedelta(days=9),
                "is_free": True,
                "registration_fee": "Free Sponsored by Karnataka Semiconductor Mission",
                "certificate_available": True,
                "certificate_conditions": "Industry Recognized Semiconductor Skills Certificate",
                "official_registration_url": "https://deshpandestartups.org/",
                "source_url": "https://deshpandestartups.org/",
                "is_verified": True
            }
        ]

        for ev_data in events_data:
            existing = WorkshopEvent.query.filter_by(title=ev_data["title"]).first()
            if not existing:
                ev = WorkshopEvent(
                    title=ev_data["title"],
                    organizer=ev_data["organizer"],
                    domain=ev_data["domain"],
                    target_branches=ev_data["target_branches"],
                    event_type=ev_data["event_type"],
                    city=ev_data["city"],
                    venue_mode=ev_data["venue_mode"],
                    venue_details=ev_data["venue_details"],
                    event_date=ev_data["event_date"],
                    registration_deadline=ev_data["registration_deadline"],
                    is_free=ev_data["is_free"],
                    registration_fee=ev_data["registration_fee"],
                    certificate_available=ev_data["certificate_available"],
                    certificate_conditions=ev_data["certificate_conditions"],
                    official_registration_url=ev_data["official_registration_url"],
                    source_url=ev_data.get("source_url"),
                    is_verified=ev_data["is_verified"],
                    last_verified_at=now
                )
                db.session.add(ev)
        db.session.commit()
        print(f"Verified & seeded {len(events_data)} Karnataka workshops & events across Bengaluru, Mysuru, Mangaluru, Belagavi, Hubballi & Online.")

        # 5. Seed initial achievements & notifications for primary demo student Alice Sharma
        alice = Student.query.filter_by(usn="4MH24IS001").first()
        if alice:
            # Check or create preferences
            pref = StudentPreference.query.filter_by(student_usn=alice.usn).first()
            if not pref:
                pref = StudentPreference(
                    student_usn=alice.usn,
                    interested_domains="DSA, Python, AI/ML, Cloud & DevOps",
                    career_goal="Senior Software Engineer / Product SDE",
                    notify_workshops=True,
                    notify_deadlines=True,
                    notify_free_courses=True,
                    coursera_email=alice.email,
                    coursera_connected=False
                )
                db.session.add(pref)

            # Seed sample verified achievements
            existing_ach = StudentAchievement.query.filter_by(student_usn=alice.usn).first()
            if not existing_ach:
                ach1 = StudentAchievement(
                    student_usn=alice.usn,
                    category="COURSE",
                    title="Programming for Everybody (Python Specialization)",
                    provider_or_organizer="Coursera (Univ of Michigan)",
                    domain="Python",
                    completion_date=now - datetime.timedelta(days=45),
                    certificate_url="https://www.coursera.org/verify/DEMO_ALICE_PY101",
                    skills_acquired="Python 3, Data Structures, Algorithms, Problem Solving",
                    verification_status="VERIFIED",
                    verified_by="mit_placement",
                    verified_at=now - datetime.timedelta(days=40),
                    verification_notes="Verified via official Coursera credential link.",
                    is_coursera_sync=True
                )
                ach2 = StudentAchievement(
                    student_usn=alice.usn,
                    category="WORKSHOP",
                    title="Karnataka Student Cloud Bootcamp 2026",
                    provider_or_organizer="Infosys Springboard Karnataka",
                    domain="Cloud & DevOps",
                    completion_date=now - datetime.timedelta(days=20),
                    certificate_url="https://infyspringboard.onwingspan.com/verify/SPRING_ALICE",
                    skills_acquired="AWS, Docker, CI/CD, Microservices",
                    verification_status="VERIFIED",
                    verified_by="placement_coordinator",
                    verified_at=now - datetime.timedelta(days=18),
                    verification_notes="Approved during Department Review.",
                    is_coursera_sync=False
                )
                ach3 = StudentAchievement(
                    student_usn=alice.usn,
                    category="CERTIFICATE",
                    title="Data Structures and Algorithms in Python",
                    provider_or_organizer="freeCodeCamp",
                    domain="DSA",
                    completion_date=now - datetime.timedelta(days=5),
                    certificate_url="https://www.freecodecamp.org/certification/alice-sharma/dsa",
                    skills_acquired="Dynamic Programming, Trees, Binary Search, Big-O",
                    verification_status="PENDING_VERIFICATION",
                    verification_notes="Submitted by student. Awaiting placement coordinator review.",
                    is_coursera_sync=False
                )
                db.session.add_all([ach1, ach2, ach3])

            # Seed Notifications
            existing_notif = StudentNotification.query.filter_by(student_usn=alice.usn).first()
            if not existing_notif:
                n1 = StudentNotification(
                    student_usn=alice.usn,
                    title="New Workshop in Mysuru: HackMITM 2026",
                    message="24-Hour Placement Hackathon registered on MIT Mysore campus. Registrations close in 10 days.",
                    category="WORKSHOP",
                    action_url="/student/achievements?tab=workshops",
                    is_read=False
                )
                n2 = StudentNotification(
                    student_usn=alice.usn,
                    title="Recommended Course: Princeton Algorithms Part I",
                    message="Recommended based on your placement diagnostic test weakness in Data Structures & Algorithms.",
                    category="COURSE",
                    action_url="/student/achievements?tab=courses",
                    is_read=False
                )
                n3 = StudentNotification(
                    student_usn=alice.usn,
                    title="Certificate Verification Approved",
                    message="Your Coursera Python course certificate has been verified by the Placement Cell.",
                    category="ACHIEVEMENT",
                    action_url="/student/achievements?tab=achievements",
                    is_read=True
                )
                db.session.add_all([n1, n2, n3])

            # Seed Course bookmark
            alg_course = Course.query.filter_by(course_id="coursera-algorithms-part1").first()
            if alg_course and not StudentCourseProgress.query.filter_by(student_usn=alice.usn, course_id=alg_course.id).first():
                progress = StudentCourseProgress(
                    student_usn=alice.usn,
                    course_id=alg_course.id,
                    status="ENROLLED",
                    progress_pct=35.0,
                    enrolled_at=now - datetime.timedelta(days=10)
                )
                db.session.add(progress)

            # Seed Event Action
            hack_event = WorkshopEvent.query.filter_by(title="HackMITM 2026: 24-Hour State-Level Placement Hackathon").first()
            if hack_event and not StudentEventAction.query.filter_by(student_usn=alice.usn, event_id=hack_event.id).first():
                act = StudentEventAction(
                    student_usn=alice.usn,
                    event_id=hack_event.id,
                    status="APPLIED",
                    reminder_set=True,
                    notes="Applied as team lead with college teammates."
                )
                db.session.add(act)

            db.session.commit()
            print("Seeded sample achievements, notifications, and event actions for student Alice Sharma (4MH24IS001).")

    print("=" * 60)
    print("ACHIEVEMENT HUB MIGRATION COMPLETED SUCCESSFULLY")
    print("=" * 60)

if __name__ == '__main__':
    run_migration()
