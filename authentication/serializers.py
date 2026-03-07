"""
Serializers for authentication app
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import User

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile data
    """
    full_name = serializers.SerializerMethodField()
    initials = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'initials', 'first_name', 'last_name',
            'phone_number', 'date_of_birth', 'national_id_number', 
            'icpau_registration_number', 'organization', 'practising_status',
            'membership_category', 'profile_picture', 'role', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'email', 'created_at', 'updated_at', 'role']
    
    def get_full_name(self, obj):
        """Get user's full name"""
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}"
        return obj.email.split('@')[0].title()
    
    def get_initials(self, obj):
        """Get user's initials for avatar"""
        if obj.first_name and obj.last_name:
            return f"{obj.first_name[0]}{obj.last_name[0]}".upper()
        email_name = obj.email.split('@')[0]
        if len(email_name) >= 2:
            return f"{email_name[0]}{email_name[1]}".upper()
        return email_name[0].upper() if email_name else "U"

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile
    """
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone_number', 'date_of_birth',
            'icpau_registration_number', 'organization', 'practising_status',
            'membership_category'
        ]
    
    def validate_icpau_registration_number(self, value):
        """Validate ICPAU registration number format"""
        if value and not value.startswith(('F/ICPAU/', 'A/ICPAU/', 'S/ICPAU/')):
            raise serializers.ValidationError(
                "ICPAU registration number must start with F/ICPAU/, A/ICPAU/, or S/ICPAU/"
            )
        return value

class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change
    """
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True)
    
    def validate_new_password(self, value):
        import re
        if not re.search(r'[A-Za-z]', value):
            raise serializers.ValidationError("Password must contain at least one letter.")
        if not re.search(r'\d', value):
            raise serializers.ValidationError("Password must contain at least one number.")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/~`]', value):
            raise serializers.ValidationError("Password must contain at least one special character.")
        return value
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs
    
    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect")
        return value

class ProfilePictureUploadSerializer(serializers.Serializer):
    """
    Serializer for profile picture upload
    """
    profile_picture = serializers.ImageField(required=True)
    
    def validate_profile_picture(self, value):
        """Validate profile picture"""
        # Check file size (max 5MB)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Profile picture must be less than 5MB")
        
        # Check file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                "Only JPEG, PNG, GIF, and WebP images are allowed"
            )
        
        return value