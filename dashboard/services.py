from applications.models import Application, Document
from authentication.models import User, UserRole
from profiles.models import UserProfile, ProfileActivityLog
from notifications.models import Notification
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q


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
        'trends': {
            'total_change': calculate_change(total_applications, last_month_total),
            'pending_change': calculate_change(pending_applications, last_month_pending),
            'approved_change': calculate_change(approved_applications, last_month_approved),
            'rejected_change': calculate_change(rejected_applications, last_month_rejected),
            'paid_change': calculate_change(paid_applications, last_month_paid),
        }
    }

def get_recent_applications(limit=5):
    """Get recent applications for dashboard display."""
    return Application.objects.select_related('user').order_by('-submitted_at')[:limit]


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

    document_qs = Document.objects.filter(application__user=user).order_by('-uploaded_at')[:10]
    documents = []
    for doc in document_qs:
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

    activity_logs = (
        ProfileActivityLog.objects.filter(profile__user=user)
        .order_by('-timestamp')[:10]
    )
    recent_activity = [
        {
            "id": log.id,
            "action": log.action,
            "field_changed": log.field_changed or "",
            "timestamp": log.timestamp,
        }
        for log in activity_logs
    ]

    notifications = (
        Notification.objects.filter(user=user)
        .order_by('-created_at')[:10]
    )
    notifications_data = [
        {
            "id": notif.id,
            "message": notif.message,
            "type": notif.type,
            "is_read": notif.is_read,
            "created_at": notif.created_at,
            "application_id": notif.application_id,
        }
        for notif in notifications
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

