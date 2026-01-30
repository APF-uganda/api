from applications.models import Application
from authentication.models import User, UserRole
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

