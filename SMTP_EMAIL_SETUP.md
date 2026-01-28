# SMTP Email Setup for Production

## Why Switch from EmailJS?

EmailJS blocks server-side API calls (403 error). For production, use SMTP which is designed for server-side email sending.

## Setup Instructions

### 1. Update `.env` file

Add these SMTP settings (example using Gmail):

```env
# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=APF Portal <your-email@gmail.com>
```

**For Gmail:**
- Enable 2-Factor Authentication
- Generate an "App Password" at: https://myaccount.google.com/apppasswords
- Use the app password (not your regular password)

**For Other Providers:**
- **Outlook/Hotmail:** smtp.office365.com, port 587
- **Yahoo:** smtp.mail.yahoo.com, port 587
- **SendGrid:** smtp.sendgrid.net, port 587 (use API key as password)

### 2. Update `services.py`

Replace the `EmailService` class with SMTP-based implementation:

```python
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

class EmailService:
    """Service for sending emails via SMTP"""
    
    @staticmethod
    def send_otp_email(email, otp_code, user_name=None):
        """Send OTP email using Django SMTP"""
        try:
            subject = 'Your APF Portal Login Code'
            message = f'''
Hello {user_name or 'User'},

Your one-time password (OTP) for logging into the APF Portal is:

{otp_code}

This code will expire in 10 minutes.

If you didn't request this code, please ignore this email.

Best regards,
APF Portal Team
            '''
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            
            logger.info(f"OTP email sent successfully to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending OTP email to {email}: {str(e)}")
            return False
    
    @staticmethod
    def send_password_reset_email(email, reset_token, user_name=None):
        """Send password reset email using Django SMTP"""
        try:
            frontend_url = settings.CORS_ALLOWED_ORIGINS[0] if settings.CORS_ALLOWED_ORIGINS else 'http://localhost:5173'
            reset_link = f"{frontend_url}/reset-password?token={reset_token}"
            
            subject = 'Reset Your APF Portal Password'
            message = f'''
Hello {user_name or 'User'},

You requested to reset your password for the APF Portal.

Click the link below to reset your password:
{reset_link}

This link will expire in 1 hour.

If you didn't request this, please ignore this email.

Best regards,
APF Portal Team
            '''
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            
            logger.info(f"Password reset email sent successfully to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending password reset email to {email}: {str(e)}")
            return False
```

### 3. Update `settings.py`

Add email configuration:

```python
# Email Configuration
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@apfportal.com')
```

### 4. Test Email Sending

```bash
python manage.py shell
```

```python
from django.core.mail import send_mail

send_mail(
    'Test Email',
    'This is a test email from APF Portal',
    'your-email@gmail.com',
    ['bashkiko@gmail.com'],
    fail_silently=False,
)
```

## Development Mode

For development, use console backend (prints emails to console):

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Emails will be printed to the terminal instead of sent.
