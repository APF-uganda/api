"""
Script to send account creation notification emails to all APF members.
Run inside the apf_backend Docker container:

    docker exec -it apf_backend python notify_apf_members.py

This uses the same SMTP email infrastructure as the rest of the application.
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

# All member emails from the register (same list as create_apf_members.py)
MEMBER_EMAILS = [
    "kherman32@gmail.com",
    "patrickmugarura10@yahoo.com",
    "gkkakala@gmail.com",
    "constant.mayende@gmail.com",
    "r.albert.otete@gmail.com",
    "maria@springstugye.com",
    "nuwamanyageoffrey@gmail.com",
    "rmutumba@mutumbamukobe.org",
    "emojongodeke@gmail.com",
    "mante@continentalpartners.org",
    "justin@osillocpa.com",
    "senogaassociates@gmail.com",
    "michael@springstugye.com",
    "a.arnold@ardenfield.com",
    "a.dennis@ardenfield.com",
    "pius.ssuuna@gmail.com",
    "rhodaochan@gmail.com",
    "annetnantumbwe1@gmail.com",
    "ochanbernard@gmail.com",
    "sekiziyivuissa@gmail.com",
    "msilverboss@gmail.com",
    "muke280@gmail.com",
    "lmawanda45@gmail.com",
    "kalindaassociates@gmail.com",
    "chrisnet4@gmail.com",
    "info@pepartnersuganda.com",
    "jay.oriekot@gmail.com",
    "rwomus.stepehn@gmail.com",
    "annerozbob1@gmail.com",
    "abdul@springstugye.com",
    "pkbanadda@gmail.com",
    "woodhask.ediomu@woodhask.com",
    "biz.bizandcompany@gmail.com",
    "glutwama@gmail.com",
    "dssebugwawo@gmail.com",
    "arch.archelia@gmail.com",
    "kabuchualfred@gmail.com",
    "jbmwanja@gmail.com",
    "gadzk@yahoo.com",
    "otimotile@yahoo.com",
    "rmatsiko89@gmail.com",
    "davidssenoga@gmail.com",
    "bwireb@gmail.com",
    "thomsonkwizina@gmail.com",
    "mwagodassociates@gmail.com",
    "jamiekasule@yahoo.com",
    "peterkasango1@gmail.com",
    "marknsubugacpa@gmail.com",
    "rwebishugi@gmail.com",
    "basiima55@yahoo.co.uk",
    "fmtwine@gmail.com",
    "kasawulibaker@gmail.com",
    "rkyalimpa@gmail.com",
    "manyiredith@gmail.com",
    "sgabula2001@yahoo.co.uk",
]

# Delay between emails (seconds) to avoid being flagged as spam
EMAIL_DELAY = 2


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


def notify_all_members():
    sent = 0
    skipped = 0
    errors = 0

    print("=" * 60)
    print("APF Member Account Notification Script")
    print("=" * 60)

    for email in MEMBER_EMAILS:
        email = email.strip().lower()

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            print(f"  SKIP (no account): {email}")
            skipped += 1
            continue

        try:
            send_notification(user)
            print(f"  SENT: {email} ({user.first_name} {user.last_name})")
            sent += 1
            # Throttle to avoid spam filters
            if EMAIL_DELAY > 0:
                time.sleep(EMAIL_DELAY)
        except Exception as e:
            print(f"  ERROR: {email} - {e}")
            errors += 1

    print()
    print("=" * 60)
    print(f"Done. Sent: {sent} | Skipped: {skipped} | Errors: {errors}")
    print("=" * 60)


if __name__ == "__main__":
    notify_all_members()
