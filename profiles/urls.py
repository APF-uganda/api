"""
URL configuration for profiles app.
"""

from django.urls import path
from .views import UserProfileViewSet
from .email_preferences_views import email_preferences

# Define explicit URL patterns for all profile endpoints
urlpatterns = [
    # Profile CRUD operations
    path('me/', UserProfileViewSet.as_view({
        'get': 'me',
        'put': 'me', 
        'patch': 'me'
    }), name='profile-me'),
    
    # Profile picture operations
    path('upload-picture/', UserProfileViewSet.as_view({
        'post': 'upload_picture'
    }), name='profile-upload-picture'),
    
    path('remove-picture/', UserProfileViewSet.as_view({
        'delete': 'remove_picture'
    }), name='profile-remove-picture'),
    
    # Settings operations
    path('privacy-settings/', UserProfileViewSet.as_view({
        'put': 'privacy_settings',
        'patch': 'privacy_settings'
    }), name='profile-privacy-settings'),
    
    path('notification-preferences/', UserProfileViewSet.as_view({
        'put': 'notification_preferences',
        'patch': 'notification_preferences'
    }), name='profile-notification-preferences'),
    
    # Email preferences
    path('email-preferences/', email_preferences, name='profile-email-preferences'),
    
    # Information endpoints
    path('activity-log/', UserProfileViewSet.as_view({
        'get': 'activity_log'
    }), name='profile-activity-log'),
    
    path('completion-status/', UserProfileViewSet.as_view({
        'get': 'completion_status'
    }), name='profile-completion-status'),
]