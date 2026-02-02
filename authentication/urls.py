from django.urls import path
from .views import LoginView, VerifyOTPView, ProfileView, ProfilePictureUploadView, ChangePasswordView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/picture/', ProfilePictureUploadView.as_view(), name='profile-picture'),
    path('profile/change-password/', ChangePasswordView.as_view(), name='change-password'),
]
