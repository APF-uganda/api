"""
Test script for notification emails - creates 3 test accounts,
sends real emails to them, then cleans up.

Run inside the apf_backend Docker container:

    docker exec -it apf_backend python test_notify_members.py

This will send REAL emails to:
  - bashkiko@gmail.com
  - kikomusa29@gmail.com
  - musbash29@gmail.com

Check those inboxes (and spam folders) to verify the emails arrived.
"""
import os
import sys
import time
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.settings")
django.setup()

import logging
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from authentication.email_service_smtp import EmailService

User = get_user_model()
logger = logging.getLogger(__name__)

DEFAULT_PASSWORD = "Apf@uganda"
EMAIL_DELAY = 2

TEST_MEMBERS = [
    ("bashkiko@gmail.com", "Bashkiko", "Test"),
    ("kikomusa29@gmail.com", "Kikomusa", "Test"),
    ("musbash29@gmail.com", "Musbash", "Test"),
]


def cleanup_test_users():
    for email, *_ in TEST_MEMBERS:
        User.objects.filter(email__iexact=email).delete()


def create_test_users():
    """Create temporary test accounts."""
    print("=" * 60)
    print("SETUP: Creating test accounts")
    print("=" * 60)

    cleanup_test_users()

    for email, first_name, last_name in TEST_MEMBERS:
        user = User.objects.create_user(
            email=email,
            password=DEFAULT_PASSWORD,
            first_name=first_name,
            last_name=last_name,
            gender="male",
            role="2",
            is_active=True,
            organization="Test Firm",
            job_title="Test Partner",
        )
        print(f"  CREATED: {email}")


def send_notification(user):
    """Send account created notification email to a single user."""
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://apfug.org')
    login_url = f'{frontend_url}/login'

    user_name = user.first_name or user.email.split('@')[0]

    context = {
        'user_name': user_name,
        'email': user.email,
        'password': DEFAULT_PASSWORD,
        'login_url': login_url,
    }

    html_content = render_to_string('email/account_created_email.html', context)

    email_message = EmailService._create_html_email(
        subject="APF Portal - Your Account Has Been Created",
        html_content=html_content,
        to_email=user.email,
    )

    email_message.send(fail_silently=False)
    return True


def test_send_emails():
    print()
    print("=" * 60)
    print("TEST: Sending notification emails")
    print("=" * 60)

    sent = 0
    errors = 0

    for email, *_ in TEST_MEMBERS:
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            print(f"  SKIP (no account): {email}")
            continue

        try:
            send_notification(user)
            print(f"  SENT: {email}")
            sent += 1
            if EMAIL_DELAY > 0:
                time.sleep(EMAIL_DELAY)
        except Exception as e:
            print(f"  ERROR: {email} - {e}")
            errors += 1

    print()
    print(f"  -> Sent: {sent} | Errors: {errors}")
    return sent == 3 and errors == 0


def run_test():
    print()
    print("*" * 60)
    print("  APF Notification Email Test")
    print("  Sending REAL emails to test inboxes")
    print("*" * 60)
    print()

    try:
        create_test_users()
        email_success = test_send_emails()
    except Exception as e:
        print(f"\n  FATAL ERROR: {e}")
        email_success = False
    finally:
        print()
        print("=" * 60)
        print("CLEANUP: Removing test accounts")
        print("=" * 60)
        cleanup_test_users()
        for email, *_ in TEST_MEMBERS:
            exists = User.objects.filter(email__iexact=email).exists()
            status = "FAIL (still exists)" if exists else "OK (removed)"
            print(f"  {status}: {email}")

    print()
    print("=" * 60)
    if email_success:
        print("RESULT: ALL EMAILS SENT SUCCESSFULLY")
        print("Check these inboxes (and spam folders):")
        for email, *_ in TEST_MEMBERS:
            print(f"  - {email}")
    else:
        print("RESULT: SOME EMAILS FAILED - check errors above")
    print("=" * 60)

    return email_success


if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
