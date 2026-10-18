"""
WorkshopDiscoveryService: Karnataka technical event & workshop discovery engine for MIT Placement Portal.
Provides opportunities across Bengaluru, Mysuru, Mangaluru, Hubballi, Belagavi, and Online.
"""

import datetime
from models import db, WorkshopEvent, StudentEventAction

class WorkshopDiscoveryService:
    @staticmethod
    def get_events(city=None, domain=None, branch=None, free_only=False, upcoming_only=True, limit=50):
        """
        Queries verified Karnataka workshops & events matching filter criteria.
        """
        now = datetime.datetime.utcnow()
        query = WorkshopEvent.query.filter_by(is_verified=True)

        if upcoming_only:
            query = query.filter(WorkshopEvent.event_date >= now - datetime.timedelta(days=1))

        if city and city != 'ALL':
            query = query.filter(WorkshopEvent.city == city)

        if domain and domain != 'ALL':
            query = query.filter(WorkshopEvent.domain == domain)

        if branch and branch != 'ALL':
            query = query.filter(
                (WorkshopEvent.target_branches == 'ALL') |
                (WorkshopEvent.target_branches.like(f"%{branch}%"))
            )

        if free_only:
            query = query.filter(WorkshopEvent.is_free == True)

        return query.order_by(WorkshopEvent.event_date.asc()).limit(limit).all()

    @staticmethod
    def get_event_by_id(event_id):
        return db.session.get(WorkshopEvent, event_id)

    @staticmethod
    def get_student_event_actions(student_usn):
        """
        Returns a dictionary mapping event_id -> StudentEventAction for the student.
        """
        actions = StudentEventAction.query.filter_by(student_usn=student_usn).all()
        return {a.event_id: a for a in actions}

    @staticmethod
    def toggle_save_event(student_usn, event_id):
        """
        Saves or unsaves an event for the student.
        """
        action = StudentEventAction.query.filter_by(student_usn=student_usn, event_id=event_id).first()
        if action:
            if action.status == 'SAVED':
                db.session.delete(action)
                db.session.commit()
                return False, "Event removed from saved list."
            else:
                return True, "Event is already in your active events list."
        else:
            action = StudentEventAction(
                student_usn=student_usn,
                event_id=event_id,
                status='SAVED',
                updated_at=datetime.datetime.utcnow()
            )
            db.session.add(action)
            db.session.commit()
            return True, "Event saved to your calendar."

    @staticmethod
    def mark_applied(student_usn, event_id, notes=None):
        """
        Records that student clicked Apply or submitted application on official organizer portal.
        """
        action = StudentEventAction.query.filter_by(student_usn=student_usn, event_id=event_id).first()
        now = datetime.datetime.utcnow()
        if not action:
            action = StudentEventAction(
                student_usn=student_usn,
                event_id=event_id,
                status='APPLIED',
                notes=notes or "Applied via official organizer portal",
                updated_at=now
            )
            db.session.add(action)
        else:
            action.status = 'APPLIED'
            if notes:
                action.notes = notes
            action.updated_at = now

        db.session.commit()
        return action

    @staticmethod
    def record_link_opened(student_usn, event_id):
        """
        Records that student opened the official registration page.
        """
        action = StudentEventAction.query.filter_by(student_usn=student_usn, event_id=event_id).first()
        now = datetime.datetime.utcnow()
        if not action:
            action = StudentEventAction(
                student_usn=student_usn,
                event_id=event_id,
                status='REGISTRATION_OPENED',
                updated_at=now
            )
            db.session.add(action)
            db.session.commit()
        elif action.status == 'SAVED':
            action.status = 'REGISTRATION_OPENED'
            action.updated_at = now
            db.session.commit()
        return action

    @staticmethod
    def toggle_reminder(student_usn, event_id):
        """
        Toggles reminder notifications for an event.
        """
        action = StudentEventAction.query.filter_by(student_usn=student_usn, event_id=event_id).first()
        now = datetime.datetime.utcnow()
        if not action:
            action = StudentEventAction(
                student_usn=student_usn,
                event_id=event_id,
                status='SAVED',
                reminder_set=True,
                updated_at=now
            )
            db.session.add(action)
            db.session.commit()
            return True, "Reminder set for this event."
        else:
            action.reminder_set = not action.reminder_set
            action.updated_at = now
            db.session.commit()
            msg = "Reminder enabled." if action.reminder_set else "Reminder disabled."
            return action.reminder_set, msg

    @staticmethod
    def create_event(data):
        """
        Admin interface to create a verified workshop / technical event.
        """
        ev = WorkshopEvent(
            title=data['title'].strip(),
            organizer=data['organizer'].strip(),
            domain=data['domain'],
            target_branches=data.get('target_branches', 'ALL'),
            event_type=data.get('event_type', 'Workshop'),
            city=data.get('city', 'Bengaluru'),
            venue_mode=data.get('venue_mode', 'In-Person'),
            venue_details=data.get('venue_details', ''),
            event_date=data['event_date'],
            registration_deadline=data['registration_deadline'],
            is_free=data.get('is_free', True),
            registration_fee=data.get('registration_fee', 'Free of Cost'),
            certificate_available=data.get('certificate_available', True),
            certificate_conditions=data.get('certificate_conditions', 'Awarded upon completion'),
            official_registration_url=data['official_registration_url'].strip(),
            source_url=data.get('source_url', '').strip(),
            is_verified=True,
            last_verified_at=datetime.datetime.utcnow()
        )
        db.session.add(ev)
        db.session.commit()
        return ev
