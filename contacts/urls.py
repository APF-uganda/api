from django.urls import path
from . import views

urlpatterns = [
    path('', views.contacts_root, name='contacts_root'),
    path('submit/', views.create_contact_message, name='create_contact_message'),
    path('list/', views.list_contact_messages, name='list_contact_messages'),
    path('<int:message_id>/toggle-read/', views.toggle_read_status, name='toggle_read_status'),
    path('<int:message_id>/delete/', views.delete_contact_message, name='delete_contact_message'),
    path('<int:message_id>/reply/', views.reply_to_contact_message, name='reply_to_contact_message'),
]
