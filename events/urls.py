from django.urls import path
from .views import (
    register_for_event, 
    AdminRegistrationListView, 
    VerifyRegistrationView
)



urlpatterns = [
    #  Public endpoint for React registration form
    
    path('register/', register_for_event, name='event-register'),
    
    #Admin endpoint to fetch all registrations
   
    path('admin/registrations/', AdminRegistrationListView.as_view(), name='admin-registrations'),
    
    #  Admin endpoint to verify a specific payment
    
    path('admin/verify/<int:pk>/', VerifyRegistrationView.as_view(), name='admin-verify'),
]