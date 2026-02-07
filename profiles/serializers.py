"""
Profile serializers for API endpoints.
Follows Single Responsibility Principle - each serializer handles one specific use case.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserProfile, ProfileActivityLog

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Complete user profile serializer for full CRUD operations.
    """
    
    # Read-only computed fields
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    initials = serializers.CharField(source='get_initials', read_only=True)
    profile_picture_url = serializers.SerializerMethodField(read_only=True)
    
    # User information (read-only)
    email = serializers.EmailField(source='user.email', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    date_joined = serializers.DateTimeField(source='user.created_at', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            # Computed fields
            'full_name',
            'initials',
            'profile_picture_url',
            
            # User info
            'email',
            'user_role',
            'date_joined',
            
            # Personal Information
            'first_name',
            'last_name',
            'middle_name',
            'date_of_birth',
            'gender',
            
            # Contact Information
            'phone_number',
            'alternative_phone',
            
            # Address Information
            'address_line_1',
            'address_line_2',
            'city',
            'state_province',
            'postal_code',
            'country',
            
            # Professional Information
            'job_title',
            'organization',
            'department',
            'icpau_registration_number',
            'years_of_experience',
            'specializations',
            
            # Profile Picture
            'profile_picture',
            
            # Bio and Additional Info
            'bio',
            'website',
            'linkedin_profile',
            
            # Preferences
            'preferred_language',
            'timezone',
            
            # Privacy Settings
            'profile_visibility',
            'show_email',
            'show_phone',
            
            # Notification Preferences
            'email_notifications',
            'sms_notifications',
            'newsletter_subscription',
            'event_notifications',
            
            # Metadata
            'created_at',
            'updated_at',
            'is_profile_complete',
        ]
        read_only_fields = [
            'created_at',
            'updated_at',
            'is_profile_complete',
            'full_name',
            'initials',
            'profile_picture_url',
            'email',
            'user_role',
            'date_joined',
        ]

    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        url = obj.get_profile_picture_url()
        if not url:
            return None
        if request is not None:
            return request.build_absolute_uri(url)
        return url
    
    def validate_profile_picture(self, value):
        """Validate profile picture upload."""
        if value:
            # Check file size (5MB limit)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError(
                    "Profile picture must be smaller than 5MB."
                )
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError(
                    "Profile picture must be a JPEG, PNG, GIF, or WebP image."
                )
        
        return value
    
    def validate_phone_number(self, value):
        """Validate phone number format."""
        if value:
            # Remove spaces and special characters for validation
            cleaned = ''.join(filter(str.isdigit, value.replace('+', '')))
            if len(cleaned) < 9 or len(cleaned) > 15:
                raise serializers.ValidationError(
                    "Phone number must be between 9 and 15 digits."
                )
        return value


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for partial profile updates.
    Allows updating specific sections without requiring all fields.
    """
    
    class Meta:
        model = UserProfile
        fields = [
            # Personal Information
            'first_name',
            'last_name',
            'middle_name',
            'date_of_birth',
            'gender',
            
            # Contact Information
            'phone_number',
            'alternative_phone',
            
            # Address Information
            'address_line_1',
            'address_line_2',
            'city',
            'state_province',
            'postal_code',
            'country',
            
            # Professional Information
            'job_title',
            'organization',
            'department',
            'icpau_registration_number',
            'years_of_experience',
            'specializations',
            
            # Bio and Additional Info
            'bio',
            'website',
            'linkedin_profile',
            
            # Preferences
            'preferred_language',
            'timezone',
        ]


class ProfilePictureSerializer(serializers.ModelSerializer):
    """
    Dedicated serializer for profile picture uploads.
    Follows Single Responsibility Principle.
    """
    
    profile_picture_url = serializers.CharField(source='get_profile_picture_url', read_only=True)
    initials = serializers.CharField(source='get_initials', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'profile_picture_url', 'initials']
    
    def validate_profile_picture(self, value):
        """Validate profile picture upload."""
        if value:
            # Check file size (5MB limit)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError(
                    "Profile picture must be smaller than 5MB."
                )
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError(
                    "Profile picture must be a JPEG, PNG, GIF, or WebP image."
                )
        
        return value


class PrivacySettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for privacy settings updates.
    """
    
    class Meta:
        model = UserProfile
        fields = [
            'profile_visibility',
            'show_email',
            'show_phone',
        ]


class NotificationPreferencesSerializer(serializers.ModelSerializer):
    """
    Serializer for notification preferences updates.
    """
    
    class Meta:
        model = UserProfile
        fields = [
            'email_notifications',
            'sms_notifications',
            'newsletter_subscription',
            'event_notifications',
        ]


class ProfileSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for profile summaries (e.g., in lists).
    """
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    initials = serializers.CharField(source='get_initials', read_only=True)
    profile_picture_url = serializers.SerializerMethodField(read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'full_name',
            'initials',
            'profile_picture_url',
            'email',
            'user_role',
            'job_title',
            'organization',
            'city',
            'country',
            'is_profile_complete',
            'updated_at',
        ]

    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        url = obj.get_profile_picture_url()
        if not url:
            return None
        if request is not None:
            return request.build_absolute_uri(url)
        return url


class ProfileActivityLogSerializer(serializers.ModelSerializer):
    """
    Serializer for profile activity logs.
    """
    
    class Meta:
        model = ProfileActivityLog
        fields = [
            'action',
            'field_changed',
            'metadata',
            'timestamp',
        ]
        read_only_fields = ['action', 'field_changed', 'metadata', 'timestamp']
