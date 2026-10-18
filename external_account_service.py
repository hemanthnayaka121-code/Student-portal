"""
ExternalAccountService: Manages external provider connections (Coursera, NPTEL, etc.)
Handles OAuth state, token life-cycle, connection tracking, and disconnect operations.
"""

import os
import datetime
from models import db, ExternalProviderAccount, StudentPreference, Student, AuditLog

class ExternalAccountService:
    @staticmethod
    def get_account(student_usn, provider_name='Coursera'):
        """
        Retrieves the external provider account for a given student.
        """
        norm_provider = provider_name.strip().capitalize() if provider_name else 'Coursera'
        return ExternalProviderAccount.query.filter_by(
            student_usn=student_usn,
            provider_name=norm_provider
        ).first()

    @staticmethod
    def link_account(student_usn, provider_name='Coursera', external_account_id=None,
                     external_email=None, access_token=None, refresh_token=None, expires_in=None):
        """
        Safely associates an external account with the authenticated student.
        """
        norm_provider = provider_name.strip().capitalize() if provider_name else 'Coursera'
        now = datetime.datetime.utcnow()
        account = ExternalAccountService.get_account(student_usn, norm_provider)

        expires_at = None
        if expires_in:
            try:
                expires_at = now + datetime.timedelta(seconds=int(expires_in))
            except Exception:
                pass

        if not account:
            account = ExternalProviderAccount(
                student_usn=student_usn,
                provider_name=norm_provider,
                external_account_id=external_account_id,
                external_email=external_email,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=expires_at,
                connection_status='CONNECTED',
                last_synced_at=now,
                created_at=now,
                updated_at=now
            )
            db.session.add(account)
        else:
            account.external_account_id = external_account_id or account.external_account_id
            account.external_email = external_email or account.external_email
            if access_token:
                account.access_token = access_token
            if refresh_token:
                account.refresh_token = refresh_token
            if expires_at:
                account.token_expires_at = expires_at
            account.connection_status = 'CONNECTED'
            account.last_synced_at = now
            account.updated_at = now

        # Synchronize backward-compatible StudentPreference
        student = Student.query.filter_by(usn=student_usn).first()
        if student:
            if not student.preference:
                pref = StudentPreference(
                    student_usn=student_usn,
                    coursera_email=external_email or student.email,
                    coursera_connected=True,
                    coursera_connected_at=now
                )
                db.session.add(pref)
            else:
                student.preference.coursera_connected = True
                if external_email:
                    student.preference.coursera_email = external_email
                student.preference.coursera_connected_at = now

        # Audit log entry
        audit = AuditLog(
            student_usn=student_usn,
            changed_by=student_usn,
            action=f"{provider_name.upper()}_CONNECTED",
            details=f"Connected {provider_name} account ({external_email or 'OAuth Identity'})."
        )
        db.session.add(audit)
        db.session.commit()
        return account

    @staticmethod
    def disconnect_account(student_usn, provider_name='Coursera'):
        """
        Safely disconnects an external provider account and revokes stored tokens.
        """
        norm_provider = provider_name.strip().capitalize() if provider_name else 'Coursera'
        account = ExternalAccountService.get_account(student_usn, norm_provider)
        if account:
            account.connection_status = 'DISCONNECTED'
            account.access_token = None
            account.refresh_token = None
            account.updated_at = datetime.datetime.utcnow()

        # Update student preference
        student = Student.query.filter_by(usn=student_usn).first()
        if student and student.preference and norm_provider == 'Coursera':
            student.preference.coursera_connected = False

        audit = AuditLog(
            student_usn=student_usn,
            changed_by=student_usn,
            action=f"{norm_provider.upper()}_DISCONNECTED",
            details=f"Disconnected {norm_provider} account."
        )
        db.session.add(audit)
        db.session.commit()
        return True

    @staticmethod
    def get_connection_status(student_usn, provider_name='Coursera'):
        """
        Returns rich connection status dict for UI and API consumers.
        """
        norm_provider = provider_name.strip().capitalize() if provider_name else 'Coursera'
        client_id = os.environ.get(f'{norm_provider.upper()}_CLIENT_ID')
        account = ExternalAccountService.get_account(student_usn, norm_provider)

        is_connected = bool(account and account.connection_status == 'CONNECTED')
        oauth_configured = bool(client_id and client_id.strip())

        return {
            "provider": norm_provider,
            "is_connected": is_connected,
            "is_oauth_configured": oauth_configured,
            "status": account.connection_status if account else "NOT_CONNECTED",
            "connection_status": account.connection_status if account else "NOT_CONNECTED",
            "external_email": account.external_email if account else None,
            "external_account_id": account.external_account_id if account else None,
            "last_synced_at": account.last_synced_at.strftime('%d %b %Y, %H:%M') if (account and account.last_synced_at) else None,
            "integration_mode": "LIVE_OAUTH_SYNC" if (oauth_configured and is_connected) else (
                "CONNECTED_PROFILE_VERIFICATION" if is_connected else "DIRECT_CATALOG_FALLBACK"
            )
        }
