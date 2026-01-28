"""
Django signals for Application model
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from applications.models import Application
from authentication.services import UserCreationService
import logging

logger = logging.getLogger(__name__)


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
        else:
            logger.error(f"Failed to create user for approved application {instance.id}: {error}")
