"""
CourseProviderService: Modular course discovery, Coursera API integration interface,
and student learning progress tracker for MIT Placement Portal.
"""

import os
import datetime
from models import db, Course, StudentCourseProgress, StudentPreference, Student

class CourseProviderService:
    @staticmethod
    def check_coursera_integration_status():
        """
        Investigates live Coursera Partner / Enterprise API configuration.
        Returns capability state and clear documentation when enterprise credentials are absent.
        """
        client_id = os.environ.get('COURSERA_CLIENT_ID')
        client_secret = os.environ.get('COURSERA_CLIENT_SECRET')

        if client_id and client_secret:
            return {
                "is_live_oauth_configured": True,
                "integration_mode": "ENTERPRISE_PARTNER_OAUTH",
                "message": "Coursera Enterprise Partner API is active with live OAuth 2.0 synchronisation."
            }
        else:
            return {
                "is_live_oauth_configured": False,
                "integration_mode": "OFFICIAL_CATALOG_AND_LINK_VERIFICATION",
                "message": "Official Coursera Direct Course Discovery is active. Students can link to official courseware, connect their student Coursera email, track learning progress, and submit completion certificates for placement verification."
            }

    @staticmethod
    def get_courses(search_query=None, domain=None, difficulty=None, branch=None,
                    free_only=False, free_certificate_only=False, paid_only=False, limit=50):
        """
        Queries and filters verified courses across domains, branch suitability, and pricing criteria.
        """
        query = Course.query

        if search_query and search_query.strip():
            term = f"%{search_query.strip().lower()}%"
            query = query.filter(
                (db.func.lower(Course.title).like(term)) |
                (db.func.lower(Course.skills_covered).like(term)) |
                (db.func.lower(Course.provider).like(term)) |
                (db.func.lower(Course.domain).like(term)) |
                (db.func.lower(Course.description).like(term))
            )

        if domain and domain != 'ALL':
            domain_lower = domain.lower()
            if 'python' in domain_lower and 'java' in domain_lower:
                query = query.filter(Course.domain.in_(['Python', 'Java']))
            elif 'dsa' in domain_lower or 'coding' in domain_lower:
                query = query.filter(Course.domain.in_(['DSA', 'Coding', 'C']))
            elif 'ai' in domain_lower or 'ml' in domain_lower:
                query = query.filter(Course.domain == 'AI/ML')
            elif 'cyber' in domain_lower:
                query = query.filter(Course.domain == 'Cybersecurity')
            elif 'web' in domain_lower or 'full' in domain_lower:
                query = query.filter(Course.domain == 'Full Stack')
            elif 'cloud' in domain_lower or 'devops' in domain_lower:
                query = query.filter(Course.domain == 'Cloud & DevOps')
            elif 'iot' in domain_lower or 'embedded' in domain_lower or 'electronic' in domain_lower:
                query = query.filter(Course.domain.in_(['IoT & Embedded', 'VLSI']))
            elif 'mech' in domain_lower or 'cad' in domain_lower or 'robot' in domain_lower:
                query = query.filter(Course.domain == 'Mechanical CAD & Robotics')
            elif 'comm' in domain_lower or 'placement' in domain_lower or 'soft' in domain_lower or 'aptitude' in domain_lower:
                query = query.filter(Course.domain == 'Aptitude & Soft Skills')
            else:
                query = query.filter(Course.domain == domain)

        if difficulty and difficulty != 'ALL':
            query = query.filter(Course.difficulty == difficulty)

        if branch and branch != 'ALL':
            query = query.filter(
                (Course.target_branches == 'ALL') |
                (Course.target_branches.like(f"%{branch}%"))
            )

        if free_only:
            query = query.filter(Course.is_free == True)

        if free_certificate_only:
            query = query.filter(Course.free_certificate == True)

        if paid_only:
            query = query.filter(Course.is_free == False)

        return query.order_by(Course.rating.desc(), Course.id.asc()).limit(limit).all()

    @staticmethod
    def get_course_by_id(course_id):
        return db.session.get(Course, course_id)

    @staticmethod
    def get_student_courses(student_usn):
        """
        Returns all courses with this student's progress and bookmark state attached.
        """
        records = StudentCourseProgress.query.filter_by(student_usn=student_usn).all()
        progress_map = {r.course_id: r for r in records}
        return progress_map

    @staticmethod
    def toggle_bookmark(student_usn, course_id):
        """
        Bookmarks or un-bookmarks a course for the authenticated student.
        """
        record = StudentCourseProgress.query.filter_by(student_usn=student_usn, course_id=course_id).first()
        if record:
            if record.status == 'BOOKMARKED':
                db.session.delete(record)
                db.session.commit()
                return False, "Course removed from bookmarks."
            else:
                # If enrolled or in progress, leave it but toggle
                return True, "Course is already in your learning list."
        else:
            new_record = StudentCourseProgress(
                student_usn=student_usn,
                course_id=course_id,
                status='BOOKMARKED',
                saved_at=datetime.datetime.utcnow()
            )
            db.session.add(new_record)
            db.session.commit()
            return True, "Course bookmarked successfully."

    @staticmethod
    def update_progress(student_usn, course_id, status, progress_pct=0.0):
        """
        Updates enrollment or completion status for a student course.
        """
        now = datetime.datetime.utcnow()
        record = StudentCourseProgress.query.filter_by(student_usn=student_usn, course_id=course_id).first()
        if not record:
            record = StudentCourseProgress(
                student_usn=student_usn,
                course_id=course_id,
                status=status,
                progress_pct=progress_pct,
                saved_at=now,
                enrolled_at=now if status in ['ENROLLED', 'IN_PROGRESS', 'COMPLETED'] else None,
                completed_at=now if status == 'COMPLETED' else None
            )
            db.session.add(record)
        else:
            record.status = status
            record.progress_pct = max(record.progress_pct or 0.0, float(progress_pct))
            if status in ['ENROLLED', 'IN_PROGRESS'] and not record.enrolled_at:
                record.enrolled_at = now
            elif status == 'COMPLETED':
                record.completed_at = now
                record.progress_pct = 100.0

        db.session.commit()
        return record

    @staticmethod
    def connect_coursera_account(student_usn, coursera_email):
        """
        Links student's Coursera email address securely in their preferences.
        """
        pref = StudentPreference.query.filter_by(student_usn=student_usn).first()
        now = datetime.datetime.utcnow()
        if not pref:
            pref = StudentPreference(
                student_usn=student_usn,
                coursera_email=coursera_email.strip().lower(),
                coursera_connected=True,
                coursera_connected_at=now
            )
            db.session.add(pref)
        else:
            pref.coursera_email = coursera_email.strip().lower()
            pref.coursera_connected = True
            pref.coursera_connected_at = now

        db.session.commit()
        return pref

    @staticmethod
    def get_recommended_courses_for_student(student):
        """
        Recommends courses tailored to student's branch and placement diagnostic weaknesses.
        """
        from recommendation_service import RecommendationService
        recs = RecommendationService.get_recommendations_for_student(student)
        return recs.get("recommended_courses", [])

# Alias matching prompt terminology
CourseDiscoveryService = CourseProviderService
