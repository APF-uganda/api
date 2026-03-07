from .models import Notification

def create_notification(application, user, message, type="info"):
    """
    Create a notification for a given application and user.
    """
    return Notification.objects.create(
        application=application,
        user=user,
        message=message,
        type=type
    )
import threading
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import UserNotification

User = get_user_model()

def create_in_app_notifications(announcement):
    """Handles the 'In-App' channel logic"""
    if announcement.channel not in ['in_app', 'both']:
        return

    #  Get Target Users
    target_users = get_target_users(announcement.audience)
    
    #  Bulk create notifications for performance
    notifications = [
        UserNotification(
            user=user,
            title=announcement.title,
            message=announcement.content,
            notification_type='announcement',
            priority=announcement.priority
        ) for user in target_users
    ]
    UserNotification.objects.bulk_create(notifications)


def send_announcement_email(announcement):
    """Handles the 'Email' channel logic"""
    if announcement.channel not in ['email', 'both']:
        return

    # Get Target Emails
    target_users = get_target_users(announcement.audience)
    email_list = list(target_users.values_list('email', flat=True))

    if email_list:
       
        thread = threading.Thread(
            target=_execute_email_broadcast, 
            args=(announcement, email_list)
        )
        thread.start()


def get_target_users(audience):
    """Helper to filter users based on the selected audience"""
    users = User.objects.filter(is_active=True)
    
    if audience == 'members':
        return users.filter(role='member')  # Ensure 'role' matches your User model
    elif audience == 'applicants':
        return users.filter(role='applicant')
    elif audience == 'admins':
        return users.filter(is_staff=True)
    elif audience == 'expired_members':
        
        return users.filter(membership_status='expired')
    
    return users # 'all_users'


def _execute_email_broadcast(announcement, email_list):
    """The actual SMTP sending logic (Runs in background)"""
    subject = f"Announcement: {announcement.title}"
    context = {
        'title': announcement.title,
        'content': announcement.content,
        'priority': announcement.priority
    }
    
    html_content = render_to_string('emails/announcement_broadcast.html', context)
    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.DEFAULT_FROM_EMAIL], # Visible 'To'
        bcc=email_list # Hidden recipients
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()