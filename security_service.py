"""
Security & Credential Management Service for MIT Placement Portal
Handles secure password changes, recovery email/mobile settings, forgot password workflows,
and security audit logging for Placement Administrator, Placement Coordinator, and Department HODs.
"""

import os
import re
import secrets
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Admin, PasswordResetToken, SecurityAuditLog

class SecurityService:
    RESET_TOKEN_EXPIRY_MINUTES = 15
    MIN_PASSWORD_LENGTH = 8

    @classmethod
    def log_security_event(cls, user_type, user_identifier, event_type, status='SUCCESS', ip_address=None, details=None):
        """Records an immutable security audit trail entry."""
        try:
            audit = SecurityAuditLog(
                user_type=user_type,
                user_identifier=str(user_identifier),
                event_type=event_type,
                status=status,
                ip_address=ip_address,
                details=details,
                timestamp=datetime.utcnow()
            )
            db.session.add(audit)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Failed to record security audit log: {e}")

    @classmethod
    def validate_password_strength(cls, password):
        """
        Validates password strength:
        - Minimum 8 characters
        - At least one letter and at least one number or special character
        """
        if not password or len(password) < cls.MIN_PASSWORD_LENGTH:
            return False, f"Password must be at least {cls.MIN_PASSWORD_LENGTH} characters long."
        if not re.search(r'[A-Za-z]', password):
            return False, "Password must contain at least one letter."
        if not re.search(r'[\d\W_]', password):
            return False, "Password must contain at least one number or special character."
        return True, ""

    @classmethod
    def change_admin_password(cls, admin, current_password, new_password, confirm_password, ip_address=None):
        """
        Securely changes an administrator's password after verifying identity.
        Increments session_version to invalidate old sessions across all devices.
        """
        if not admin:
            return False, "Administrator account not found."

        # 1. Identity re-authentication
        if not admin.check_password(current_password):
            cls.log_security_event(
                user_type=admin.role,
                user_identifier=admin.username,
                event_type='PASSWORD_CHANGE_FAILED',
                status='FAILED',
                ip_address=ip_address,
                details='Invalid current password supplied during password change'
            )
            return False, "Current password verification failed. Please enter your correct current password."

        # 2. Confirm matching
        if new_password != confirm_password:
            return False, "New password and confirmation password do not match."

        # 3. Disallow re-using current password
        if current_password == new_password:
            return False, "New password cannot be the same as your current password."

        # 4. Strength validation
        is_strong, reason = cls.validate_password_strength(new_password)
        if not is_strong:
            return False, reason

        # 5. Set new password, increment session_version (session revocation)
        admin.set_password(new_password)
        cls.log_security_event(
            user_type=admin.role,
            user_identifier=admin.username,
            event_type='PASSWORD_CHANGED',
            status='SUCCESS',
            ip_address=ip_address,
            details=f"Password updated successfully. Session version incremented to {admin.session_version}."
        )
        db.session.commit()
        return True, "Your password has been changed successfully. All other active sessions have been invalidated."

    @classmethod
    def update_admin_username(cls, admin, new_username, current_password, ip_address=None):
        """
        Updates an administrator's username after identity verification.
        Validates format and uniqueness.
        """
        if not admin:
            return False, "Administrator account not found."

        # 1. Identity verification
        if not admin.check_password(current_password):
            return False, "Current password verification failed. Identity could not be confirmed."

        clean_user = new_username.strip()
        if not clean_user or len(clean_user) < 3:
            return False, "Username must be at least 3 characters long."
        if not re.match(r'^[a-zA-Z0-9_.-]+$', clean_user):
            return False, "Username may only contain letters, numbers, underscores, dots, and hyphens."

        # Check existing
        existing = Admin.query.filter(Admin.username.ilike(clean_user)).first()
        if existing and existing.id != admin.id:
            return False, f"Username '{clean_user}' is already taken by another account."

        old_user = admin.username
        admin.username = clean_user
        cls.log_security_event(
            user_type=admin.role,
            user_identifier=clean_user,
            event_type='USERNAME_CHANGED',
            status='SUCCESS',
            ip_address=ip_address,
            details=f"Username changed from '{old_user}' to '{clean_user}'"
        )
        db.session.commit()
        return True, f"Username updated to '{clean_user}' successfully."

    @classmethod
    def update_recovery_settings(cls, admin, recovery_email, recovery_mobile, ip_address=None):
        """
        Updates recovery email and recovery mobile number for password recovery.
        """
        if not admin:
            return False, "Administrator account not found."

        clean_email = recovery_email.strip().lower() if recovery_email else None
        clean_mobile = re.sub(r'\D', '', str(recovery_mobile).strip()) if recovery_mobile else None
        if clean_mobile and len(clean_mobile) > 10:
            clean_mobile = clean_mobile[-10:]

        if clean_email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', clean_email):
            return False, "Invalid recovery email address format."

        if clean_mobile and len(clean_mobile) != 10:
            return False, "Recovery mobile number must be 10 digits."

        admin.recovery_email = clean_email
        admin.recovery_mobile = clean_mobile
        admin.is_recovery_email_verified = True if clean_email else False
        admin.is_recovery_mobile_verified = True if clean_mobile else False

        cls.log_security_event(
            user_type=admin.role,
            user_identifier=admin.username,
            event_type='RECOVERY_SETTINGS_UPDATED',
            status='SUCCESS',
            ip_address=ip_address,
            details=f"Recovery settings updated: email={clean_email or 'None'}, mobile={clean_mobile or 'None'}"
        )
        db.session.commit()
        return True, "Recovery settings have been updated successfully."

    @classmethod
    def initiate_password_recovery(cls, identifier, method='EMAIL', ip_address=None):
        """
        Initiates password recovery for an administrator, coordinator, or HOD.
        Supports recovery via registered recovery email or recovery mobile.
        Never reveals whether the account exists in public messages.
        Returns: (success: bool, generic_message: str, dev_token_preview: str or None)
        """
        clean_id = identifier.strip().lower() if identifier else ""
        generic_msg = "If a matching privileged account with configured recovery settings exists, a time-limited verification code has been dispatched."

        if not clean_id:
            return True, generic_msg, None

        # Search for admin by username, recovery_email, or recovery_mobile
        clean_phone = re.sub(r'\D', '', clean_id)
        last10 = clean_phone[-10:] if len(clean_phone) >= 10 else clean_phone

        admin = Admin.query.filter(
            (Admin.username.ilike(clean_id)) |
            (db.func.lower(Admin.recovery_email) == clean_id) |
            (Admin.recovery_mobile == last10)
        ).first()

        if not admin:
            cls.log_security_event(
                user_type='UNKNOWN',
                user_identifier=clean_id,
                event_type='RECOVERY_REQUESTED_UNKNOWN',
                status='BLOCKED',
                ip_address=ip_address,
                details=f"Password recovery requested for non-existent account identifier '{clean_id}'"
            )
            return True, generic_msg, None

        # Invalidate any old unused reset tokens for this admin
        PasswordResetToken.query.filter_by(admin_id=admin.id, is_used=False).update({
            'is_used': True,
            'used_at': datetime.utcnow()
        })

        # Generate secure 6-digit recovery OTP / token
        token_str = f"{secrets.randbelow(900000) + 100000:06d}"
        token_hash = generate_password_hash(token_str)
        expires_at = datetime.utcnow() + timedelta(minutes=cls.RESET_TOKEN_EXPIRY_MINUTES)

        reset_record = PasswordResetToken(
            admin_id=admin.id,
            token_hash=token_hash,
            method=method,
            expires_at=expires_at,
            is_used=False,
            created_at=datetime.utcnow()
        )
        db.session.add(reset_record)

        cls.log_security_event(
            user_type=admin.role,
            user_identifier=admin.username,
            event_type='RECOVERY_CODE_GENERATED',
            status='SUCCESS',
            ip_address=ip_address,
            details=f"Password recovery code generated via {method}. Valid for {cls.RESET_TOKEN_EXPIRY_MINUTES} mins."
        )
        db.session.commit()

        # Development/Console notification
        print(f"\n=======================================================")
        print(f"[ADMIN PASSWORD RECOVERY] MIT Placement Security Service")
        print(f"Target Account: {admin.username} ({admin.role})")
        print(f"Recovery Code: {token_str}")
        print(f"Expires at: {expires_at.strftime('%H:%M:%S UTC')}")
        print(f"=======================================================\n")

        dev_preview = None
        if os.environ.get('FLASK_ENV') != 'production':
            dev_preview = token_str

        return True, generic_msg, dev_preview

    @classmethod
    def verify_and_reset_password(cls, identifier, recovery_code, new_password, confirm_password, ip_address=None):
        """
        Verifies recovery code and resets the administrator's password.
        """
        clean_id = identifier.strip().lower() if identifier else ""
        clean_code = recovery_code.strip() if recovery_code else ""

        if not clean_id or not clean_code:
            return False, "Account identifier and recovery code are required."

        if new_password != confirm_password:
            return False, "New password and confirmation password do not match."

        is_strong, reason = cls.validate_password_strength(new_password)
        if not is_strong:
            return False, reason

        # Find admin
        clean_phone = re.sub(r'\D', '', clean_id)
        last10 = clean_phone[-10:] if len(clean_phone) >= 10 else clean_phone
        admin = Admin.query.filter(
            (Admin.username.ilike(clean_id)) |
            (db.func.lower(Admin.recovery_email) == clean_id) |
            (Admin.recovery_mobile == last10)
        ).first()

        if not admin:
            return False, "Invalid account identifier or recovery code."

        # Find active reset token
        now = datetime.utcnow()
        active_tokens = PasswordResetToken.query.filter_by(
            admin_id=admin.id,
            is_used=False
        ).order_by(PasswordResetToken.created_at.desc()).all()

        valid_token = None
        for t in active_tokens:
            if now <= t.expires_at and check_password_hash(t.token_hash, clean_code):
                valid_token = t
                break

        if not valid_token:
            cls.log_security_event(
                user_type=admin.role,
                user_identifier=admin.username,
                event_type='PASSWORD_RESET_FAILED',
                status='FAILED',
                ip_address=ip_address,
                details='Invalid or expired recovery code supplied'
            )
            return False, "Invalid or expired recovery code. Please request a new code."

        # Mark token used
        valid_token.is_used = True
        valid_token.used_at = now

        # Update password and revoke sessions
        admin.set_password(new_password)

        cls.log_security_event(
            user_type=admin.role,
            user_identifier=admin.username,
            event_type='PASSWORD_RESET_COMPLETED',
            status='SUCCESS',
            ip_address=ip_address,
            details='Password successfully reset via verified recovery code. Sessions revoked.'
        )
        db.session.commit()
        return True, "Your password has been reset successfully. You can now log in with your new credentials."
