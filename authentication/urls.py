from django.urls import path
from .views import (
    LoginView, 
    VerifyOTPView, 
    ChangePasswordView,
    ForgotPasswordView,
    ResetPasswordView,
    ResendLoginOTPView,
    ResendPasswordResetOTPView
)
from .profile_views import UserProfileViewSet

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-login-otp/', ResendLoginOTPView.as_view(), name='resend-login-otp'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('resend-password-reset-otp/', ResendPasswordResetOTPView.as_view(), name='resend-password-reset-otp'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('profile/change-password/', ChangePasswordView.as_view(), name='profile-change-password'),

    # Profile endpoints (scoped to authenticated user only)
    path('profile/', UserProfileViewSet.as_view({
        'get': 'me',
        'put': 'me',
        'patch': 'me',
    }), name='profile-me'),
    path('profile/upload-picture/', UserProfileViewSet.as_view({
        'post': 'upload_picture',
    }), name='profile-upload-picture'),
    path('profile/remove-picture/', UserProfileViewSet.as_view({
        'delete': 'remove_picture',
    }), name='profile-remove-picture'),
    path('profile/privacy-settings/', UserProfileViewSet.as_view({
        'put': 'privacy_settings',
        'patch': 'privacy_settings',
    }), name='profile-privacy-settings'),
    path('profile/notification-preferences/', UserProfileViewSet.as_view({
        'put': 'notification_preferences',
        'patch': 'notification_preferences',
    }), name='profile-notification-preferences'),
    path('profile/completion-status/', UserProfileViewSet.as_view({
        'get': 'completion_status',
    }), name='profile-completion-status'),
    path('profile/activity-log/', UserProfileViewSet.as_view({
        'get': 'activity_log',
    }), name='profile-activity-log'),
]
