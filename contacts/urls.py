from django.urls import path
from . import views

urlpatterns = [
    path('', views.contacts_root, name='contacts_root'),
    path('submit/', views.create_contact_message, name='create_contact_message'),
    path('list/', views.list_contact_messages, name='list_contact_messages'),
    path('<int:message_id>/reply/', views.reply_to_contact_message, name='reply_to_contact_message'),
]
