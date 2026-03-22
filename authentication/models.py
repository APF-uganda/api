from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from PIL import Image
import os
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
    
    # Profile Information (moved from profiles.UserProfile)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    middle_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=20,
        choices=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
            ('prefer_not_to_say', 'Prefer not to say')
        ],
        blank=True
    )
    
    # Contact Information
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ]
    )
    national_id_number = models.CharField(max_length=20, blank=True)
    alternative_phone = models.CharField(max_length=20, blank=True)
    
    # Address Information
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state_province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='Uganda')
    
    # Professional Information
    job_title = models.CharField(max_length=200, blank=True)
    organization = models.CharField(max_length=200, blank=True)
    department = models.CharField(max_length=100, blank=True)
    icpau_registration_number = models.CharField(max_length=50, blank=True)
    practising_status = models.CharField(max_length=50, default='Active')
    membership_category = models.CharField(max_length=50, default='Full Member')
    years_of_experience = models.PositiveIntegerField(null=True, blank=True)
    specializations = models.TextField(
        blank=True,
        help_text="Areas of specialization, comma-separated"
    )
    
    # Profile Picture
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        null=True,
        blank=True,
        help_text='User profile picture'
    )

    # Subscription management
    subscription_due_date = models.DateField(null=True, blank=True, help_text='Annual subscription renewal date')
    
    # Email notification preferences
    email_notifications_enabled = models.BooleanField(default=True, help_text='Receive email notifications for forum activities')
    email_new_posts = models.BooleanField(default=True, help_text='Receive emails when new posts are created')
    email_new_comments = models.BooleanField(default=True, help_text='Receive emails when someone comments on posts you participate in')
    email_post_replies = models.BooleanField(default=True, help_text='Receive emails when someone replies to your posts')
    email_digest_frequency = models.CharField(
        max_length=10,
        choices=[('none', 'None'), ('daily', 'Daily'), ('weekly', 'Weekly')],
        default='weekly',
        help_text='Frequency of forum activity digest emails'
    )
    
    # Account lockout fields
    failed_login_attempts = models.PositiveIntegerField(default=0, help_text='Number of consecutive failed login attempts')
    account_locked_until = models.DateTimeField(null=True, blank=True, help_text='Account locked until this time')
    last_failed_login = models.DateTimeField(null=True, blank=True, help_text='Timestamp of last failed login attempt')
    
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
        names = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(filter(None, names)) or self.email.split('@')[0].title()
    
    @property
    def initials(self):
        """Get user's initials for avatar"""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        email_name = self.email.split('@')[0]
        if len(email_name) >= 2:
            return f"{email_name[0]}{email_name[1]}".upper()
        return email_name[0].upper() if email_name else "U"
    
    def is_account_locked(self):
        """Check if account is currently locked"""
        if self.account_locked_until and timezone.now() < self.account_locked_until:
            return True
        return False
    
    def get_lockout_time_remaining(self):
        """Get remaining lockout time in minutes"""
        if self.is_account_locked():
            remaining = (self.account_locked_until - timezone.now()).total_seconds() / 60
            return max(0, int(remaining))
        return 0
    
    def record_failed_login(self):
        """Record a failed login attempt and lock account if threshold reached"""
        self.failed_login_attempts += 1
        self.last_failed_login = timezone.now()
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            # Lock for 30 minutes
            self.account_locked_until = timezone.now() + timezone.timedelta(minutes=30)
        
        self.save(update_fields=['failed_login_attempts', 'last_failed_login', 'account_locked_until'])
    
    def reset_failed_login_attempts(self):
        """Reset failed login attempts after successful login"""
        self.failed_login_attempts = 0
        self.last_failed_login = None
        self.account_locked_until = None
        self.save(update_fields=['failed_login_attempts', 'last_failed_login', 'account_locked_until'])
    
    def save(self, *args, **kwargs):
        """Override save to handle profile picture processing and completion tracking."""
        profile_picture = getattr(self, "profile_picture", None)

        # Check if profile_picture field references a non-existent file
        if profile_picture and not hasattr(profile_picture, 'file'):
            try:
                if hasattr(profile_picture, 'path'):
                    file_path = profile_picture.path
                    if not os.path.exists(file_path):
                        print(f"Warning: Profile picture file not found: {file_path}. Clearing field.")
                        if hasattr(self, "profile_picture"):
                            self.profile_picture = None
            except (ValueError, AttributeError, FileNotFoundError) as e:
                print(f"Warning: Issue with profile picture: {e}. Clearing field.")
                if hasattr(self, "profile_picture"):
                    self.profile_picture = None
        
        # Process profile picture only if it's a new file upload
        profile_picture = getattr(self, "profile_picture", None)
        if profile_picture and hasattr(profile_picture, 'file'):
            try:
                self._process_profile_picture()
            except Exception as e:
                print(f"Warning: Failed to process profile picture: {e}")
        
        # Check if profile is complete
        try:
            self._update_profile_completion()
        except Exception as e:
            print(f"Warning: Failed to update profile completion: {e}")
        
        super().save(*args, **kwargs)
    
    def _process_profile_picture(self):
        """Process and optimize profile picture."""
        profile_picture = getattr(self, "profile_picture", None)
        if not profile_picture:
            return
        
        try:
            if not hasattr(profile_picture, 'file'):
                return
            
            if not hasattr(profile_picture, 'path'):
                return
                
            try:
                file_path = profile_picture.path
                if not os.path.exists(file_path):
                    return
            except (ValueError, AttributeError):
                return
            
            img = Image.open(profile_picture.path)
            
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            max_size = (400, 400)
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            img.save(profile_picture.path, 'JPEG', quality=85, optimize=True)
            
        except Exception as e:
            print(f"Error processing profile picture: {e}")
    
    def _update_profile_completion(self):
        """Update profile completion status based on filled fields."""
        required_fields = [
            self.first_name,
            self.last_name,
            self.phone_number,
            self.city,
            self.country
        ]
        
        professional_fields = [
            self.job_title,
            self.organization
        ]
        
        filled_required = sum(1 for field in required_fields if field)
        filled_professional = sum(1 for field in professional_fields if field)
        
        self.is_profile_complete = (
            filled_required >= 4 and
            filled_professional >= 1
        )


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
