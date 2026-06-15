"""
SMTP-based Email Service for APF Portal
Replaces EmailJS with Django's built-in SMTP functionality
Uses HTML templates from authentication/templates/email/

Behaviour:
- If EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are set, sends real emails via
  Django's SMTP backend (regardless of EMAIL_BACKEND setting).
- Otherwise, falls back to printing the code to the server console so
  development/testing can proceed without SMTP credentials.
"""

import logging
import base64
import os
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils.html import strip_tags
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

def _get_logo_base64() -> str:
    """Return the APF logo as a base64 data URI (fallback only)."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(base_dir, 'media', 'logo.png')
    try:
        with open(logo_path, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        return f"data:image/png;base64,{encoded}"
    except Exception as e:
        logger.warning(f"Could not load logo for email: {e}")
        return ""


def _get_logo_url():
    """Return the absolute public URL for the APF logo."""
    frontend_url = getattr(settings, 'FRONTEND_URL', 'https://apfuganda.org').rstrip('/')
    return f"{frontend_url}/media/logo.png"


def _render_email(template_name: str, context: dict) -> str:
    """Render an email template, injecting the logo URL.
    
    Uses the live hosted URL — Gmail and most clients block data: URIs.
    Falls back to base64 only when FRONTEND_URL is localhost (dev mode).
    """
    if 'logo_url' not in context:
        logo_url = _get_logo_url()
        # On localhost the URL won't be reachable from email clients, use base64
        if 'localhost' in logo_url or '127.0.0.1' in logo_url:
            logo_url = _get_logo_base64() or logo_url
        context['logo_url'] = logo_url
    return render_to_string(template_name, context)


class EmailService:
    """Service for sending emails via SMTP with dev-mode console fallback"""

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _get_email_config():
        """Get email configuration from settings"""
        return {
            'host': getattr(settings, 'EMAIL_HOST', 'smtp.gmail.com'),
            'port': getattr(settings, 'EMAIL_PORT', 587),
            'use_tls': getattr(settings, 'EMAIL_USE_TLS', True),
            'username': getattr(settings, 'EMAIL_HOST_USER', ''),
            'password': getattr(settings, 'EMAIL_HOST_PASSWORD', ''),
            'timeout': getattr(settings, 'EMAIL_TIMEOUT', 10),
            'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@apfportal.com'),
        }

    @staticmethod
    def _is_smtp_configured():
        """Return True when current mail backend is ready for real sending."""
        backend = getattr(settings, 'EMAIL_BACKEND', '')
        if backend == 'utils.gmail_api_backend.EmailBackend':
            from pathlib import Path

            token_file = getattr(settings, 'GMAIL_TOKEN_FILE', 'token.json')
            token_path = Path(token_file)
            if not token_path.is_absolute():
                token_path = Path(getattr(settings, 'BASE_DIR', '.')) / token_file
            return token_path.exists()

        config = EmailService._get_email_config()
        return bool(config['username'] and config['password'])

    @staticmethod
    def _should_log_auth_tokens():
        """Explicit opt-in to mirror OTPs in server logs."""
        return bool(getattr(settings, 'LOG_AUTH_TOKENS', False))

    @staticmethod
    def _dev_log(label, to_email, code, user_name=''):
        """Print a clear console message so devs can grab the code"""
        print("\n" + "=" * 60)
        print(f"  [DEV MODE] {label}")
        print("=" * 60)
        print(f"  To:   {to_email}")
        if user_name:
            print(f"  User: {user_name}")
        print(f"  CODE: {code}")
        print("=" * 60 + "\n")
        logger.info(f"[DEV MODE] {label} — code {code} for {to_email} printed to console")

    @staticmethod
    def _get_smtp_connection():
        """
        Return the configured Django email connection.
        """
        return get_connection()

    @staticmethod
    def _create_html_email(subject, html_content, to_email):
        """
        Create an HTML email message
        
        Args:
            subject: Email subject
            html_content: HTML content of the email
            to_email: Recipient email address
            
        Returns:
            EmailMultiAlternatives object
        """
        config = EmailService._get_email_config()
        
        # Create plain text version by stripping HTML tags
        text_content = strip_tags(html_content)
        
        # Use project-configured email backend connection.
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=config['from_email'],
            to=[to_email],
            connection=EmailService._get_smtp_connection(),
        )
        
        # Attach HTML version
        email.attach_alternative(html_content, "text/html")
        
        return email

    # ------------------------------------------------------------------ #
    #  Public send methods
    # ------------------------------------------------------------------ #

    @staticmethod
    def send_otp_email(email, otp_code, user_name=None):
        """
        Send OTP email using SMTP
        
        Args:
            email: Recipient email address
            otp_code: 6-digit OTP code
            user_name: Optional user name for personalization
            
        Returns:
            Boolean indicating success or failure
        """
        try:
            if not user_name:
                user_name = email.split('@')[0]

            # Dev-mode fallback: print to console when SMTP is not configured
            if not EmailService._is_smtp_configured():
                EmailService._dev_log("Login OTP Email", email, otp_code, user_name)
                return True

            if EmailService._should_log_auth_tokens():
                EmailService._dev_log("Login OTP Email (Mirror Log)", email, otp_code, user_name)
            
            # Render HTML template for login OTP
            context = {
                'user_name': user_name,
                'otp_code': otp_code,
            }
            html_content = _render_email('email/otp_email.html', context)
            
            # Create and send email
            email_message = EmailService._create_html_email(
                subject="APF Portal - Your Login Verification Code",
                html_content=html_content,
                to_email=email
            )
            
            email_message.send(fail_silently=False)
            logger.info(f"OTP email sent successfully to {email} via SMTP")
            return True
            
        except Exception as e:
            logger.error(f"Error sending OTP email to {email}: {str(e)}")
            # Fall back to console so login still works during development
            print(f"\n[EMAIL ERROR] Could not send OTP to {email}: {e}")
            print(f"[FALLBACK] OTP CODE: {otp_code}\n")
            return True
    
    @staticmethod
    def send_password_reset_email(email, otp_code, user_name=None):
        """
        Send password reset OTP email using SMTP
        
        Args:
            email: Recipient email address
            otp_code: 6-digit OTP code for password reset
            user_name: Optional user name for personalization
            
        Returns:
            Boolean indicating success or failure
        """
        try:
            if not user_name:
                user_name = email.split('@')[0]

            if not EmailService._is_smtp_configured():
                EmailService._dev_log("Password Reset OTP Email", email, otp_code, user_name)
                return True

            if EmailService._should_log_auth_tokens():
                EmailService._dev_log("Password Reset OTP Email (Mirror Log)", email, otp_code, user_name)
            
            # Render HTML template for password reset
            context = {
                'user_name': user_name,
                'otp_code': otp_code,
            }
            html_content = _render_email('email/password_reset_email.html', context)
            
            # Create and send email
            email_message = EmailService._create_html_email(
                subject="APF Portal - Password Reset Verification Code",
                html_content=html_content,
                to_email=email
            )
            
            email_message.send(fail_silently=False)
            logger.info(f"Password reset email sent successfully to {email} via SMTP")
            return True
            
        except Exception as e:
            logger.error(f"Error sending password reset email to {email}: {str(e)}")
            print(f"\n[EMAIL ERROR] Could not send reset OTP to {email}: {e}")
            print(f"[FALLBACK] RESET CODE: {otp_code}\n")
            return True
    
    @staticmethod
    def send_approval_email(email, user_name=None, login_url=None, apf_membership_number=None):
        """
        Send member approval email using SMTP

        Args:
            email: Recipient email address
            user_name: Optional user name for personalization
            login_url: Optional login URL (defaults to FRONTEND_URL/login from settings)
            apf_membership_number: Optional APF membership number to include in the email

        Returns:
            Boolean indicating success or failure
        """
        try:
            if not user_name:
                user_name = email.split('@')[0]
            
            if not login_url:
                frontend_url = getattr(settings, 'FRONTEND_URL')
                login_url = f'{frontend_url}/login'

            if not EmailService._is_smtp_configured():
                EmailService._dev_log("Approval Email", email, f"login_url={login_url}", user_name)
                return True
            
            context = {
                'username': user_name,
                'member_email': email,
                'loginUrl': login_url,
                'apf_membership_number': apf_membership_number or '',
            }
            html_content = _render_email('email/approval_email.html', context)
            
            email_message = EmailService._create_html_email(
                subject="APF Portal - Membership Approved!",
                html_content=html_content,
                to_email=email
            )
            
            email_message.send(fail_silently=False)
            logger.info(f"Approval email sent successfully to {email} via SMTP")
            return True
            
        except Exception as e:
            logger.error(f"Error sending approval email to {email}: {str(e)}")
            return False

    @staticmethod
    def send_email_verification(email, verification_code, user_name=None, verification_url=None):
        """
        Send email verification code using SMTP
        
        Args:
            email: Recipient email address
            verification_code: 6-digit verification code
            user_name: Optional user name for personalization
            verification_url: Optional verification URL for one-click verification
            
        Returns:
            Boolean indicating success or failure
        """
        try:
            if not user_name:
                user_name = email.split('@')[0]

            if not EmailService._is_smtp_configured():
                EmailService._dev_log("Email Verification", email, verification_code, user_name)
                return True

            if EmailService._should_log_auth_tokens():
                EmailService._dev_log("Email Verification (Mirror Log)", email, verification_code, user_name)
            
            # Render HTML template for email verification
            context = {
                'user_name': user_name,
                'verification_code': verification_code,
                'verification_url': verification_url,
            }
            html_content = _render_email('email/email_verification.html', context)
            
            # Create and send email
            email_message = EmailService._create_html_email(
                subject="APF Portal - Verify Your Email Address",
                html_content=html_content,
                to_email=email
            )
            
            email_message.send(fail_silently=False)
            logger.info(f"Email verification sent successfully to {email} via SMTP")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email verification to {email}: {str(e)}")
            print(f"\n[EMAIL ERROR] Could not send verification to {email}: {e}")
            print(f"[FALLBACK] VERIFICATION CODE: {verification_code}\n")
            return True

    @staticmethod
    def send_temp_credentials_email(email, first_name, temp_password, login_url=None):
        """
        Send welcome email with temporary credentials to a bulk-registered member.

        Args:
            email: Recipient email address
            first_name: Member's first name
            temp_password: Generated temporary password
            login_url: Portal login URL (defaults to FRONTEND_URL/login)

        Returns:
            Boolean indicating success or failure
        """
        try:
            if not login_url:
                frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
                login_url = f'{frontend_url}/login'

            if not EmailService._is_smtp_configured():
                print("\n" + "=" * 60)
                print("  [DEV MODE] Bulk Registration Welcome Email")
                print("=" * 60)
                print(f"  To:       {email}")
                print(f"  Name:     {first_name}")
                print(f"  Password: {temp_password}")
                print(f"  Login:    {login_url}")
                print("=" * 60 + "\n")
                logger.info(f"[DEV MODE] Temp credentials for {email} printed to console")
                return True

            context = {
                'first_name': first_name,
                'email': email,
                'temp_password': temp_password,
                'login_url': login_url,
            }
            html_content = _render_email('email/bulk_registration_welcome.html', context)

            email_message = EmailService._create_html_email(
                subject="APF Portal - Your Account Has Been Created",
                html_content=html_content,
                to_email=email,
            )
            email_message.send(fail_silently=False)
            logger.info(f"Temp credentials email sent to {email}")
            return True

        except Exception as e:
            logger.error(f"Error sending temp credentials email to {email}: {str(e)}")
            return False

    @staticmethod
    def send_application_confirmation_email(email, user_name=None, application_id=None, submitted_at=None):
        """
        Send confirmation email to applicant after successful submission.

        Args:
            email: Recipient email address
            user_name: Applicant's name
            application_id: Application ID for reference
            submitted_at: Submission datetime string

        Returns:
            Boolean indicating success or failure
        """
        try:
            if not user_name:
                user_name = email.split('@')[0]

            if not EmailService._is_smtp_configured():
                print("\n" + "=" * 60)
                print("  [DEV MODE] Application Confirmation Email")
                print("=" * 60)
                print(f"  To:             {email}")
                print(f"  Name:           {user_name}")
                print(f"  Application ID: {application_id}")
                print("=" * 60 + "\n")
                return True

            context = {
                'user_name': user_name,
                'email': email,
                'application_id': application_id or 'N/A',
                'submitted_at': submitted_at or '',
            }
            html_content = _render_email('email/application_confirmation_email.html', context)

            email_message = EmailService._create_html_email(
                subject="APF Uganda – Application Received & Under Review",
                html_content=html_content,
                to_email=email,
            )
            email_message.send(fail_silently=False)
            logger.info(f"Application confirmation email sent to {email}")
            return True

        except Exception as e:
            logger.error(f"Error sending application confirmation email to {email}: {str(e)}")
            return False

    @staticmethod
    def send_renewal_reminder_email(email, user_name=None, due_date=None, days_remaining=0, renewal_url=None):
        """Send membership renewal reminder email."""
        try:
            if not user_name:
                user_name = email.split('@')[0]
            if not renewal_url:
                frontend_url = getattr(settings, 'FRONTEND_URL', 'https://apfuganda.org').rstrip('/')
                renewal_url = f"{frontend_url}/payments"

            if not EmailService._is_smtp_configured():
                print(f"\n[DEV MODE] Renewal reminder to {email} — {days_remaining} days remaining\n")
                return True

            context = {
                'user_name': user_name,
                'email': email,
                'due_date': due_date or '',
                'days_remaining': days_remaining,
                'renewal_url': renewal_url,
            }
            html_content = _render_email('email/renewal_reminder_email.html', context)
            subject = (
                f"APF Uganda – Membership Renewal Due in {days_remaining} Day{'s' if days_remaining != 1 else ''}"
                if days_remaining > 0
                else "APF Uganda – Membership Renewal Overdue"
            )
            email_message = EmailService._create_html_email(subject, html_content, email)
            email_message.send(fail_silently=False)
            logger.info(f"Renewal reminder sent to {email} ({days_remaining} days remaining)")
            return True
        except Exception as e:
            logger.error(f"Error sending renewal reminder to {email}: {str(e)}")
            return False

    @staticmethod
    def send_suspension_email(email, user_name=None, reason=None, suspended_at=None, renewal_url=None):
        """Send account suspension notification email with renewal link."""
        try:
            if not user_name:
                user_name = email.split('@')[0]
            if not renewal_url:
                frontend_url = getattr(settings, 'FRONTEND_URL', 'https://apfuganda.org').rstrip('/')
                renewal_url = f"{frontend_url}/payments"

            if not EmailService._is_smtp_configured():
                print(f"\n[DEV MODE] Suspension email to {email} — reason: {reason}\n")
                return True

            context = {
                'user_name': user_name,
                'email': email,
                'reason': reason or 'Non-payment of annual subscription fee',
                'suspended_at': suspended_at or '',
                'renewal_url': renewal_url,
            }
            html_content = _render_email('email/suspension_email.html', context)
            email_message = EmailService._create_html_email(
                "APF Uganda – Your Account Has Been Suspended",
                html_content,
                email,
            )
            email_message.send(fail_silently=False)
            logger.info(f"Suspension email sent to {email}")
            return True
        except Exception as e:
            logger.error(f"Error sending suspension email to {email}: {str(e)}")
            return False

    @staticmethod
    def send_non_payment_suspension_email(email, user_name=None, reason=None, suspended_at=None, renewal_url=None):
        """Send non-payment suspension email with clear renewal CTA."""
        try:
            if not user_name:
                user_name = email.split('@')[0]
            if not renewal_url:
                frontend_url = getattr(settings, 'FRONTEND_URL', 'https://apfuganda.org').rstrip('/')
                renewal_url = f"{frontend_url}/payments"

            if not EmailService._is_smtp_configured():
                print(f"\n[DEV MODE] Non-payment suspension email to {email}\n")
                return True

            context = {
                'user_name': user_name,
                'email': email,
                'reason': reason or 'Non-payment of annual subscription fee',
                'suspended_at': suspended_at or '',
                'renewal_url': renewal_url,
            }
            html_content = _render_email('email/suspension_non_payment_email.html', context)
            email_message = EmailService._create_html_email(
                "APF Uganda – Account Suspended: Renew to Reactivate",
                html_content,
                email,
            )
            email_message.send(fail_silently=False)
            logger.info(f"Non-payment suspension email sent to {email}")
            return True
        except Exception as e:
            logger.error(f"Error sending non-payment suspension email to {email}: {str(e)}")
            return False

    @staticmethod
    def send_reactivation_email(email, user_name=None, dashboard_url=None):
        """Send account reactivation confirmation email."""
        try:
            if not user_name:
                user_name = email.split('@')[0]
            if not dashboard_url:
                frontend_url = getattr(settings, 'FRONTEND_URL', 'https://apfuganda.org').rstrip('/')
                dashboard_url = f"{frontend_url}/dashboard"

            if not EmailService._is_smtp_configured():
                print(f"\n[DEV MODE] Reactivation email to {email}\n")
                return True

            context = {'user_name': user_name, 'email': email, 'dashboard_url': dashboard_url}
            html_content = _render_email('email/reactivation_email.html', context)
            email_message = EmailService._create_html_email(
                "APF Uganda – Your Account Has Been Reactivated",
                html_content,
                email,
            )
            email_message.send(fail_silently=False)
            logger.info(f"Reactivation email sent to {email}")
            return True
        except Exception as e:
            logger.error(f"Error sending reactivation email to {email}: {str(e)}")
            return False
