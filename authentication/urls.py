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
<<<<<<< HEAD
    path('profile/change-password/', ChangePasswordView.as_view(), name='change-password'),

    # Profile endpoints (consolidated from profiles app)
    path('profile/', UserProfileViewSet.as_view({
        'get': 'me',
        'put': 'me',
        'patch': 'me'
    }), name='auth-profile-me'),
    path('profile/upload-picture/', UserProfileViewSet.as_view({
        'post': 'upload_picture'
    }), name='auth-profile-upload-picture'),
    path('profile/remove-picture/', UserProfileViewSet.as_view({
        'delete': 'remove_picture'
    }), name='auth-profile-remove-picture'),
    path('profile/privacy-settings/', UserProfileViewSet.as_view({
        'put': 'privacy_settings',
        'patch': 'privacy_settings'
    }), name='auth-profile-privacy-settings'),
    path('profile/notification-preferences/', UserProfileViewSet.as_view({
        'put': 'notification_preferences',
        'patch': 'notification_preferences'
    }), name='auth-profile-notification-preferences'),
    path('profile/activity-log/', UserProfileViewSet.as_view({
        'get': 'activity_log'
    }), name='auth-profile-activity-log'),
    path('profile/completion-status/', UserProfileViewSet.as_view({
        'get': 'completion_status'
    }), name='auth-profile-completion-status'),
||||||| 65d17f5
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/picture/', ProfilePictureUploadView.as_view(), name='profile-picture'),
    path('profile/change-password/', ChangePasswordView.as_view(), name='change-password'),
=======
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
>>>>>>> feature1
]
