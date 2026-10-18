"""
RecommendationService: Rule-based personalised recommendation engine for MIT Placement Portal.
Connects engineering branch, diagnostic placement weaknesses, and student career interests to
targeted courses, certifications, and Karnataka technical workshops.
"""

from models import Course, WorkshopEvent, PerformanceRecord, StudentPreference

class RecommendationService:
    @staticmethod
    def get_recommendations_for_student(student):
        """
        Computes tailored learning recommendations for the student based on:
        1. Placement diagnostic performance & weaknesses (< 70% benchmark)
        2. Engineering Department (IS/CS, EC, ME)
        3. Stored preferences and career goals
        """
        branch = student.department.code.upper() if student.department else 'IS'
        perf = student.performance
        pref = student.preference

        recommended_courses = []
        recommended_events = []

        # 1. Diagnostic Weakness Rules
        weakness_rules = []

        if perf:
            # DSA Rule
            if (perf.coding_dsa_score or 0.0) < 70.0:
                weakness_rules.append({
                    "domain": "DSA",
                    "reason": f"Recommended because your DSA score ({perf.coding_dsa_score:.0f}%) is below the college placement benchmark (≥ 70%).",
                    "priority": 1
                })

            # Java / OOP Rule
            if (perf.coding_java_score or 0.0) < 70.0:
                weakness_rules.append({
                    "domain": "Java",
                    "reason": f"Recommended because your Java & OOP score ({perf.coding_java_score:.0f}%) needs improvement for technical interview rounds.",
                    "priority": 2
                })

            # C / Core Programming Rule
            if (perf.coding_c_score or 0.0) < 70.0:
                weakness_rules.append({
                    "domain": "Python",
                    "reason": f"Recommended to strengthen problem-solving fundamentals (C Assessment: {perf.coding_c_score:.0f}%).",
                    "priority": 3
                })

            # Aptitude Rule
            if (perf.aptitude_score or 0.0) < 70.0:
                weakness_rules.append({
                    "domain": "Aptitude & Soft Skills",
                    "reason": f"Recommended because your Aptitude score ({perf.aptitude_score:.0f}%) is under the 70% screening benchmark.",
                    "priority": 4
                })

            # HR / Communication Rule
            if not perf.hr_status or not perf.gd_status:
                weakness_rules.append({
                    "domain": "Aptitude & Soft Skills",
                    "reason": "Recommended to practice structured communication for GD & HR behavioral interviews.",
                    "priority": 5
                })

        # 2. Branch-specific Core Domains
        branch_domains = {
            'IS': ['DSA', 'Python', 'Full Stack', 'Cloud & DevOps', 'AI/ML', 'Cybersecurity'],
            'CS': ['DSA', 'Python', 'Java', 'Full Stack', 'Cloud & DevOps', 'AI/ML'],
            'EC': ['IoT & Embedded', 'VLSI', 'Python', 'AI/ML'],
            'ME': ['Mechanical CAD & Robotics', 'Python', 'Aptitude & Soft Skills']
        }
        domains_for_branch = branch_domains.get(branch, ['DSA', 'Python', 'Full Stack'])

        # Match Courses
        seen_course_ids = set()

        # A. Courses matching diagnosed weaknesses
        for rule in weakness_rules:
            matched = Course.query.filter(Course.domain == rule["domain"]).limit(2).all()
            for c in matched:
                if c.id not in seen_course_ids:
                    seen_course_ids.add(c.id)
                    recommended_courses.append({
                        "course": c,
                        "rationale": rule["reason"],
                        "type": "Diagnostic Weakness Remedial"
                    })

        # B. Courses matching branch specialization
        for dom in domains_for_branch:
            matched = Course.query.filter(
                Course.domain == dom,
                (Course.target_branches == 'ALL') | (Course.target_branches.like(f"%{branch}%"))
            ).limit(2).all()
            for c in matched:
                if c.id not in seen_course_ids and len(recommended_courses) < 6:
                    seen_course_ids.add(c.id)
                    recommended_courses.append({
                        "course": c,
                        "rationale": f"Recommended for {branch} engineering students pursuing technical placements.",
                        "type": "Branch Core Skill"
                    })

        # Match Karnataka Workshops & Events
        seen_event_ids = set()
        matched_events = WorkshopEvent.query.filter(
            WorkshopEvent.is_verified == True,
            (WorkshopEvent.target_branches == 'ALL') | (WorkshopEvent.target_branches.like(f"%{branch}%"))
        ).order_by(WorkshopEvent.event_date.asc()).limit(5).all()

        for ev in matched_events:
            if ev.id not in seen_event_ids:
                seen_event_ids.add(ev.id)
                rationale = f"Upcoming Karnataka {ev.event_type} in {ev.city} open to {branch} branch students."
                if ev.domain == 'Hackathon':
                    rationale = f"High-impact competitive coding hackathon in Mysuru to boost placement shortlist chances."
                elif ev.domain in ['AI/ML', 'Cloud & DevOps']:
                    rationale = f"Hands-on {ev.domain} opportunity matching current recruitment trends."

                recommended_events.append({
                    "event": ev,
                    "rationale": rationale,
                    "type": "Karnataka Opportunity"
                })

        return {
            "recommended_courses": recommended_courses,
            "recommended_events": recommended_events,
            "weakness_count": len(weakness_rules),
            "branch": branch
        }
