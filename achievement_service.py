"""
AchievementService & CertificateVerificationService: Student portfolio tracking,
manual achievement submission, file evidence handling, and Placement Admin verification workflow.
"""

import os
import datetime
from werkzeug.utils import secure_filename
from models import db, StudentAchievement, Student, AuditLog
from notification_service import NotificationService

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class AchievementService:
    @staticmethod
    def get_student_portfolio_summary(student_usn):
        """
        Calculates verified achievement statistics for the student portfolio.
        Only counts achievements according to their actual status.
        """
        all_achievements = StudentAchievement.query.filter_by(student_usn=student_usn).order_by(StudentAchievement.completion_date.desc()).all()
        
        verified_list = [a for a in all_achievements if a.verification_status == 'VERIFIED']
        pending_list = [a for a in all_achievements if a.verification_status == 'PENDING_VERIFICATION']
        rejected_list = [a for a in all_achievements if a.verification_status == 'REJECTED']

        completed_courses = len([a for a in verified_list if a.category in ['COURSE', 'CERTIFICATE']])
        verified_certs = len([a for a in verified_list if a.certificate_url or a.evidence_file])
        workshops_attended = len([a for a in verified_list if a.category in ['WORKSHOP', 'BOOTCAMP', 'TRAINING']])
        hackathons_participated = len([a for a in verified_list if a.category in ['HACKATHON', 'COMPETITION']])
        internships_completed = len([a for a in verified_list if a.category in ['INTERNSHIP', 'PROJECT']])

        # Unique skills
        skills_set = set()
        for a in verified_list:
            if a.skills_acquired:
                for s in a.skills_acquired.split(','):
                    s_clean = s.strip()
                    if s_clean:
                        skills_set.add(s_clean)

        return {
            "all_achievements": all_achievements,
            "verified_achievements": verified_list,
            "pending_achievements": pending_list,
            "rejected_achievements": rejected_list,
            "total_completed_courses": completed_courses,
            "total_verified_certificates": verified_certs,
            "workshops_attended": workshops_attended,
            "hackathons_participated": hackathons_participated,
            "internships_completed": internships_completed,
            "pending_verifications_count": len(pending_list),
            "skills_developed": sorted(list(skills_set)),
            "total_count": len(all_achievements)
        }

    @staticmethod
    def get_filtered_achievements(student_usn, category='ALL', status='ALL', search_query='', sort_by='newest'):
        """
        Retrieves student achievements with advanced category, status, search and sort filters.
        """
        query = StudentAchievement.query.filter_by(student_usn=student_usn)

        # Category Filter
        if category and category != 'ALL':
            cat_upper = category.upper()
            if cat_upper in ['COURSES', 'COURSE']:
                query = query.filter(StudentAchievement.category.in_(['COURSE', 'CERTIFICATE']))
            elif cat_upper in ['WORKSHOPS', 'WORKSHOP']:
                query = query.filter(StudentAchievement.category.in_(['WORKSHOP', 'BOOTCAMP', 'TRAINING']))
            elif cat_upper in ['HACKATHONS', 'HACKATHON']:
                query = query.filter(StudentAchievement.category.in_(['HACKATHON', 'COMPETITION']))
            elif cat_upper in ['INTERNSHIPS', 'INTERNSHIP']:
                query = query.filter(StudentAchievement.category.in_(['INTERNSHIP', 'PROJECT']))
            else:
                query = query.filter(StudentAchievement.category == cat_upper)

        # Verification Status Filter
        if status and status != 'ALL':
            query = query.filter(StudentAchievement.verification_status == status.upper())

        # Search Query
        if search_query and search_query.strip():
            term = f"%{search_query.strip().lower()}%"
            query = query.filter(
                (db.func.lower(StudentAchievement.title).like(term)) |
                (db.func.lower(StudentAchievement.provider_or_organizer).like(term)) |
                (db.func.lower(StudentAchievement.domain).like(term)) |
                (db.func.lower(StudentAchievement.skills_acquired).like(term))
            )

        # Sorting
        if sort_by == 'oldest':
            query = query.order_by(StudentAchievement.completion_date.asc())
        elif sort_by == 'category':
            query = query.order_by(StudentAchievement.category.asc(), StudentAchievement.completion_date.desc())
        elif sort_by == 'title':
            query = query.order_by(StudentAchievement.title.asc())
        else: # 'newest' default
            query = query.order_by(StudentAchievement.completion_date.desc())

        return query.all()

    @staticmethod
    def get_achievement_secure(student_usn, achievement_id, is_admin=False):
        """
        Retrieves achievement with server-side ownership validation.
        Prevents IDOR: returns (None, 'FORBIDDEN') if not owned by student.
        """
        ach = db.session.get(StudentAchievement, achievement_id)
        if not ach:
            return None, "NOT_FOUND"

        if not is_admin and ach.student_usn != student_usn:
            return None, "FORBIDDEN"

        return ach, None

    @staticmethod
    def submit_achievement(student_usn, data, file_obj=None, upload_folder=None):
        """
        Records a new student achievement with status PENDING_VERIFICATION.
        Handles deduplication and optional certificate file evidence safely.
        """
        title = data['title'].strip()
        provider = data['provider_or_organizer'].strip()
        category = data.get('category', 'COURSE').upper()

        # Deduplication check: check if already exists for this student
        existing = StudentAchievement.query.filter_by(
            student_usn=student_usn,
            title=title,
            provider_or_organizer=provider
        ).first()

        if existing:
            return existing

        filename = None
        if file_obj and file_obj.filename and allowed_file(file_obj.filename) and upload_folder:
            os.makedirs(upload_folder, exist_ok=True)
            clean_name = secure_filename(file_obj.filename)
            unique_prefix = f"cert_{student_usn}_{int(datetime.datetime.utcnow().timestamp())}"
            filename = f"{unique_prefix}_{clean_name}"
            target_path = os.path.join(upload_folder, filename)
            file_obj.save(target_path)

        completion_date = datetime.datetime.utcnow()
        if data.get('completion_date'):
            try:
                completion_date = datetime.datetime.strptime(data['completion_date'], '%Y-%m-%d')
            except Exception:
                pass

        ach = StudentAchievement(
            student_usn=student_usn,
            category=category,
            achievement_type=category,
            title=title,
            provider_or_organizer=provider,
            domain=data.get('domain', 'Technical Core').strip(),
            completion_date=completion_date,
            certificate_url=data.get('certificate_url', '').strip() or None,
            evidence_file=filename,
            skills_acquired=data.get('skills_acquired', '').strip() or None,
            verification_status='PENDING_VERIFICATION',
            verification_method='MANUAL_SUBMISSION',
            verification_notes="Submitted by student. Awaiting placement coordinator review.",
            description=data.get('description', '').strip() or None
        )
        db.session.add(ach)
        db.session.commit()

        # Send in-app notification confirming receipt
        NotificationService.create_notification(
            student_usn=student_usn,
            title="Achievement Submitted for Verification",
            message=f"'{ach.title}' has been submitted. Placement cell will verify your certificate.",
            category="ACHIEVEMENT",
            action_url="/student/achievements?tab=my_achievements"
        )

        return ach

class CertificateVerificationService:
    @staticmethod
    def get_pending_submissions(dept_code=None):
        """
        Returns all pending student achievements for admin review.
        """
        query = StudentAchievement.query.filter_by(verification_status='PENDING_VERIFICATION')
        if dept_code and dept_code != 'ALL':
            query = query.join(Student).join(Student.department).filter(Student.department.has(code=dept_code))
        return query.order_by(StudentAchievement.created_at.desc()).all()

    @staticmethod
    def get_recent_verifications(dept_code=None, limit=10):
        """
        Returns recently verified or rejected achievements for audit history.
        """
        query = StudentAchievement.query.filter(StudentAchievement.verification_status.in_(['VERIFIED', 'REJECTED']))
        if dept_code and dept_code != 'ALL':
            query = query.join(Student).join(Student.department).filter(Student.department.has(code=dept_code))
        return query.order_by(StudentAchievement.verified_at.desc()).limit(limit).all()

    @staticmethod
    def verify_achievement(achievement_id, admin_username, action, notes=None):
        """
        Approves or Rejects a student achievement submission.
        Logs audit record and sends student in-app notification.
        """
        ach = db.session.get(StudentAchievement, achievement_id)
        if not ach:
            return False, "Achievement record not found."

        now = datetime.datetime.utcnow()
        if action == 'APPROVE':
            ach.verification_status = 'VERIFIED'
            ach.verified_by = admin_username
            ach.verified_at = now
            ach.verification_notes = notes or "Certificate verified and approved by Placement Cell."
            
            # Send notification to student
            NotificationService.create_notification(
                student_usn=ach.student_usn,
                title="Certificate Verified & Approved! 🏆",
                message=f"Your achievement '{ach.title}' ({ach.provider_or_organizer}) has been verified and added to your official placement portfolio.",
                category="ACHIEVEMENT",
                action_url="/student/achievements?tab=achievements"
            )
            msg = f"Achievement '{ach.title}' approved successfully."
        elif action == 'REJECT':
            ach.verification_status = 'REJECTED'
            ach.verified_by = admin_username
            ach.verified_at = now
            ach.verification_notes = notes or "Certificate could not be verified. Please check verification URL or evidence file."
            
            NotificationService.create_notification(
                student_usn=ach.student_usn,
                title="Certificate Verification Update",
                message=f"Your submission '{ach.title}' was reviewed: {ach.verification_notes}",
                category="ACHIEVEMENT",
                action_url="/student/achievements?tab=achievements"
            )
            msg = f"Achievement '{ach.title}' marked as rejected."
        else:
            return False, "Invalid action."

        # Audit log entry
        audit = AuditLog(
            student_usn=ach.student_usn,
            changed_by=admin_username,
            action=f"CERTIFICATE_{action}",
            details=f"Achievement ID {ach.id} ('{ach.title}') {action}D. Notes: {ach.verification_notes}"
        )
        db.session.add(audit)
        db.session.commit()

        return True, msg
