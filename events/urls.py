from django.urls import path
from .views import (
    register_for_event, 
    AdminRegistrationListView, 
    VerifyRegistrationView
)

urlpatterns = [
    # Public endpoint for React registration form
    path('register/', register_for_event, name='event-register'),
    
    # Admin endpoints for the frontend dashboard
    path('admin/registrations/', AdminRegistrationListView.as_view(), name='admin-registrations'),
    path('admin/verify/<int:pk>/', VerifyRegistrationView.as_view(), name='admin-verify'),
]