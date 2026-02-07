"""
Admin interface for payment models.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import Payment, PaymentConfig


class DateRangeFilter(admin.SimpleListFilter):
    """Custom filter for date ranges."""
    title = 'date range'
    parameter_name = 'date_range'
    
    def lookups(self, request, model_admin):
        return (
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('week', 'Past 7 days'),
            ('month', 'This month'),
            ('year', 'This year'),
        )
    
    def queryset(self, request, queryset):
        now = timezone.now()
        
        if self.value() == 'today':
            return queryset.filter(created_at__date=now.date())
        
        if self.value() == 'yesterday':
            yesterday = now.date() - timedelta(days=1)
            return queryset.filter(created_at__date=yesterday)
        
        if self.value() == 'week':
            week_ago = now - timedelta(days=7)
            return queryset.filter(created_at__gte=week_ago)
        
        if self.value() == 'month':
            return queryset.filter(
                created_at__year=now.year,
                created_at__month=now.month
            )
        
        if self.value() == 'year':
            return queryset.filter(created_at__year=now.year)
        
        return queryset


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin interface for Payment model."""
    
    list_display = [
        'transaction_reference',
        'user',
        'masked_phone',
        'amount',
        'currency',
        'provider',
        'colored_status',
        'created_at',
    ]
    
    list_filter = [
        'status',
        'provider',
        DateRangeFilter,
        'currency',
    ]
    
    search_fields = [
        'transaction_reference',
        'provider_transaction_id',
        'user__email',
    ]
    
    date_hierarchy = 'created_at'
    
    readonly_fields = [
        'id',
        'transaction_reference',
        'provider_transaction_id',
        'user',
        'application',
        'phone_number',
        'amount',
        'currency',
        'provider',
        'status',
        'error_message',
        'formatted_provider_response',
        'created_at',
        'updated_at',
        'completed_at',
        'ip_address',
        'user_agent',
        'masked_phone',
    ]
    
    fieldsets = (
        ('Transaction Information', {
            'fields': (
                'id',
                'transaction_reference',
                'provider_transaction_id',
                'status',
            )
        }),
        ('User Information', {
            'fields': (
                'user',
                'application',
            )
        }),
        ('Payment Details', {
            'fields': (
                'masked_phone',
                'amount',
                'currency',
                'provider',
            )
        }),
        ('Status & Errors', {
            'fields': (
                'error_message',
                'formatted_provider_response',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
                'completed_at',
            )
        }),
        ('Audit Information', {
            'fields': (
                'ip_address',
                'user_agent',
            )
        }),
    )
    
    def masked_phone(self, obj):
        """Display masked phone number."""
        return obj.get_masked_phone()
    masked_phone.short_description = 'Phone Number'
    
    def formatted_provider_response(self, obj):
        """Display provider response as formatted JSON."""
        if not obj.provider_response:
            return '-'
        
        import json
        try:
            formatted_json = json.dumps(obj.provider_response, indent=2)
            return format_html(
                '<pre style="background: #f8f9fa; padding: 10px; border-radius: 5px; '
                'border: 1px solid #dee2e6; overflow-x: auto; max-width: 800px;">{}</pre>',
                formatted_json
            )
        except (TypeError, ValueError):
            return format_html(
                '<pre style="background: #f8f9fa; padding: 10px; border-radius: 5px; '
                'border: 1px solid #dee2e6; overflow-x: auto; max-width: 800px;">{}</pre>',
                str(obj.provider_response)
            )
    formatted_provider_response.short_description = 'Provider Response'
    
    def colored_status(self, obj):
        """Display status with color coding."""
        colors = {
            'completed': '#28a745',  # green
            'pending': '#ffc107',    # yellow
            'processing': '#17a2b8', # blue
            'failed': '#dc3545',     # red
            'timeout': '#fd7e14',    # orange
            'cancelled': '#6c757d',  # gray
        }
        color = colors.get(obj.status, '#000000')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    colored_status.short_description = 'Status'
    colored_status.admin_order_field = 'status'
    
    def changelist_view(self, request, extra_context=None):
        """Override changelist view to add payment statistics."""
        extra_context = extra_context or {}
        
        # Get all payments
        queryset = self.get_queryset(request)
        
        # Calculate total revenue (completed payments only)
        total_revenue = queryset.filter(
            status=Payment.STATUS_COMPLETED
        ).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Calculate success rate by provider
        mtn_stats = self._calculate_provider_stats(queryset, Payment.PROVIDER_MTN)
        airtel_stats = self._calculate_provider_stats(queryset, Payment.PROVIDER_AIRTEL)
        
        # Calculate overall success rate
        total_completed = queryset.filter(status=Payment.STATUS_COMPLETED).count()
        total_failed = queryset.filter(
            status__in=[Payment.STATUS_FAILED, Payment.STATUS_TIMEOUT]
        ).count()
        total_attempts = total_completed + total_failed
        overall_success_rate = (total_completed / total_attempts * 100) if total_attempts > 0 else 0
        
        # Payment status breakdown
        status_breakdown = {
            'pending': queryset.filter(status=Payment.STATUS_PENDING).count(),
            'processing': queryset.filter(status=Payment.STATUS_PROCESSING).count(),
            'completed': queryset.filter(status=Payment.STATUS_COMPLETED).count(),
            'failed': queryset.filter(status=Payment.STATUS_FAILED).count(),
            'timeout': queryset.filter(status=Payment.STATUS_TIMEOUT).count(),
            'cancelled': queryset.filter(status=Payment.STATUS_CANCELLED).count(),
        }
        
        extra_context['payment_statistics'] = {
            'total_revenue': total_revenue,
            'overall_success_rate': round(overall_success_rate, 2),
            'mtn_stats': mtn_stats,
            'airtel_stats': airtel_stats,
            'status_breakdown': status_breakdown,
        }
        
        return super().changelist_view(request, extra_context=extra_context)
    
    def _calculate_provider_stats(self, queryset, provider):
        """Calculate statistics for a specific provider."""
        provider_payments = queryset.filter(provider=provider)
        
        total = provider_payments.count()
        completed = provider_payments.filter(status=Payment.STATUS_COMPLETED).count()
        failed = provider_payments.filter(
            status__in=[Payment.STATUS_FAILED, Payment.STATUS_TIMEOUT]
        ).count()
        
        attempts = completed + failed
        success_rate = (completed / attempts * 100) if attempts > 0 else 0
        
        revenue = provider_payments.filter(
            status=Payment.STATUS_COMPLETED
        ).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        return {
            'total': total,
            'completed': completed,
            'failed': failed,
            'success_rate': round(success_rate, 2),
            'revenue': revenue,
        }
    
    def has_add_permission(self, request):
        """Disable adding payments through admin."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable deleting payments through admin."""
        return False


@admin.register(PaymentConfig)
class PaymentConfigAdmin(admin.ModelAdmin):
    """Admin interface for PaymentConfig model."""
    
    list_display = ['key', 'value', 'description', 'updated_at']
    search_fields = ['key', 'description']
    readonly_fields = ['updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('key', 'value', 'description')
        }),
        ('Metadata', {
            'fields': ('updated_at',)
        }),
    )
