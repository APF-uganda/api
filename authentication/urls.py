from django.urls import path
from .views import login_view

urlpatterns = [
    path('login/', login_view, name='login'),
    # Temporarily remove other URLs to isolate the issue
]
