"""
Email service for sending OTP and password reset emails
Automatically switches between console logging (development) and actual email sending (production)
"""
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending emails with automatic dev/prod switching
    - Development: Logs to console only
    - Production: Sends actual emails via SMTP
    """
    
    @staticmethod
    def is_development():
        """Check if we're in development mode"""
        return settings.DEBUG or settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend'
    
    @staticmethod
    def send_otp_email(user_email: str, otp_code: str, user_name: str = None) -> bool:
        """
        Send OTP email to user
        
        Args:
            user_email: Recipient email address
            otp_code: The OTP code to send
            user_name: User's display name (optional)
            
        Returns:
            bool: True if email was sent/logged successfully
        """
        try:
            if not user_name:
                user_name = user_email.split('@')[0]
            
            subject = 'Your APF Portal Login Code'
            
            # Create email content
            message = f"""
Hello {user_name},

Your One-Time Password (OTP) for APF Portal login is:

{otp_code}

This code will expire in 15 minutes.

If you didn't request this code, please ignore this email.

Best regards,
APF Portal Team
"""
            
            # In development mode, log to console with clear formatting
            if EmailService.is_development():
                logger.info("\n" + "="*60)
                logger.info("📧 [DEVELOPMENT MODE] OTP Email (Console Only)")
                logger.info("="*60)
                logger.info(f"To: {user_email}")
                logger.info(f"User: {user_name}")
                logger.info(f"Subject: {subject}")
                logger.info("-"*60)
                logger.info(f"OTP CODE: {otp_code}")
                logger.info("-"*60)
                logger.info("✅ Email logged to console (not sent)")
                logger.info("="*60 + "\n")
                
                # Also print to console for visibility
                print("\n" + "="*60)
                print("📧 [DEVELOPMENT MODE] OTP Email")
                print("="*60)
                print(f"To: {user_email}")
                print(f"OTP CODE: {otp_code}")
                print("="*60 + "\n")
                
                return True
            
            # In production mode, send actual email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                fail_silently=False,
            )
            
            logger.info(f"✅ OTP email sent successfully to {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending OTP email to {user_email}: {str(e)}")
            return False
    
    @staticmethod
    def send_password_reset_email(user_email: str, otp_code: str, user_name: str = None) -> bool:
        """
        Send password reset OTP email to user
        
        Args:
            user_email: Recipient email address
            otp_code: The OTP code to send
            user_name: User's display name (optional)
            
        Returns:
            bool: True if email was sent/logged successfully
        """
        try:
            if not user_name:
                user_name = user_email.split('@')[0]
            
            subject = 'APF Portal - Password Reset Code'
            
            # Create email content
            message = f"""
Hello {user_name},

You requested to reset your password for APF Portal.

Your password reset code is:

{otp_code}

This code will expire in 15 minutes.

If you didn't request a password reset, please ignore this email and your password will remain unchanged.

Best regards,
APF Portal Team
"""
            
            # In development mode, log to console with clear formatting
            if EmailService.is_development():
                logger.info("\n" + "="*60)
                logger.info("📧 [DEVELOPMENT MODE] Password Reset Email (Console Only)")
                logger.info("="*60)
                logger.info(f"To: {user_email}")
                logger.info(f"User: {user_name}")
                logger.info(f"Subject: {subject}")
                logger.info("-"*60)
                logger.info(f"RESET CODE: {otp_code}")
                logger.info("-"*60)
                logger.info("✅ Email logged to console (not sent)")
                logger.info("="*60 + "\n")
                
                # Also print to console for visibility
                print("\n" + "="*60)
                print("📧 [DEVELOPMENT MODE] Password Reset Email")
                print("="*60)
                print(f"To: {user_email}")
                print(f"RESET CODE: {otp_code}")
                print("="*60 + "\n")
                
                return True
            
            # In production mode, send actual email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                fail_silently=False,
            )
            
            logger.info(f"✅ Password reset email sent successfully to {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending password reset email to {user_email}: {str(e)}")
            return False
