"""
WorkshopIntegrationService & HackathonIntegrationService:
Manages technical event participation and provides automated organizer verification (Method A)
along with secure manual submission handling (Method B) for hackathons and workshops.
"""

import datetime
from models import (
    db, Student, WorkshopEvent, StudentEventAction,
    StudentAchievement, AuditLog
)
from notification_service import NotificationService

class WorkshopIntegrationService:
    @staticmethod
    def verify_workshop_completion(student_usn, event_id, certificate_url=None, notes=None, verifier_identity="Organizer Integration"):
        """
        Method A: Automatically verifies student participation in an engineering workshop.
        Publishes verified certificate directly to My Achievements.
        """
        student = Student.query.filter_by(usn=student_usn).first()
        event = db.session.get(WorkshopEvent, event_id)

        if not student or not event:
            return False, "Invalid student USN or event ID."

        # Check existing action
        action = StudentEventAction.query.filter_by(student_usn=student_usn, event_id=event_id).first()
        if not action:
            action = StudentEventAction(
                student_usn=student_usn,
                event_id=event_id,
                status='ATTENDED',
                notes='Attended and verified via Organizer Integration'
            )
            db.session.add(action)
        else:
            action.status = 'ATTENDED'
            action.updated_at = datetime.datetime.utcnow()

        # Deduplication check: check if already published
        existing_ach = StudentAchievement.query.filter_by(
            student_usn=student_usn,
            title=event.title,
            provider_or_organizer=event.organizer
        ).first()

        if existing_ach:
            if existing_ach.verification_status != 'VERIFIED':
                existing_ach.verification_status = 'VERIFIED'
                existing_ach.verification_method = 'ORGANIZER_VERIFIED'
                existing_ach.verified_by = verifier_identity
                existing_ach.verified_at = datetime.datetime.utcnow()
                db.session.commit()
            return True, f"Workshop certificate for '{event.title}' confirmed as Verified."

        # Create new verified achievement
        ach = StudentAchievement(
            student_usn=student_usn,
            category='WORKSHOP',
            achievement_type='WORKSHOP',
            title=event.title,
            provider_or_organizer=event.organizer,
            domain=event.domain,
            completion_date=event.event_date,
            certificate_url=certificate_url or event.official_registration_url,
            skills_acquired=f"{event.domain}, Hands-on Engineering",
            verification_status='VERIFIED',
            verification_method='ORGANIZER_VERIFIED',
            verified_by=verifier_identity,
            verified_at=datetime.datetime.utcnow(),
            verification_notes=notes or f"Verified attendance at {event.venue_mode} workshop in {event.city}.",
            external_certificate_id=f"EVT_{event.id}_{student_usn}",
            description=f"Participated in {event.event_type} organized by {event.organizer}."
        )
        db.session.add(ach)
        db.session.commit()

        # Notify student
        NotificationService.create_notification(
            student_usn=student_usn,
            title="Workshop Certificate Verified! 🏅",
            message=f"Your participation in '{event.title}' has been verified by the organizer.",
            category="WORKSHOP",
            action_url="/student/achievements?tab=my_achievements"
        )

        return True, f"Workshop achievement '{event.title}' successfully verified and published."

class HackathonIntegrationService:
    @staticmethod
    def verify_hackathon_participation(student_usn, hackathon_title, organizer, domain, award_or_rank=None, certificate_url=None, verifier_identity="Hackathon Portal API"):
        """
        Method A: Automatically verifies hackathon award, rank, or participation.
        Publishes verified credential to student's My Achievements.
        """
        student = Student.query.filter_by(usn=student_usn).first()
        if not student:
            return False, "Student not found."

        ext_cert_id = f"HACK_{student_usn}_{abs(hash(hackathon_title)) % 1000000}"

        # Deduplication check
        existing = StudentAchievement.query.filter_by(
            student_usn=student_usn,
            title=hackathon_title,
            provider_or_organizer=organizer
        ).first()

        if existing:
            existing.verification_status = 'VERIFIED'
            existing.verification_method = 'ORGANIZER_VERIFIED'
            existing.verified_by = verifier_identity
            existing.verified_at = datetime.datetime.utcnow()
            db.session.commit()
            return True, f"Hackathon certificate for '{hackathon_title}' confirmed as Verified."

        ach = StudentAchievement(
            student_usn=student_usn,
            category='HACKATHON',
            achievement_type='HACKATHON',
            title=hackathon_title,
            provider_or_organizer=organizer,
            domain=domain,
            completion_date=datetime.datetime.utcnow(),
            certificate_url=certificate_url,
            skills_acquired=f"{domain}, Rapid Prototyping, Competitive Coding",
            verification_status='VERIFIED',
            verification_method='ORGANIZER_VERIFIED',
            verified_by=verifier_identity,
            verified_at=datetime.datetime.utcnow(),
            verification_notes=f"Organizer verified: {award_or_rank or 'Participated in competition'}.",
            external_certificate_id=ext_cert_id,
            description=f"{award_or_rank or 'Competitive participation'} in {hackathon_title}."
        )
        db.session.add(ach)
        db.session.commit()

        # Audit log
        audit = AuditLog(
            student_usn=student_usn,
            changed_by=verifier_identity,
            action="HACKATHON_AUTO_VERIFIED",
            details=f"Verified '{hackathon_title}' for {student_usn}."
        )
        db.session.add(audit)
        db.session.commit()

        # Notification
        NotificationService.create_notification(
            student_usn=student_usn,
            title="Hackathon Achievement Verified! 🚀",
            message=f"Your achievement in '{hackathon_title}' ({award_or_rank or 'Participation'}) is published in My Achievements.",
            category="ACHIEVEMENT",
            action_url="/student/achievements?tab=my_achievements"
        )

        return True, f"Hackathon '{hackathon_title}' verified and published."
