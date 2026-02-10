from django.urls import path
from .views import (
    LoginView, 
    VerifyOTPView, 
    ProfileView, 
    ProfilePictureUploadView, 
    ChangePasswordView,
    ForgotPasswordView,
    ResetPasswordView,
    ResendLoginOTPView,
    ResendPasswordResetOTPView
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-login-otp/', ResendLoginOTPView.as_view(), name='resend-login-otp'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('resend-password-reset-otp/', ResendPasswordResetOTPView.as_view(), name='resend-password-reset-otp'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/picture/', ProfilePictureUploadView.as_view(), name='profile-picture'),
    path('profile/change-password/', ChangePasswordView.as_view(), name='change-password'),
]
