"""
LearningProgressSyncService: Automated synchronisation of course progress and verified certificates.
Performs incremental updates, duplicate prevention, logging to CertificateSyncLog,
and notifies students of newly synchronized verified credentials.
"""

import datetime
from models import (
    db, Student, StudentAchievement, ExternalProviderAccount,
    CertificateSyncLog, Course, StudentCourseProgress
)
from coursera_service import CourseraIntegrationService
from notification_service import NotificationService
from external_account_service import ExternalAccountService

class LearningProgressSyncService:
    @staticmethod
    def sync_provider_certificates(student_usn, provider_name='Coursera'):
        """
        Executes an incremental synchronization of verified achievements from an external provider.
        Prevents duplicates by matching external_certificate_id and provider records.
        """
        norm_provider = provider_name.strip().capitalize() if provider_name else 'Coursera'
        account = ExternalAccountService.get_account(student_usn, norm_provider)
        now = datetime.datetime.utcnow()

        # Create sync log
        sync_log = CertificateSyncLog(
            student_usn=student_usn,
            provider_name=norm_provider,
            sync_started_at=now,
            sync_status='IN_PROGRESS',
            certificates_found=0,
            certificates_synced=0
        )
        db.session.add(sync_log)
        db.session.commit()

        if not account or account.connection_status != 'CONNECTED':
            sync_log.sync_completed_at = datetime.datetime.utcnow()
            sync_log.sync_status = 'NOT_CONNECTED'
            sync_log.error_category = 'AUTHENTICATION_REQUIRED'
            sync_log.error_message = f"Student has not connected an authorised {provider_name} account."
            db.session.commit()
            return {
                "success": False,
                "status": "NOT_CONNECTED",
                "message": f"Your {provider_name} account is not connected. Please connect your account first.",
                "certificates_synced": 0
            }

        # Check token expiration
        if account.token_expires_at and account.token_expires_at < now:
            sync_log.sync_completed_at = datetime.datetime.utcnow()
            sync_log.sync_status = 'EXPIRED'
            sync_log.error_category = 'TOKEN_EXPIRED'
            sync_log.error_message = "OAuth access token has expired. Re-authorisation required."
            account.connection_status = 'EXPIRED'
            db.session.commit()
            return {
                "success": False,
                "status": "EXPIRED",
                "message": "Authorisation token has expired. Please reconnect your account.",
                "certificates_synced": 0
            }

        # Fetch certificates from provider
        try:
            if provider_name == 'Coursera':
                cert_items = CourseraIntegrationService.fetch_verified_certificates(
                    account.access_token, account.external_account_id
                )
            else:
                cert_items = []

            sync_log.certificates_found = len(cert_items)
            synced_count = 0
            newly_added_titles = []

            for item in cert_items:
                ext_id = item.get("external_certificate_id")
                title = item.get("title")

                # Deduplication check: by external_certificate_id or exact title+provider for this student
                existing = None
                if ext_id:
                    existing = StudentAchievement.query.filter_by(
                        student_usn=student_usn,
                        external_certificate_id=ext_id
                    ).first()

                if not existing:
                    existing = StudentAchievement.query.filter_by(
                        student_usn=student_usn,
                        title=title,
                        provider_or_organizer=item.get("provider", provider_name)
                    ).first()

                if not existing:
                    # Insert new verified achievement directly
                    new_ach = StudentAchievement(
                        student_usn=student_usn,
                        category='COURSE',
                        achievement_type='COURSE',
                        title=title,
                        provider_or_organizer=item.get("provider", provider_name),
                        domain=item.get("domain", "Technical Core"),
                        completion_date=item.get("completion_date", datetime.datetime.utcnow()),
                        certificate_url=item.get("certificate_url"),
                        skills_acquired=item.get("skills", ""),
                        verification_status='VERIFIED',
                        verification_method='OAUTH_SYNC',
                        verified_by=f"{provider_name} Automated OAuth Sync",
                        verified_at=datetime.datetime.utcnow(),
                        verification_notes="Automatically verified via official provider synchronization.",
                        external_certificate_id=ext_id,
                        is_coursera_sync=(provider_name == 'Coursera'),
                        description=item.get("description", "Imported via authorized external learning account.")
                    )
                    db.session.add(new_ach)
                    synced_count += 1
                    newly_added_titles.append(title)

                    # Update or mark matching course in StudentCourseProgress as COMPLETED
                    matched_course = Course.query.filter(Course.title.ilike(f"%{title[:20]}%")).first()
                    if matched_course:
                        prog = StudentCourseProgress.query.filter_by(
                            student_usn=student_usn,
                            course_id=matched_course.id
                        ).first()
                        if prog:
                            prog.status = 'COMPLETED'
                            prog.progress_pct = 100.0
                            prog.completed_at = datetime.datetime.utcnow()

            # Update account sync timestamp
            account.last_synced_at = datetime.datetime.utcnow()
            sync_log.sync_completed_at = datetime.datetime.utcnow()
            sync_log.certificates_synced = synced_count
            sync_log.sync_status = 'SUCCESS' if synced_count > 0 else 'NO_NEW_CERTIFICATES'

            db.session.commit()

            # Send student notification if any new certificates were synced
            if synced_count > 0:
                NotificationService.create_notification(
                    student_usn=student_usn,
                    title="New Verified Certificate Synchronized! 🏆",
                    message=f"Synchronized {synced_count} verified certificate(s) from {provider_name}: {', '.join(newly_added_titles)}.",
                    category="ACHIEVEMENT",
                    action_url="/student/achievements?tab=my_achievements"
                )

            return {
                "success": True,
                "status": sync_log.sync_status,
                "certificates_found": len(cert_items),
                "certificates_synced": synced_count,
                "message": f"Successfully checked {provider_name}. {synced_count} new certificate(s) added." if synced_count > 0 else f"{provider_name} is in sync. No new certificates found."
            }

        except Exception as e:
            db.session.rollback()
            sync_log.sync_completed_at = datetime.datetime.utcnow()
            sync_log.sync_status = 'FAILED'
            sync_log.error_category = 'SYNC_EXECUTION_ERROR'
            sync_log.error_message = str(e)
            db.session.commit()
            return {
                "success": False,
                "status": "FAILED",
                "message": f"Synchronisation error: {str(e)}",
                "certificates_synced": 0
            }

    sync_coursera_for_student = sync_provider_certificates
