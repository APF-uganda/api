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


def get_annual_renewal_date(base_date=None):
    """
    Calculate annual renewal date - always December 31st.
    If joining after December 31st of the current year, renewal is Dec 31 next year.
    Otherwise, renewal is December 31st of the current year.
    """
    if base_date is None:
        base_date = timezone.now().date()
    elif hasattr(base_date, 'date'):
        base_date = base_date.date()

    renewal_month = 12
    renewal_day = 31
    current_year = base_date.year
    renewal_date_this_year = base_date.replace(month=renewal_month, day=renewal_day, year=current_year)

    if base_date > renewal_date_this_year:
        return base_date.replace(month=renewal_month, day=renewal_day, year=current_year + 1)
    else:
        return renewal_date_this_year


@receiver(post_save, sender=Application)
def create_payment_record(sender, instance, created, **kwargs):
    """
    Signal handler to create a payment record when an Application is created.
    This ensures all applications appear in the payments dashboard.
    """
    if created:
        # Import here to avoid circular imports
        from payments.models import ManualPayment
        
        try:
            # Create a manual payment record for this application
            payment = ManualPayment.objects.create(
                application=instance,
                user=instance.user,  # May be None for new applications
                amount=instance.payment_amount,
                currency='UGX',
                reference=instance.application_id,
                description='Application Fee',
                application_reference=instance.application_id,
                status=ManualPayment.STATUS_PENDING,
                # Use the proof of payment from application if available
                proof_of_payment=instance.proof_of_payment_doc
            )
            
            logger.info(f"Created payment record {payment.id} for application {instance.application_id}")
            
        except Exception as e:
            logger.error(f"Failed to create payment record for application {instance.application_id}: {e}")


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
            
            # Set subscription due date to one year from approval
            user.subscription_due_date = get_annual_renewal_date(
                instance.updated_at or timezone.now()
            )
            user.save(update_fields=['subscription_due_date'])
            logger.info(f"Set subscription due date for user {user.email} to {user.subscription_due_date}")
            
            # Send approval email to the newly approved member
            try:
                # Use the username from the application
                user_name = instance.username if instance.username else f"{user.first_name} {user.last_name}".strip()
                if not user_name:
                    user_name = user.email.split('@')[0]
                
                email_sent = EmailService.send_approval_email(
                    email=user.email,
                    user_name=user_name,
                    apf_membership_number=user.apf_membership_number or None,
                )
                if email_sent:
                    logger.info(f"Approval email sent successfully to {user.email} with username: {user_name}")
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
def update_payment_status_on_approval(sender, instance, **kwargs):
    """
    Signal handler to update payment status when application status changes.
    """
    if not instance.pk:
        # New instance, skip
        return
    
    try:
        old_instance = Application.objects.get(pk=instance.pk)
        
        # Check if status changed
        if old_instance.status != instance.status:
            # Import here to avoid circular imports
            from payments.models import ManualPayment
            
            # Update related payment records
            payments = ManualPayment.objects.filter(application=instance)
            
            if instance.status == 'approved':
                # Mark payments as verified when application is approved
                for payment in payments:
                    if payment.status == ManualPayment.STATUS_PENDING:
                        payment.status = ManualPayment.STATUS_VERIFIED
                        payment.verified_at = timezone.now()
                        payment.save()
                        logger.info(f"Verified payment {payment.id} for approved application {instance.application_id}")
                        
            elif instance.status == 'rejected':
                # Mark payments as rejected when application is rejected
                for payment in payments:
                    if payment.status == ManualPayment.STATUS_PENDING:
                        payment.status = ManualPayment.STATUS_REJECTED
                        payment.verified_at = timezone.now()
                        payment.verification_notes = 'Application rejected'
                        payment.save()
                        logger.info(f"Rejected payment {payment.id} for rejected application {instance.application_id}")
                        
    except Application.DoesNotExist:
        # This is a new application, skip
        pass


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
                # Set subscription due date to one year from approval
                instance.user.subscription_due_date = get_annual_renewal_date(
                    instance.updated_at or timezone.now()
                )
                instance.user.save(update_fields=['subscription_due_date'])
                logger.info(f"Set subscription due date for user {instance.user.email} to {instance.user.subscription_due_date}")
                
                # Send approval email
                try:
                    # Use the username from the application
                    user_name = instance.username if instance.username else f"{instance.user.first_name} {instance.user.last_name}".strip()
                    if not user_name:
                        user_name = instance.user.email.split('@')[0]
                    
                    email_sent = EmailService.send_approval_email(
                        email=instance.user.email,
                        user_name=user_name,
                        apf_membership_number=instance.user.apf_membership_number or None,
                    )
                    if email_sent:
                        logger.info(f"Approval email sent successfully to {instance.user.email} with username: {user_name}")
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
