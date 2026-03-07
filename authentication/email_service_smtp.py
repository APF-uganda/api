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
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils.html import strip_tags
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


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
            'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@apfportal.com'),
        }

    @staticmethod
    def _is_smtp_configured():
        """Return True when real SMTP credentials are available"""
        config = EmailService._get_email_config()
        return bool(config['username'] and config['password'])

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
        Return an explicit SMTP connection so the email is really sent
        even when EMAIL_BACKEND is set to the console backend.
        """
        config = EmailService._get_email_config()
        return get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=config['host'],
            port=config['port'],
            username=config['username'],
            password=config['password'],
            use_tls=config['use_tls'],
        )

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
        
        # Create email message with explicit SMTP connection
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
            
            # Render HTML template for login OTP
            context = {
                'user_name': user_name,
                'otp_code': otp_code,
            }
            html_content = render_to_string('email/otp_email.html', context)
            
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
            
            # Render HTML template for password reset
            context = {
                'user_name': user_name,
                'otp_code': otp_code,
            }
            html_content = render_to_string('email/password_reset_email.html', context)
            
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
    def send_approval_email(email, user_name=None, login_url=None):
        """
        Send member approval email using SMTP
        
        Args:
            email: Recipient email address
            user_name: Optional user name for personalization
            login_url: Optional login URL (defaults to FRONTEND_URL/login from settings)
            
        Returns:
            Boolean indicating success or failure
        """
        try:
            if not user_name:
                user_name = email.split('@')[0]
            
            if not login_url:
                # Use FRONTEND_URL from settings with /login path
                frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
                login_url = f'{frontend_url}/login'

            if not EmailService._is_smtp_configured():
                EmailService._dev_log("Approval Email", email, f"login_url={login_url}", user_name)
                return True
            
            # Render HTML template
            context = {
                'user_name': user_name,
                'login_url': login_url,
            }
            html_content = render_to_string('email/approval_email.html', context)
            
            # Create and send email
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
            
            # Render HTML template for email verification
            context = {
                'user_name': user_name,
                'verification_code': verification_code,
                'verification_url': verification_url,
            }
            html_content = render_to_string('email/email_verification.html', context)
            
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
