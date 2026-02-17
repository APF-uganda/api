from applications.models import Application
from Documents.models import Document, MemberDocument
from authentication.models import User, UserRole
from profiles.models import UserProfile, ProfileActivityLog
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q, Sum
from decimal import Decimal


def get_total_applications():
    return Application.objects.count()

def get_total_members():
    return Application.objects.filter(status='approved').count()

def get_application_statistics():
    """Get comprehensive application statistics with trends."""
    now = timezone.now()
    last_month = now - timedelta(days=30)
    
    # Current counts
    total_applications = Application.objects.count()
    pending_applications = Application.objects.filter(status='pending').count()
    approved_applications = Application.objects.filter(status='approved').count()
    rejected_applications = Application.objects.filter(status='rejected').count()
    paid_applications = Application.objects.filter(payment_status='success').count()
    
    # Calculate total revenue from all sources
    # Revenue is generated from successful payments regardless of approval status
    # This includes application fees, event payments, renewals, etc.
    application_revenue = Application.objects.filter(
        payment_status='success'
    ).aggregate(
        total=Sum('payment_amount')
    )['total'] or Decimal('0.00')
    
    # Debug logging to help troubleshoot revenue calculation
    print(f'DEBUG: Total applications with successful payments: {paid_applications}')
    print(f'DEBUG: Calculated application revenue: {application_revenue}')
    
    # 2. Other revenue sources can be added here when implemented
    # For example, event registrations, annual renewals, donations, etc.
    # For now, we'll just use application revenue
    # TODO: Add separate models for different payment types (events, renewals, etc.)
    total_revenue = application_revenue
    
    # Calculate last month's revenue for trend
    last_month_revenue = Application.objects.filter(
        payment_status='success',
        updated_at__lt=last_month
    ).aggregate(
        total=Sum('payment_amount')
    )['total'] or Decimal('0.00')
    
    # Last month counts for trend calculation
    last_month_total = Application.objects.filter(submitted_at__lt=last_month).count()
    last_month_pending = Application.objects.filter(
        status='pending', 
        submitted_at__lt=last_month
    ).count()
    last_month_approved = Application.objects.filter(
        status='approved', 
        updated_at__lt=last_month
    ).count()
    last_month_rejected = Application.objects.filter(
        status='rejected', 
        updated_at__lt=last_month
    ).count()
    last_month_paid = Application.objects.filter(
        payment_status='success', 
        updated_at__lt=last_month
    ).count()
    
    # Calculate percentage changes
    def calculate_change(current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 1)
    
    return {
        'total_applications': total_applications,
        'pending_applications': pending_applications,
        'approved_applications': approved_applications,
        'rejected_applications': rejected_applications,
        'paid_applications': paid_applications,
        'total_revenue': float(total_revenue),
        'trends': {
            'total_change': calculate_change(total_applications, last_month_total),
            'pending_change': calculate_change(pending_applications, last_month_pending),
            'approved_change': calculate_change(approved_applications, last_month_approved),
            'rejected_change': calculate_change(rejected_applications, last_month_rejected),
            'paid_change': calculate_change(paid_applications, last_month_paid),
            'revenue_change': calculate_change(float(total_revenue), float(last_month_revenue)),
        }
    }

def get_recent_applications(limit=5):
    """Get recent applications for dashboard display."""
    return Application.objects.only(
        'id', 'username', 'email', 'first_name', 'last_name',
        'status', 'payment_status', 'submitted_at', 'updated_at'
    ).order_by('-submitted_at')[:limit]


def get_recent_payments(limit=5):
    """Get recent successful payments for dashboard display."""
    from django.db.models import F
    
    # Get applications with successful payments, ordered by most recent
    payments = Application.objects.filter(
        payment_status='success'
    ).select_related('user').annotate(
        member_name=F('first_name'),
        member_last_name=F('last_name')
    ).order_by('-updated_at')[:limit]
    
    return [{
        'id': payment.id,
        'payment_id': payment.payment_transaction_reference or f'PAY-{payment.id}',
        'member_name': f"{payment.first_name} {payment.last_name}",
        'amount': float(payment.payment_amount),
        'payment_method': payment.payment_method,
        'status': payment.payment_status,
        'created_at': payment.updated_at,
    } for payment in payments]


def _safe_add_year(input_date):
    if not input_date:
        return None
    try:
        return input_date.replace(year=input_date.year + 1)
    except ValueError:
        return input_date.replace(month=2, day=28, year=input_date.year + 1)


def _get_member_since_date(user):
    approved_app = (
        Application.objects.filter(user=user, status='approved')
        .order_by('updated_at')
        .first()
    )
    if approved_app and approved_app.updated_at:
        return approved_app.updated_at.date()
    if user.created_at:
        return user.created_at.date()
    return None


def get_member_dashboard_data(user, request=None):
    """Build member dashboard data using existing models."""
    profile = UserProfile.objects.filter(user=user).first()
    display_name = profile.get_full_name() if profile else user.full_name
    member_since = _get_member_since_date(user)
    next_renewal_date = _safe_add_year(member_since) if member_since else None

    app_docs = Document.objects.filter(application__user=user).order_by('-uploaded_at')[:10]
    member_docs = MemberDocument.objects.filter(user=user).order_by('-uploaded_at')[:10]
    documents = []

    def _append_doc(doc):
        file_url = None
        if doc.file and hasattr(doc.file, "url"):
            file_url = request.build_absolute_uri(doc.file.url) if request else doc.file.url
        documents.append({
            "id": doc.id,
            "name": doc.file_name,
            "document_type": doc.document_type or "",
            "uploaded_at": doc.uploaded_at,
            "file_url": file_url,
        })

    for doc in app_docs:
        _append_doc(doc)
    for doc in member_docs:
        _append_doc(doc)

    activity_logs = (
        ProfileActivityLog.objects.filter(profile__user=user)
        .order_by('-timestamp')[:10]
    )
    action_labels = {
        "created": "Profile created",
        "updated": "Profile updated",
        "picture_uploaded": "Profile picture uploaded",
        "picture_removed": "Profile picture removed",
        "privacy_changed": "Privacy settings updated",
        "notifications_changed": "Notification preferences updated",
    }

    def _format_value(value):
        if value is None or value == "":
            return ""
        if isinstance(value, bool):
            return "enabled" if value else "disabled"
        text = str(value)
        if len(text) > 40:
            return f"{text[:37]}..."
        return text

    def _humanize_field(field_name):
        if not field_name:
            return ""
        return field_name.replace('_', ' ').strip().title()

    def _build_message(log):
        meta = log.metadata or {}
        changes = meta.get("changes") or []
        document_name = meta.get("document_name")

        if document_name and log.action in ["picture_uploaded", "picture_removed"]:
            return f"{action_labels.get(log.action, 'Profile picture updated')}: {document_name}"

        if changes:
            if len(changes) == 1:
                change = changes[0]
                field_label = _humanize_field(change.get("field") or log.field_changed)
                old_val = _format_value(change.get("old"))
                new_val = _format_value(change.get("new"))

                if old_val and new_val:
                    return f"Updated {field_label} from {old_val} to {new_val}"
                if new_val:
                    return f"Set {field_label} to {new_val}"
                if old_val and not new_val:
                    return f"Cleared {field_label}"
                return f"Updated {field_label}"

            labels = [
                _humanize_field(change.get("field"))
                for change in changes
                if change.get("field")
            ]
            labels = [label for label in labels if label]
            if labels:
                listed = ", ".join(labels[:3])
                suffix = "..." if len(labels) > 3 else ""
                return f"Updated {len(labels)} fields: {listed}{suffix}"

        return action_labels.get(log.action, "Account activity")

    recent_activity = [
        {
            "id": log.id,
            "action": log.action,
            "field_changed": log.field_changed or "",
            "timestamp": log.timestamp,
            "message": _build_message(log),
        }
        for log in activity_logs
    ]

    # Fetch UserNotification objects (announcements from admin)
    from notifications.models import UserNotification
    user_notifications = (
        UserNotification.objects.filter(user=user)
        .order_by('-created_at')[:10]
    )
    notifications_data = [
        {
            "id": notif.id,
            "message": notif.message,
            "type": notif.notification_type,
            "is_read": notif.is_read,
            "created_at": notif.created_at,
            "application_id": None,  # UserNotifications are not tied to applications
        }
        for notif in user_notifications
    ]

    return {
        "profile": {
            "display_name": display_name,
            "membership_category": getattr(user, "membership_category", "") or "",
            "membership_status": "Active" if user.is_active else "Inactive",
            "member_since": member_since,
            "next_renewal_date": next_renewal_date,
        },
        "documents": documents,
        "recent_activity": recent_activity,
        "notifications": notifications_data,
    }

