from django.contrib import admin
from .models import UserProfile, ProfileActivityLog


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for UserProfile model.
    """
    
    list_display = [
        'get_full_name',
        'user_email',
        'user_role',
        'job_title',
        'organization',
        'city',
        'is_profile_complete',
        'updated_at'
    ]
    
    list_filter = [
        'user__role',
        'is_profile_complete',
        'country',
        'profile_visibility',
        'created_at',
        'updated_at'
    ]
    
    search_fields = [
        'first_name',
        'last_name',
        'user__email',
        'organization',
        'job_title',
        'icpau_registration_number'
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'is_profile_complete',
        'get_full_name',
        'get_initials'
    ]
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'get_full_name', 'get_initials')
        }),
        ('Personal Information', {
            'fields': (
                'first_name',
                'last_name',
                'middle_name',
                'date_of_birth',
                'gender'
            )
        }),
        ('Contact Information', {
            'fields': (
                'phone_number',
                'alternative_phone'
            )
        }),
        ('Address Information', {
            'fields': (
                'address_line_1',
                'address_line_2',
                'city',
                'state_province',
                'postal_code',
                'country'
            )
        }),
        ('Professional Information', {
            'fields': (
                'job_title',
                'organization',
                'department',
                'icpau_registration_number',
                'years_of_experience',
                'specializations'
            )
        }),
        ('Profile & Bio', {
            'fields': (
                'profile_picture',
                'bio',
                'website',
                'linkedin_profile'
            )
        }),
        ('Preferences', {
            'fields': (
                'preferred_language',
                'timezone'
            )
        }),
        ('Privacy Settings', {
            'fields': (
                'profile_visibility',
                'show_email',
                'show_phone'
            )
        }),
        ('Notification Preferences', {
            'fields': (
                'email_notifications',
                'sms_notifications',
                'newsletter_subscription',
                'event_notifications'
            )
        }),
        ('Metadata', {
            'fields': (
                'is_profile_complete',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'
    
    def user_role(self, obj):
        return 'Admin' if obj.user.role == '1' else 'Member'
    user_role.short_description = 'Role'
    user_role.admin_order_field = 'user__role'


@admin.register(ProfileActivityLog)
class ProfileActivityLogAdmin(admin.ModelAdmin):
    """
    Admin interface for ProfileActivityLog model.
    """
    
    list_display = [
        'profile_user_email',
        'action',
        'field_changed',
        'timestamp',
        'ip_address'
    ]
    
    list_filter = [
        'action',
        'timestamp'
    ]
    
    search_fields = [
        'profile__user__email',
        'profile__first_name',
        'profile__last_name',
        'field_changed'
    ]
    
    readonly_fields = [
        'profile',
        'action',
        'field_changed',
        'old_value',
        'new_value',
        'ip_address',
        'user_agent',
        'timestamp'
    ]
    
    def profile_user_email(self, obj):
        return obj.profile.user.email
    profile_user_email.short_description = 'User Email'
    profile_user_email.admin_order_field = 'profile__user__email'
    
    def has_add_permission(self, request):
        return False  # Don't allow manual creation of activity logs
    
    def has_change_permission(self, request, obj=None):
        return False  # Don't allow editing of activity logs
