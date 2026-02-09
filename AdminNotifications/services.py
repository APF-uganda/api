"""
Services for handling announcement notifications
"""
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Announcement

User = get_user_model()


def send_welcome_announcement(user):
    """
    Send a welcome announcement to a newly approved member
    
    Args:
        user: The user object who was just approved
    """
    try:
        # Get or create admin user for the announcement
        admin_user = User.objects.filter(role='1').first()
        
        if not admin_user:
            print("Warning: No admin user found to create welcome announcement")
            return None
        
        # Create welcome announcement
        welcome_announcement = Announcement.objects.create(
            title=f"Welcome to APF, {user.first_name or user.email}!",
            content=f"""
Dear {user.first_name or user.email},

Congratulations! Your membership application has been approved.

We are thrilled to welcome you to the Accountancy Practitioners Forum (APF). 
As a member, you now have access to:

- Professional networking opportunities
- Continuing Professional Development (CPD) events
- Industry resources and publications
- Member-exclusive forums and discussions
- Career development support

Your membership journey starts now. We encourage you to:
1. Complete your profile
2. Explore upcoming events
3. Connect with fellow members
4. Stay updated with the latest accounting news

If you have any questions or need assistance, please don't hesitate to reach out to our support team.

Welcome aboard!

Best regards,
The APF Team
            """.strip(),
            audience='members',
            channel='both',
            status='sent',
            priority='high',
            created_by=admin_user
        )
        
        # Mark as sent
        from django.utils import timezone
        welcome_announcement.sent_at = timezone.now()
        welcome_announcement.save()
        
        print(f"Welcome announcement created for {user.email}")
        return welcome_announcement
        
    except Exception as e:
        print(f"Error creating welcome announcement: {e}")
        return None


def get_announcement_recipients(announcement):
    """
    Get the list of users who should receive this announcement
    
    Args:
        announcement: Announcement object
        
    Returns:
        QuerySet of User objects
    """
    audience = announcement.audience
    
    if audience == 'all_users':
        return User.objects.all()
    elif audience == 'members':
        # Active members (role = 2 and approved)
        return User.objects.filter(role='2')
    elif audience == 'applicants':
        # Users with pending applications
        from applications.models import Application
        pending_apps = Application.objects.filter(status='pending').values_list('user_id', flat=True)
        return User.objects.filter(id__in=pending_apps)
    elif audience == 'admins':
        return User.objects.filter(role='1')
    elif audience == 'expired_members':
        # Members whose subscription has expired
        # This would need to be implemented based on your subscription model
        # For now, return members with role='2'
        # TODO: Add subscription_end_date filtering when implemented
        return User.objects.filter(role='2')
    else:
        return User.objects.none()


def send_announcement_email(announcement):
    """
    Send announcement via email to recipients
    
    Args:
        announcement: Announcement object
    """
    if announcement.channel not in ['email', 'both']:
        return
    
    recipients = get_announcement_recipients(announcement)
    recipient_emails = list(recipients.values_list('email', flat=True))
    
    if not recipient_emails:
        print(f"No recipients found for announcement: {announcement.title}")
        return
    
    try:
        # TODO: Integrate with actual email service (SendGrid, AWS SES, etc.)
        # For now, just log
        print(f"Would send email to {len(recipient_emails)} recipients")
        print(f"Subject: {announcement.title}")
        print(f"Recipients: {recipient_emails[:5]}...")  # Show first 5
        
        # Uncomment when email is configured:
        # send_mail(
        #     subject=announcement.title,
        #     message=announcement.content,
        #     from_email=settings.DEFAULT_FROM_EMAIL,
        #     recipient_list=recipient_emails,
        #     fail_silently=False,
        # )
        
    except Exception as e:
        print(f"Error sending announcement email: {e}")


def create_in_app_notifications(announcement):
    """
    Create in-app notifications for recipients
    
    Args:
        announcement: Announcement object
    """
    if announcement.channel not in ['in_app', 'both']:
        return
    
    recipients = get_announcement_recipients(announcement)
    
    if recipients.count() == 0:
        print(f"No recipients found for in-app notifications: {announcement.title}")
        return
    
    # Import here to avoid circular imports
    from notifications.models import UserNotification
    
    # Create in-app notification for each recipient
    notifications_created = 0
    for user in recipients:
        try:
            UserNotification.objects.create(
                user=user,
                title=announcement.title,
                message=announcement.content,
                notification_type='announcement',
                priority=announcement.priority,
                is_read=False
            )
            notifications_created += 1
        except Exception as e:
            print(f"Error creating notification for user {user.email}: {e}")
    
    print(f"Created {notifications_created} in-app notifications for announcement: {announcement.title}")
