"""Django signals for Payment model
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from payments.models import Payment
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Payment)
def update_subscription_on_payment_completion(sender, instance, created, **kwargs):
    """
    Signal handler to update subscription due date when payment is completed
    
    When a payment is marked as completed, this updates the user's subscription_due_date
    to 1 year from the payment completion date.
    
    Args:
        sender: The model class (Payment)
        instance: The actual Payment instance being saved
        created: Boolean indicating if this is a new instance
        **kwargs: Additional keyword arguments
    """
    # Only proceed if payment status is completed
    if instance.status == Payment.STATUS_COMPLETED and instance.user:
        try:
            user = instance.user
            
            # Set subscription due date to 1 year from now
            new_due_date = (timezone.now() + timedelta(days=365)).date()
            user.subscription_due_date = new_due_date
            user.save(update_fields=['subscription_due_date'])
            
            logger.info(
                f"Updated subscription due date for user {user.email} to {new_due_date} "
                f"after payment {instance.transaction_reference} completed"
            )
            
            # If user was suspended, reactivate them
            if not user.is_active:
                user.is_active = True
                user.save(update_fields=['is_active'])
                logger.info(f"Reactivated user {user.email} after successful payment")
                
                # Update suspension record if exists
                try:
                    from admin_management.models import SuspendedMember
                    suspended_record = user.suspension_record
                    suspended_record.reactivated_at = timezone.now()
                    suspended_record.save(update_fields=['reactivated_at'])
                    logger.info(f"Updated suspension record for user {user.email}")
                except Exception as e:
                    logger.debug(f"No suspension record to update for user {user.email}: {e}")
                    
        except Exception as e:
            logger.error(f"Error updating subscription for payment {instance.transaction_reference}: {e}")
