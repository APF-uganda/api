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
    application_revenue = Application.objects.filter(
        payment_status='success'
    ).aggregate(
        total=Sum('payment_amount')
    )['total'] or Decimal('0.00')
    
    print(f'DEBUG: Total applications with successful payments: {paid_applications}')
    print(f'DEBUG: Calculated application revenue: {application_revenue}')
    
    total_revenue = application_revenue
    
    # FIX 1: Calculate last month's revenue for trend (last 30 days)
    last_month_revenue = Application.objects.filter(
        payment_status='success',
        updated_at__gte=last_month,
        updated_at__lte=now
    ).aggregate(
        total=Sum('payment_amount')
    )['total'] or Decimal('0.00')
    
    # FIX 2: Last month counts for trend calculation (last 30 days)
    last_month_total = Application.objects.filter(
        submitted_at__gte=last_month,
        submitted_at__lte=now
    ).count()
    last_month_pending = Application.objects.filter(
        status='pending',
        submitted_at__gte=last_month,
        submitted_at__lte=now
    ).count()
    last_month_approved = Application.objects.filter(
        status='approved',
        updated_at__gte=last_month,
        updated_at__lte=now
    ).count()
    last_month_rejected = Application.objects.filter(
        status='rejected',
        updated_at__gte=last_month,
        updated_at__lte=now
    ).count()
    last_month_paid = Application.objects.filter(
        payment_status='success',
        updated_at__gte=last_month,
        updated_at__lte=now
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

    # FIX 3: Safe field mapping for both Document and MemberDocument models
    def _append_doc(doc):
        file_obj = getattr(doc, "file", None) or getattr(doc, "document", None) or getattr(doc, "document_file", None)
        file_url = None
        if file_obj and hasattr(file_obj, "url"):
            file_url = request.build_absolute_uri(file_obj.url) if request else file_obj.url
        
        documents.append({
            "id": doc.id,
            "name": getattr(doc, "file_name", None) or getattr(doc, "document_name", None) or getattr(doc, "name", "") or "",
            "document_type": getattr(doc, "document_type", "") or getattr(doc, "doc_type", "") or "",
            "uploaded_at": getattr(doc, "uploaded_at", None) or getattr(doc, "created_at", None) or getattr(doc, "uploaded_on", None),
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
    
    # Fetch UserNotification objects (document activities, announcements, etc.)
    from notifications.models import UserNotification
    user_notifications = (
        UserNotification.objects.filter(user=user)
        .order_by('-created_at')[:20]
    )
    
    # FIX 4: Helper to convert notification to activity format with complete message
    def _notif_to_activity(notif):
        # Build complete message from title and message
        text = f"{notif.title}: {notif.message}".strip() if notif.title else notif.message
        
        # Determine action type based on title and message (safe checks)
        action_type = "other"
        title_l = (notif.title or "").lower()
        msg_l = (notif.message or "").lower()
        
        if "upload" in title_l or "replace" in title_l:
            action_type = "document_upload"
        elif "remove" in title_l or "delete" in title_l:
            action_type = "document_remove"
        elif "approved" in msg_l:
            action_type = "document_approved"
        elif "rejected" in msg_l:
            action_type = "document_rejected"
        
        return {
            "id": f"notif_{notif.id}",
            "action": action_type,
            "field_changed": "",
            "timestamp": notif.created_at,
            "message": text,
        }
    
    # Add document-related notifications to recent activity
    for notif in user_notifications:
        # Only include document-related activities (not announcements)
        if any(keyword in (notif.title or "").lower() for keyword in ['document', 'upload', 'replace', 'remove']):
            recent_activity.append(_notif_to_activity(notif))
    
    # Sort all activities by timestamp (most recent first)
    recent_activity = sorted(recent_activity, key=lambda x: x['timestamp'], reverse=True)
    
    # Deduplicate activities based on timestamp, message, and action
    seen = set()
    deduped = []
    for item in recent_activity:
        key = (item["timestamp"], item["message"], item["action"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    
    # Limit to 15 most recent unique activities
    recent_activity = deduped[:15]
    
    # Separate notifications for the notifications section
    notifications_data = [
        {
            "id": notif.id,
            "message": notif.message,
            "type": notif.notification_type,
            "is_read": notif.is_read,
            "created_at": notif.created_at,
            "application_id": None,
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

