"""
Centralized service for creating admin notifications
Ensures all admins are notified of important events in the system
"""
import logging
from django.contrib.auth import get_user_model
from django.db.models import Q

logger = logging.getLogger(__name__)
User = get_user_model()


def notify_admins(title, message, notification_type='info', priority='medium', metadata=None):
    """
    Send notification to all active admin users
    
    Args:
        title: Notification title
        message: Notification message
        notification_type: Type of notification (info, success, warning, error, payment, document)
        priority: Priority level (low, medium, high)
        metadata: Optional dictionary with additional data (e.g., actionUrl, userId)
    
    Returns:
        int: Number of notifications created
    """
    try:
        from notifications.models import UserNotification
        
        # Get all active admin users (role='1' or is_staff=True)
        admin_users = User.objects.filter(
            is_active=True
        ).filter(
            Q(role='1') | Q(is_staff=True)
        ).distinct()
        
        if not admin_users.exists():
            logger.warning(f"No admin users found to notify: {title}")
            return 0
        
        notifications_created = 0
        for admin in admin_users:
            notification = UserNotification.objects.create(
                user=admin,
                title=title,
                message=message,
                notification_type=notification_type,
                priority=priority,
                is_read=False
            )
            
            # Add metadata if provided
            if metadata:
                notification.metadata = metadata
                notification.save(update_fields=['metadata'])
            
            notifications_created += 1
        
        logger.info(f"Created {notifications_created} admin notifications: {title}")
        return notifications_created
        
    except Exception as e:
        logger.error(f"Failed to create admin notifications: {title} - {e}")
        return 0


def notify_admin_new_application(application):
    """Notify admins of new application submission"""
    member_name = application.username or application.email
    return notify_admins(
        title="New Membership Application",
        message=f"{member_name} has submitted a new membership application. Click to review in Applications.",
        notification_type="info",
        priority="high",
        metadata={
            'actionUrl': '/admin/approval',
            'applicationId': str(application.id)
        }
    )


def notify_admin_payment_proof(user, payment_type, amount, reference):
    """Notify admins of new proof of payment upload"""
    member_name = getattr(user, 'full_name', None) or user.email
    
    type_labels = {
        'membership_renewal': 'Membership Renewal',
        'donation': 'Donation',
        'event': 'Event Payment',
        'other': 'Other Payment'
    }
    payment_label = type_labels.get(payment_type, 'Payment')
    
    return notify_admins(
        title="New Proof of Payment",
        message=f"{member_name} uploaded proof of payment for {payment_label} (Amount: UGX {amount:,.0f}, Ref: {reference}). Click to review in Manage Users.",
        notification_type="info",
        priority="high",
        metadata={
            'actionUrl': '/admin/manageusers',
            'userId': str(user.id),
            'paymentType': payment_type,
            'reference': reference
        }
    )


def notify_admin_document_upload(user, document_name, document_type):
    """Notify admins of new document upload"""
    member_name = getattr(user, 'full_name', None) or user.email
    
    return notify_admins(
        title="New Document Uploaded",
        message=f"{member_name} uploaded \"{document_name}\" for review. Click to view in Manage Users.",
        notification_type="info",
        priority="medium",
        metadata={
            'actionUrl': '/admin/manageusers',
            'userId': str(user.id),
            'documentType': document_type
        }
    )
