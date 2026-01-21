from django.urls import path
from . import views

urlpatterns = [
    path('submit/', views.create_contact_message, name='create_contact_message'),
    path('list/', views.list_contact_messages, name='list_contact_messages'),
]
