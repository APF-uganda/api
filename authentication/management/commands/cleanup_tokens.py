"""
Management command to clean up expired OTPs and PasswordResetTokens.
Usage: python manage.py cleanup_tokens
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from authentication.models import OTP, PasswordResetToken


class Command(BaseCommand):
    help = 'Delete expired OTPs and PasswordResetTokens'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # Delete expired OTPs
        expired_otps = OTP.objects.filter(expires_at__lt=now)
        otp_count = expired_otps.count()
        expired_otps.delete()
        
        # Delete expired PasswordResetTokens
        expired_tokens = PasswordResetToken.objects.filter(expires_at__lt=now)
        token_count = expired_tokens.count()
        expired_tokens.delete()
        
        # Log cleanup statistics
        self.stdout.write(
            self.style.SUCCESS(
                f'Cleanup completed:\n'
                f'  - Deleted {otp_count} expired OTP(s)\n'
                f'  - Deleted {token_count} expired password reset token(s)\n'
                f'  - Total: {otp_count + token_count} expired records removed'
            )
        )
