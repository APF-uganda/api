from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
import secrets


class UserRole(models.TextChoices):
    ADMIN = '1', 'Admin'
    MEMBER = '2', 'Member'


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user"""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', UserRole.MEMBER)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, db_index=True)
    role = models.CharField(
        max_length=10,
        choices=UserRole.choices,
        default=UserRole.MEMBER
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Profile fields
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    national_id_number = models.CharField(max_length=20, blank=True)
    
    # Professional fields
    icpau_registration_number = models.CharField(max_length=50, blank=True)
    organization = models.CharField(max_length=200, blank=True)
    practising_status = models.CharField(max_length=50, default='Active')
    membership_category = models.CharField(max_length=50, default='Full Member')
    
    # Profile picture
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    
    # Subscription management
    subscription_due_date = models.DateField(null=True, blank=True, help_text='Annual subscription renewal date')
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        db_table = 'auth_users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return self.email
    
    @property
    def full_name(self):
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email.split('@')[0].title()
    
    @property
    def initials(self):
        """Get user's initials for avatar"""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        email_name = self.email.split('@')[0]
        if len(email_name) >= 2:
            return f"{email_name[0]}{email_name[1]}".upper()
        return email_name[0].upper() if email_name else "U"


class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    code = models.CharField(max_length=6)
    session_id = models.UUIDField(unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'auth_otps'
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['user', 'is_used']),
        ]
    
    def is_valid(self):
        """Check if OTP is valid (not used and not expired)"""
        return not self.is_used and timezone.now() < self.expires_at
    
    @staticmethod
    def generate_code():
        """Generate a 6-digit OTP code"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])

    def __str__(self):
        return f"OTP for {self.user.email} - {self.code}"


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'auth_password_reset_tokens'
        indexes = [
            models.Index(fields=['token']),
        ]
    
    def is_valid(self):
        """Check if token is valid (not used and not expired)"""
        return not self.is_used and timezone.now() < self.expires_at
    
    @staticmethod
    def generate_token():
        """Generate a secure random token"""
        return secrets.token_urlsafe(48)

    def __str__(self):
        return f"Password reset token for {self.user.email}"


class AuthEventType(models.TextChoices):
    LOGIN_ATTEMPT = 'login_attempt', 'Login Attempt'
    LOGIN_SUCCESS = 'login_success', 'Login Success'
    LOGIN_FAILURE = 'login_failure', 'Login Failure'
    OTP_GENERATED = 'otp_generated', 'OTP Generated'
    OTP_VERIFIED = 'otp_verified', 'OTP Verified'
    OTP_FAILED = 'otp_failed', 'OTP Failed'
    PASSWORD_RESET_REQUESTED = 'password_reset_requested', 'Password Reset Requested'
    PASSWORD_RESET_COMPLETED = 'password_reset_completed', 'Password Reset Completed'
    RATE_LIMIT_TRIGGERED = 'rate_limit_triggered', 'Rate Limit Triggered'
    TOKEN_REFRESHED = 'token_refreshed', 'Token Refreshed'
    LOGOUT = 'logout', 'Logout'


class AuthLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='auth_logs')
    email = models.EmailField()
    event_type = models.CharField(max_length=30, choices=AuthEventType.choices)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    success = models.BooleanField()
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'auth_logs'
        indexes = [
            models.Index(fields=['email', 'timestamp']),
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.event_type} - {self.email} at {self.timestamp}"
