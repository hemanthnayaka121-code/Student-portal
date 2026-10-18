"""
NotificationService: Student in-app notification center, deadline alerts,
and achievement update dispatcher for MIT Placement Portal.
"""

import datetime
from models import db, StudentNotification, StudentEventAction, WorkshopEvent

class NotificationService:
    @staticmethod
    def get_student_notifications(student_usn, unread_only=False, limit=20):
        """
        Retrieves in-app notifications for the student, newest first.
        """
        query = StudentNotification.query.filter_by(
            student_usn=student_usn,
            is_dismissed=False
        )
        if unread_only:
            query = query.filter_by(is_read=False)
        return query.order_by(StudentNotification.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_unread_count(student_usn):
        """
        Returns number of unread notifications for badge display.
        """
        return StudentNotification.query.filter_by(
            student_usn=student_usn,
            is_read=False,
            is_dismissed=False
        ).count()

    @staticmethod
    def mark_as_read(student_usn, notification_id):
        """
        Marks an individual notification as read with ownership validation.
        """
        notif = StudentNotification.query.filter_by(id=notification_id, student_usn=student_usn).first()
        if notif:
            notif.is_read = True
            db.session.commit()
            return True
        return False

    @staticmethod
    def mark_all_read(student_usn):
        """
        Marks all active notifications as read for this student.
        """
        StudentNotification.query.filter_by(
            student_usn=student_usn,
            is_read=False,
            is_dismissed=False
        ).update({"is_read": True})
        db.session.commit()
        return True

    @staticmethod
    def dismiss_notification(student_usn, notification_id):
        """
        Dismisses a notification from the student feed.
        """
        notif = StudentNotification.query.filter_by(id=notification_id, student_usn=student_usn).first()
        if notif:
            notif.is_dismissed = True
            db.session.commit()
            return True
        return False

    @staticmethod
    def create_notification(student_usn, title, message, category="WORKSHOP", action_url=None):
        """
        Dispatches a new notification to the student's in-app center.
        """
        notif = StudentNotification(
            student_usn=student_usn,
            title=title.strip(),
            message=message.strip(),
            category=category,
            action_url=action_url,
            is_read=False,
            is_dismissed=False,
            created_at=datetime.datetime.utcnow()
        )
        db.session.add(notif)
        db.session.commit()
        return notif

    @staticmethod
    def check_approaching_deadlines(student_usn):
        """
        Checks student's saved events and automatically creates deadline alerts if within 3 days.
        """
        now = datetime.datetime.utcnow()
        deadline_window = now + datetime.timedelta(days=3)

        saved_actions = StudentEventAction.query.filter_by(student_usn=student_usn).all()
        for act in saved_actions:
            ev = act.event
            if ev and ev.registration_deadline and now < ev.registration_deadline <= deadline_window:
                # Check if notification already dispatched recently
                existing = StudentNotification.query.filter_by(
                    student_usn=student_usn,
                    category="DEADLINE"
                ).filter(StudentNotification.title.like(f"%{ev.title[:30]}%")).first()

                if not existing:
                    days_left = (ev.registration_deadline - now).days
                    NotificationService.create_notification(
                        student_usn=student_usn,
                        title=f"Registration Deadline in {days_left}d: {ev.title[:40]}...",
                        message=f"Registration closes on {ev.registration_deadline.strftime('%b %d, %Y')} for {ev.title} ({ev.organizer}).",
                        category="DEADLINE",
                        action_url="/student/achievements?tab=workshops"
                    )
