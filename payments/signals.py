"""Django signals for Payment model
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta, date
from payments.models import Payment
import logging

logger = logging.getLogger(__name__)


def get_annual_renewal_date(base_date=None):
    """
    Calculate annual renewal date - always March 31st.
    If joining after March 31st, renewal is March 31st of next year.
    If joining before or on March 31st, renewal is March 31st of current year.
    """
    if base_date is None:
        base_date = timezone.now().date()
    elif hasattr(base_date, 'date'):
        base_date = base_date.date()

    # Renewal date is always March 31st
    renewal_month = 3
    renewal_day = 31
    
    # Determine the year for renewal
    current_year = base_date.year
    renewal_date_this_year = base_date.replace(month=renewal_month, day=renewal_day, year=current_year)
    
    # If the base date is after March 31st of the current year, 
    # set renewal to March 31st of next year
    if base_date > renewal_date_this_year:
        return base_date.replace(month=renewal_month, day=renewal_day, year=current_year + 1)
    else:
        # Otherwise, renewal is March 31st of the current year
        return renewal_date_this_year


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
            
            # Set subscription due date to one year from payment completion
            new_due_date = get_annual_renewal_date(instance.completed_at or timezone.now())
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


@receiver(post_save, sender=Payment)
def reconcile_invoice_payment(sender, instance, created, **kwargs):
    """
    Signal handler to automatically reconcile payments with membership invoices
    
    When a payment with an invoice_number is marked as completed:
    1. Find the invoice using the invoice_number
    2. Verify the invoice belongs to the payment user
    3. Create InvoicePaymentLink
    4. Update invoice amount_paid
    5. Invoice status is auto-updated by the model's save method
    6. Notify admins of successful payment
    
    Args:
        sender: The model class (Payment)
        instance: The actual Payment instance being saved
        created: Boolean indicating if this is a new instance
        **kwargs: Additional keyword arguments
    """
    # Only proceed if payment is completed and has an invoice number
    if instance.status == Payment.STATUS_COMPLETED and instance.invoice_number and instance.user:
        try:
            from admin_management.models import MembershipInvoice, InvoicePaymentLink
            from decimal import Decimal
            
            # Find the invoice
            invoice = MembershipInvoice.objects.filter(
                invoice_number=instance.invoice_number
            ).first()
            
            if not invoice:
                logger.warning(
                    f"Invoice not found for payment {instance.transaction_reference}: "
                    f"invoice_number={instance.invoice_number}"
                )
                return
            
            # Verify invoice belongs to the payment user
            if invoice.user != instance.user:
                logger.error(
                    f"Invoice {invoice.invoice_number} belongs to {invoice.user.email} "
                    f"but payment {instance.transaction_reference} is from {instance.user.email}"
                )
                return
            
            # Check if link already exists (idempotency)
            existing_link = InvoicePaymentLink.objects.filter(
                invoice=invoice,
                payment=instance
            ).first()
            
            if existing_link:
                logger.info(
                    f"Invoice payment link already exists: "
                    f"invoice={invoice.invoice_number}, payment={instance.transaction_reference}"
                )
                return
            
            # Create invoice payment link
            link = InvoicePaymentLink.objects.create(
                invoice=invoice,
                payment=instance,
                amount=Decimal(str(instance.amount))
            )
            
            # Update invoice amount_paid (this will trigger invoice.save() which updates status)
            invoice.record_payment(instance.amount)
            
            logger.info(
                f"Successfully reconciled payment to invoice: "
                f"invoice={invoice.invoice_number}, payment={instance.transaction_reference}, "
                f"amount={instance.amount}, new_balance={invoice.balance_due}, status={invoice.status}"
            )
            
            # Notify admins of successful payment
            notify_admins_of_payment(instance, invoice)
            
        except Exception as e:
            logger.error(
                f"Error reconciling invoice payment for {instance.transaction_reference}: {e}",
                exc_info=True
            )


def notify_admins_of_payment(payment, invoice):
    """
    Send notification to all admin users about successful payment
    
    Args:
        payment: Payment instance
        invoice: MembershipInvoice instance
    """
    try:
        from notifications.models import UserNotification
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Get all admin users
        admin_users = User.objects.filter(is_staff=True, is_active=True)
        
        if not admin_users.exists():
            logger.warning("No admin users found to notify about payment")
            return
        
        # Prepare notification details
        title = f"Payment Received: {payment.transaction_reference}"
        message = (
            f"Member {payment.user.full_name or payment.user.email} has successfully paid "
            f"UGX {payment.amount:,.0f} for invoice {invoice.invoice_number}. "
            f"Invoice status: {invoice.get_status_display()}. "
            f"Balance due: UGX {invoice.balance_due:,.0f}."
        )
        
        # Create notification for each admin
        notifications_created = 0
        for admin in admin_users:
            UserNotification.objects.create(
                user=admin,
                title=title,
                message=message,
                notification_type='payment',
                priority='medium',
                is_read=False
            )
            notifications_created += 1
        
        logger.info(
            f"Created {notifications_created} admin notifications for payment "
            f"{payment.transaction_reference}"
        )
        
    except Exception as e:
        logger.error(f"Error notifying admins of payment {payment.transaction_reference}: {e}")
