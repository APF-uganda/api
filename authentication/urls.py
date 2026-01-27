from django.urls import path
from .views import (
    LoginView,
    VerifyOTPView,
    RefreshTokenView,
    LogoutView,
    CurrentUserView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    AuthLogsView
)

urlpatterns = [
    path('login', LoginView.as_view(), name='login'),
    path('verify-otp', VerifyOTPView.as_view(), name='verify-otp'),
    path('refresh', RefreshTokenView.as_view(), name='refresh'),
    path('logout', LogoutView.as_view(), name='logout'),
    path('me', CurrentUserView.as_view(), name='current-user'),
    path('password-reset-request', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset-confirm', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('logs', AuthLogsView.as_view(), name='auth-logs'),
]
