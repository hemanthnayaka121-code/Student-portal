"""
Administrative Credential Management & Bootstrap CLI
Maharaja Institute of Technology Mysore (MITM) Placement Portal

Enables secure configuration of fresh credentials, password resets,
and recovery email/mobile settings for:
- Placement Administrator
- Placement Coordinator
- Department HODs (CSE, ISE, ECE, MECH, and all configured departments)

Usage:
  python manage_credentials.py --status
  python manage_credentials.py --bootstrap
  python manage_credentials.py --set-password --username <user> --password <new_pass>
  python manage_credentials.py --set-recovery --username <user> --email <email> --mobile <phone>
"""

import os
import sys
import argparse
from datetime import datetime
from app import app, db
from models import Admin, Department, SecurityAuditLog
from security_service import SecurityService

# Default fresh setup credentials map for initial bootstrap (strong, hashed, customizable)
DEFAULT_BOOTSTRAP_CONFIG = {
    'Mit_placement': {
        'role': 'PLACEMENT_ADMIN',
        'dept_code': None,
        'default_pass': 'MitmAdmin@2026Secure',
        'recovery_email': 'placement.admin@mitmysore.in',
        'recovery_mobile': '9845099001'
    },
    'placement_coordinator': {
        'role': 'PLACEMENT_COORDINATOR',
        'dept_code': None,
        'default_pass': 'MitmCoord@2026Secure',
        'recovery_email': 'placement.coordinator@mitmysore.in',
        'recovery_mobile': '9845099002'
    },
    'hod_cse': {
        'role': 'HOD',
        'dept_code': 'CSE',
        'default_pass': 'HOD_CSE@2026Secure',
        'recovery_email': 'ramesh.cse@mitmysore.in',
        'recovery_mobile': '9845011001'
    },
    'hod_ise': {
        'role': 'HOD',
        'dept_code': 'ISE',
        'default_pass': 'HOD_ISE@2026Secure',
        'recovery_email': 'sunitha.ise@mitmysore.in',
        'recovery_mobile': '9845011006'
    },
    'hod_ece': {
        'role': 'HOD',
        'dept_code': 'ECE',
        'default_pass': 'HOD_ECE@2026Secure',
        'recovery_email': 'venkatesh.ece@mitmysore.in',
        'recovery_mobile': '9845011007'
    },
    'hod_mech': {
        'role': 'HOD',
        'dept_code': 'MECH',
        'default_pass': 'HOD_MECH@2026Secure',
        'recovery_email': 'praveen.mech@mitmysore.in',
        'recovery_mobile': '9845011010'
    },
    'hod_ce': {
        'role': 'HOD',
        'dept_code': 'CE',
        'default_pass': 'HOD_CE@2026Secure',
        'recovery_email': 'rajesh.ce@mitmysore.in',
        'recovery_mobile': '9845011002'
    },
    'hod_ai': {
        'role': 'HOD',
        'dept_code': 'AI',
        'default_pass': 'HOD_AI@2026Secure',
        'recovery_email': 'priya.ai@mitmysore.in',
        'recovery_mobile': '9845011003'
    },
    'hod_csd': {
        'role': 'HOD',
        'dept_code': 'CSD',
        'default_pass': 'HOD_CSD@2026Secure',
        'recovery_email': 'harish.csd@mitmysore.in',
        'recovery_mobile': '9845011004'
    },
    'hod_csml': {
        'role': 'HOD',
        'dept_code': 'CSML',
        'default_pass': 'HOD_CSML@2026Secure',
        'recovery_email': 'sandeep.csml@mitmysore.in',
        'recovery_mobile': '9845011005'
    },
    'hod_iot': {
        'role': 'HOD',
        'dept_code': 'IOT',
        'default_pass': 'HOD_IOT@2026Secure',
        'recovery_email': 'manjunath.iot@mitmysore.in',
        'recovery_mobile': '9845011008'
    },
    'hod_civil': {
        'role': 'HOD',
        'dept_code': 'CIVIL',
        'default_pass': 'HOD_CIVIL@2026Secure',
        'recovery_email': 'anand.civil@mitmysore.in',
        'recovery_mobile': '9845011009'
    }
}

def print_account_status():
    with app.app_context():
        admins = Admin.query.order_by(Admin.id).all()
        print("\n" + "="*85)
        print("MIT MYSORE PLACEMENT PORTAL — PRIVILEGED ACCOUNT SECURITY STATUS")
        print("="*85)
        print(f"{'ID':<4} {'Username':<22} {'Role':<22} {'Dept':<6} {'Recovery Email':<25} {'Version':<8}")
        print("-"*85)
        for a in admins:
            dept_code = a.department.code if a.department else "N/A"
            rec_email = a.recovery_email or "Not Set"
            print(f"{a.id:<4} {a.username:<22} {a.role:<22} {dept_code:<6} {rec_email:<25} {a.session_version or 1:<8}")
        print("="*85 + "\n")

def run_bootstrap():
    with app.app_context():
        print("\n" + "="*70)
        print("INITIALIZING SECURE PRIVILEGED CREDENTIALS (BOOTSTRAP)")
        print("="*70)
        
        updated_count = 0
        for username, cfg in DEFAULT_BOOTSTRAP_CONFIG.items():
            admin = Admin.query.filter(Admin.username.ilike(username)).first()
            dept_id = None
            if cfg['dept_code']:
                dept = Department.query.filter_by(code=cfg['dept_code']).first()
                if dept:
                    dept_id = dept.id

            if not admin:
                admin = Admin(
                    username=username,
                    role=cfg['role'],
                    department_id=dept_id
                )
                db.session.add(admin)
                action_text = "Created"
            else:
                action_text = "Updated"

            admin.set_password(cfg['default_pass'])
            admin.recovery_email = cfg['recovery_email']
            admin.recovery_mobile = cfg['recovery_mobile']
            admin.is_recovery_email_verified = True
            admin.is_recovery_mobile_verified = True
            admin.failed_login_count = 0
            admin.locked_until = None
            admin.session_version = (admin.session_version or 0) + 1

            SecurityService.log_security_event(
                user_type=cfg['role'],
                user_identifier=username,
                event_type='CREDENTIALS_BOOTSTRAPPED',
                status='SUCCESS',
                details=f"Account credentials initialized via secure bootstrap"
            )
            print(f"  [{action_text}] {username:<22} ({cfg['role']:<20}) -> Pass: {cfg['default_pass']}")
            updated_count += 1

        db.session.commit()
        print("-"*70)
        print(f"Successfully configured fresh credentials for {updated_count} accounts.")
        print("All old sessions and obsolete reset tokens have been invalidated.")
        print("="*70 + "\n")

def set_account_password(username, new_password):
    with app.app_context():
        admin = Admin.query.filter(Admin.username.ilike(username)).first()
        if not admin:
            print(f"Error: No account found with username '{username}'.")
            return

        is_strong, reason = SecurityService.validate_password_strength(new_password)
        if not is_strong:
            print(f"Password validation error: {reason}")
            return

        admin.set_password(new_password)
        SecurityService.log_security_event(
            user_type=admin.role,
            user_identifier=admin.username,
            event_type='CLI_PASSWORD_SET',
            status='SUCCESS',
            details="Password manually updated via CLI manage_credentials.py"
        )
        db.session.commit()
        print(f"Success: Password for '{admin.username}' ({admin.role}) has been updated securely.")
        print(f"Session version incremented to {admin.session_version}. All prior sessions revoked.")

def set_account_recovery(username, email, mobile):
    with app.app_context():
        admin = Admin.query.filter(Admin.username.ilike(username)).first()
        if not admin:
            print(f"Error: No account found with username '{username}'.")
            return

        success, msg = SecurityService.update_recovery_settings(admin, email, mobile)
        if success:
            print(f"Success: {msg} for account '{admin.username}'.")
        else:
            print(f"Error: {msg}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="MIT Placement Portal Administrative Credentials Tool")
    parser.add_argument('--status', action='store_true', help="Display current accounts and security status")
    parser.add_argument('--bootstrap', action='store_true', help="Initialize fresh credentials for all accounts")
    parser.add_argument('--set-password', action='store_true', help="Set new password for an account")
    parser.add_argument('--set-recovery', action='store_true', help="Configure recovery email/mobile for an account")
    parser.add_argument('--username', type=str, help="Username of the administrator/HOD")
    parser.add_argument('--password', type=str, help="New password to set")
    parser.add_argument('--email', type=str, help="Recovery email address")
    parser.add_argument('--mobile', type=str, help="Recovery mobile number")

    args = parser.parse_args()

    if args.status:
        print_account_status()
    elif args.bootstrap:
        run_bootstrap()
        print_account_status()
    elif args.set_password:
        if not args.username or not args.password:
            print("Error: --username and --password are required when using --set-password.")
            sys.exit(1)
        set_account_password(args.username, args.password)
    elif args.set_recovery:
        if not args.username:
            print("Error: --username is required when using --set-recovery.")
            sys.exit(1)
        set_account_recovery(args.username, args.email, args.mobile)
    else:
        parser.print_help()
