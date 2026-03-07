"""Django signals for Application model
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta, date
from applications.models import Application
from authentication.services import UserCreationService
from authentication.email_service_smtp import EmailService
from notifications.announcement_services import send_welcome_announcement
import logging

logger = logging.getLogger(__name__)


def get_next_april_first():
    """
    Calculate the next April 1st renewal date.
    
    Returns:
        date: The next April 1st (current year if before April 1st, next year if after)
    """
    today = timezone.now().date()
    current_year = today.year
    
    # April 1st of current year
    april_first_this_year = date(current_year, 4, 1)
    
    # If today is before April 1st this year, return April 1st this year
    # Otherwise, return April 1st next year
    if today < april_first_this_year:
        return april_first_this_year
    else:
        return date(current_year + 1, 4, 1)


@receiver(post_save, sender=Application)
def create_user_on_approval(sender, instance, created, **kwargs):
    """
    Signal handler to create User account when Application is approved
    
    Listens for Application status changes to 'approved' and automatically
    creates a corresponding User account.
    
    Args:
        sender: The model class (Application)
        instance: The actual Application instance being saved
        created: Boolean indicating if this is a new instance
        **kwargs: Additional keyword arguments
    """
    # Only proceed if the application is approved and doesn't have a linked user
    if instance.status == 'approved' and instance.user is None:
        logger.info(f"Application {instance.id} approved, creating user account for {instance.email}")
        
        # Create user from application
        user, error = UserCreationService.create_user_from_application(instance)
        
        if user:
            logger.info(f"Successfully created user {user.id} for approved application {instance.id}")
            
            # Set subscription due date to next April 1st for newly approved members
            user.subscription_due_date = get_next_april_first()
            user.save(update_fields=['subscription_due_date'])
            logger.info(f"Set subscription due date for user {user.email} to {user.subscription_due_date}")
            
            # Send approval email to the newly approved member
            try:
                user_name = f"{user.first_name} {user.last_name}".strip() if user.first_name or user.last_name else user.email.split('@')[0]
                email_sent = EmailService.send_approval_email(
                    email=user.email,
                    user_name=user_name
                )
                if email_sent:
                    logger.info(f"Approval email sent successfully to {user.email}")
                else:
                    logger.warning(f"Failed to send approval email to {user.email}")
            except Exception as e:
                logger.error(f"Error sending approval email to {user.email}: {e}")
            
            # Send welcome notification to the newly approved member
            try:
                send_welcome_announcement(user)
                logger.info(f"Welcome announcement sent to user {user.email}")
            except Exception as e:
                logger.error(f"Failed to send welcome announcement to user {user.email}: {e}")
        else:
            logger.error(f"Failed to create user for approved application {instance.id}: {error}")


@receiver(pre_save, sender=Application)
def send_welcome_notification_on_status_change(sender, instance, **kwargs):
    """
    Signal handler to send welcome notification when an application status changes to approved
    This catches cases where an existing application gets approved (not just new ones)
    
    Args:
        sender: The model class (Application)
        instance: The actual Application instance being saved
        **kwargs: Additional keyword arguments
    """
    if not instance.pk:
        # New instance, handled by the post_save signal
        return
    
    try:
        old_instance = Application.objects.get(pk=instance.pk)
        # Check if status changed to approved
        if old_instance.status != 'approved' and instance.status == 'approved':
            logger.info(f"Application {instance.id} status changed to approved, sending welcome notification")
            
            # If user already exists, send approval email, welcome notification and set subscription date
            if instance.user:
                # Set subscription due date to next April 1st
                instance.user.subscription_due_date = get_next_april_first()
                instance.user.save(update_fields=['subscription_due_date'])
                logger.info(f"Set subscription due date for user {instance.user.email} to {instance.user.subscription_due_date}")
                
                # Send approval email
                try:
                    user_name = f"{instance.user.first_name} {instance.user.last_name}".strip() if instance.user.first_name or instance.user.last_name else instance.user.email.split('@')[0]
                    email_sent = EmailService.send_approval_email(
                        email=instance.user.email,
                        user_name=user_name
                    )
                    if email_sent:
                        logger.info(f"Approval email sent successfully to {instance.user.email}")
                    else:
                        logger.warning(f"Failed to send approval email to {instance.user.email}")
                except Exception as e:
                    logger.error(f"Error sending approval email to {instance.user.email}: {e}")
                
                # Send welcome announcement
                try:
                    send_welcome_announcement(instance.user)
                    logger.info(f"Welcome announcement sent to user {instance.user.email}")
                except Exception as e:
                    logger.error(f"Failed to send welcome announcement to user {instance.user.email}: {e}")
    except Application.DoesNotExist:
        # This is a new application, will be handled by post_save
        pass