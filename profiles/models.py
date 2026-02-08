from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from PIL import Image
import os


class UserProfile(models.Model):
    """
    Extended user profile information for both admin and member users.
    Follows Single Responsibility Principle - handles only profile data.
    """
    
    # Core relationship
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    # Personal Information
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
    icpau_registration_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="ICPAU Registration Number"
    )
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
        help_text="Profile picture (max 5MB, recommended: 400x400px)"
    )
    
    # Bio and Additional Info
    bio = models.TextField(
        max_length=1000,
        blank=True,
        help_text="Brief professional biography"
    )
    website = models.URLField(blank=True)
    linkedin_profile = models.URLField(blank=True)
    
    # Preferences
    preferred_language = models.CharField(
        max_length=10,
        choices=[
            ('en', 'English'),
            ('sw', 'Swahili'),
            ('lg', 'Luganda')
        ],
        default='en'
    )
    timezone = models.CharField(
        max_length=50,
        default='Africa/Kampala'
    )
    
    # Privacy Settings
    profile_visibility = models.CharField(
        max_length=20,
        choices=[
            ('public', 'Public'),
            ('members_only', 'Members Only'),
            ('private', 'Private')
        ],
        default='members_only'
    )
    show_email = models.BooleanField(default=False)
    show_phone = models.BooleanField(default=False)
    
    # Notification Preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    newsletter_subscription = models.BooleanField(default=True)
    event_notifications = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_profile_complete = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.get_full_name()} - {self.user.email}"
    
    def get_full_name(self):
        """Return the full name of the user."""
        names = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(filter(None, names)) or self.user.email.split('@')[0]
    
    def get_initials(self):
        """Return user initials for avatar display."""
        full_name = self.get_full_name()
        if full_name and full_name != self.user.email.split('@')[0]:
            names = full_name.split()
            if len(names) >= 2:
                return f"{names[0][0]}{names[-1][0]}".upper()
            return names[0][:2].upper()
        # Fallback to email
        email_name = self.user.email.split('@')[0]
        return email_name[:2].upper()
    
    def get_profile_picture_url(self):
        """Return profile picture URL or None."""
        if self.profile_picture:
            try:
                if hasattr(self.profile_picture, 'url'):
                    # Return full URL for API responses
                    from django.conf import settings
                    if settings.DEBUG:
                        # In development, construct full URL
                        return f"http://localhost:8000{self.profile_picture.url}"
                    else:
                        # In production, use the configured domain
                        return self.profile_picture.url
                else:
                    print(f"Warning: profile_picture has no url attribute: {self.profile_picture}")
            except Exception as e:
                print(f"Error getting profile picture URL: {e}")
        return None
    
    def save(self, *args, **kwargs):
        """Override save to handle image processing and profile completion."""
        # Check if profile_picture field references a non-existent file
        # BUT only if it's not a new upload (new uploads won't have a path yet)
        if self.profile_picture and not hasattr(self.profile_picture, 'file'):
            # This is an existing file reference, check if it exists
            try:
                # Try to access the file
                if hasattr(self.profile_picture, 'path'):
                    file_path = self.profile_picture.path
                    if not os.path.exists(file_path):
                        # File doesn't exist, clear the field
                        print(f"Warning: Profile picture file not found: {file_path}. Clearing field.")
                        self.profile_picture = None
            except (ValueError, AttributeError, FileNotFoundError) as e:
                # File path can't be determined or doesn't exist
                print(f"Warning: Issue with profile picture: {e}. Clearing field.")
                self.profile_picture = None
        
        # Process profile picture only if it's a new file upload
        if self.profile_picture and hasattr(self.profile_picture, 'file'):
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
        if not self.profile_picture:
            return
        
        try:
            # Check if this is a new file being uploaded (has a file attribute)
            # If it's just a reference to an existing file, skip processing
            if not hasattr(self.profile_picture, 'file'):
                return
            
            # Check if file exists and has a path
            if not hasattr(self.profile_picture, 'path'):
                return
                
            # For new uploads, the path might not exist yet
            # Only process if we can actually access the file
            try:
                file_path = self.profile_picture.path
                if not os.path.exists(file_path):
                    return
            except (ValueError, AttributeError):
                # Path doesn't exist yet or can't be determined
                return
            
            # Open and process image
            img = Image.open(self.profile_picture.path)
            
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Resize if too large
            max_size = (400, 400)
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save optimized image
            img.save(self.profile_picture.path, 'JPEG', quality=85, optimize=True)
            
        except Exception as e:
            # Log error but don't fail the save
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
        
        # Profile is complete if most required fields are filled
        filled_required = sum(1 for field in required_fields if field)
        filled_professional = sum(1 for field in professional_fields if field)
        
        self.is_profile_complete = (
            filled_required >= 4 and  # At least 4 of 5 required fields
            filled_professional >= 1   # At least 1 professional field
        )


class ProfileActivityLog(models.Model):
    """
    Log profile changes for audit purposes.
    Follows Single Responsibility Principle - handles only activity logging.
    """
    
    profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='activity_logs'
    )
    action = models.CharField(
        max_length=50,
        choices=[
            ('created', 'Profile Created'),
            ('updated', 'Profile Updated'),
            ('picture_uploaded', 'Picture Uploaded'),
            ('picture_removed', 'Picture Removed'),
            ('privacy_changed', 'Privacy Settings Changed'),
            ('notifications_changed', 'Notification Preferences Changed')
        ]
    )
    field_changed = models.CharField(max_length=100, blank=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    metadata = models.JSONField(blank=True, default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Profile Activity Log'
        verbose_name_plural = 'Profile Activity Logs'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.profile.user.email} - {self.action} - {self.timestamp}"
