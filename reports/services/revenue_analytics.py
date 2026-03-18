"""
Revenue Analytics Service
Provides revenue and payment analytics for dashboard charts
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.utils import timezone

from payments.models import Payment, ManualPayment
from applications.models import Application
from admin_management.models import MembershipInvoice
from .base import BaseAnalyticsService


class RevenueAnalyticsService(BaseAnalyticsService):
    """
    Service for revenue and payment analytics
    Handles revenue trends, payment status distribution, and financial metrics
    """
    
    def get_metrics(self, period_start: datetime, period_end: datetime) -> Dict[str, Any]:
        """Get revenue metrics for the specified period"""
        
        # Calculate total revenue from all sources
        application_revenue = self._get_application_revenue(period_start, period_end)
        manual_payment_revenue = self._get_manual_payment_revenue(period_start, period_end)
        membership_revenue = self._get_membership_revenue(period_start, period_end)
        
        total_revenue = application_revenue + manual_payment_revenue + membership_revenue
        
        # Get payment statistics
        payment_stats = self._get_payment_statistics(period_start, period_end)
        
        # Calculate growth rate (compare with previous period)
        previous_period_start = period_start - (period_end - period_start)
        previous_revenue = self._get_total_revenue(previous_period_start, period_start)
        
        growth_rate = 0
        if previous_revenue > 0:
            growth_rate = ((total_revenue - previous_revenue) / previous_revenue) * 100
        
        return {
            'total_revenue': float(total_revenue),
            'application_revenue': float(application_revenue),
            'manual_payment_revenue': float(manual_payment_revenue),
            'membership_revenue': float(membership_revenue),
            'growth_rate': round(float(growth_rate), 2),
            'payment_statistics': payment_stats,
            'period_start': period_start.isoformat(),
            'period_end': period_end.isoformat()
        }
    
    def get_chart_data(self, chart_type: str, period: str = '30d', **kwargs) -> Dict[str, Any]:
        """Get chart data for revenue visualizations"""
        period_start, period_end = self.get_period_dates(period)
        
        if chart_type == 'revenue_trends':
            return self._get_revenue_trends_chart(period_start, period_end, period)
        elif chart_type == 'payment_status':
            return self._get_payment_status_chart(period_start, period_end)
        elif chart_type == 'revenue_sources':
            return self._get_revenue_sources_chart(period_start, period_end)
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")
    
    def _get_application_revenue(self, period_start: datetime, period_end: datetime) -> Decimal:
        """Calculate revenue from application payments"""
        revenue = Application.objects.filter(
            payment_status__in=['success', 'completed'],
            updated_at__gte=period_start,
            updated_at__lte=period_end
        ).aggregate(
            total=Sum('payment_amount')
        )['total'] or Decimal('0.00')
        
        return revenue
    
    def _get_manual_payment_revenue(self, period_start: datetime, period_end: datetime) -> Decimal:
        """Calculate revenue from verified manual payments"""
        revenue = ManualPayment.objects.filter(
            status=ManualPayment.STATUS_VERIFIED,
            updated_at__gte=period_start,
            updated_at__lte=period_end
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        return revenue
    
    def _get_membership_revenue(self, period_start: datetime, period_end: datetime) -> Decimal:
        """Calculate revenue from membership renewals"""
        revenue = MembershipInvoice.objects.filter(
            status=MembershipInvoice.STATUS_PAID,
            paid_at__gte=period_start,
            paid_at__lte=period_end
        ).aggregate(
            total=Sum('amount_paid')
        )['total'] or Decimal('0.00')
        
        return revenue
    
    def _get_total_revenue(self, period_start: datetime, period_end: datetime) -> Decimal:
        """Calculate total revenue for a period"""
        app_revenue = self._get_application_revenue(period_start, period_end)
        manual_revenue = self._get_manual_payment_revenue(period_start, period_end)
        membership_revenue = self._get_membership_revenue(period_start, period_end)
        
        return app_revenue + manual_revenue + membership_revenue
    
    def _get_payment_statistics(self, period_start: datetime, period_end: datetime) -> Dict[str, Any]:
        """Get payment status statistics"""
        
        # Get payment counts by status
        payment_stats = Payment.objects.filter(
            created_at__gte=period_start,
            created_at__lte=period_end
        ).values('status').annotate(
            count=Count('id')
        )
        
        # Convert to dictionary
        stats = {item['status']: item['count'] for item in payment_stats}
        
        # Add manual payment stats
        manual_stats = ManualPayment.objects.filter(
            created_at__gte=period_start,
            created_at__lte=period_end
        ).values('status').annotate(
            count=Count('id')
        )
        
        # Merge manual payment stats (map to standard payment statuses)
        status_mapping = {
            ManualPayment.STATUS_VERIFIED: 'completed',
            ManualPayment.STATUS_PENDING: 'pending',
            ManualPayment.STATUS_REJECTED: 'failed'
        }
        
        for item in manual_stats:
            mapped_status = status_mapping.get(item['status'], item['status'])
            stats[mapped_status] = stats.get(mapped_status, 0) + item['count']
        
        return stats
    
    def _get_revenue_trends_chart(self, period_start: datetime, period_end: datetime, period: str) -> Dict[str, Any]:
        """Get revenue trends chart data - showing daily revenue"""
        
        # Always use daily truncation for more granular view
        trunc_func = TruncDay
        date_format = '%Y-%m-%d'
        
        # Get application revenue by day
        app_revenue_data = Application.objects.filter(
            payment_status__in=['success', 'completed'],
            updated_at__gte=period_start,
            updated_at__lte=period_end
        ).annotate(
            period=trunc_func('updated_at')
        ).values('period').annotate(
            revenue=Sum('payment_amount')
        ).order_by('period')
        
        # Get manual payment revenue by day
        manual_revenue_data = ManualPayment.objects.filter(
            status=ManualPayment.STATUS_VERIFIED,
            updated_at__gte=period_start,
            updated_at__lte=period_end
        ).annotate(
            period=trunc_func('updated_at')
        ).values('period').annotate(
            revenue=Sum('amount')
        ).order_by('period')
        
        # Get membership revenue by day
        membership_revenue_data = MembershipInvoice.objects.filter(
            status=MembershipInvoice.STATUS_PAID,
            paid_at__gte=period_start,
            paid_at__lte=period_end
        ).annotate(
            period=trunc_func('paid_at')
        ).values('period').annotate(
            revenue=Sum('amount_paid')
        ).order_by('period')
        
        # Create a complete date range to fill gaps
        from datetime import timedelta
        current_date = period_start.date()
        end_date = period_end.date()
        all_dates = []
        
        while current_date <= end_date:
            all_dates.append(current_date)
            current_date += timedelta(days=1)
        
        # Combine all revenue sources by day
        revenue_by_date = {}
        
        # Initialize all dates with 0
        for date in all_dates:
            revenue_by_date[date.strftime(date_format)] = 0.0
        
        # Add application revenue
        for item in app_revenue_data:
            date_key = item['period'].strftime(date_format)
            revenue_by_date[date_key] += float(item['revenue'] or 0)
        
        # Add manual payment revenue
        for item in manual_revenue_data:
            date_key = item['period'].strftime(date_format)
            revenue_by_date[date_key] += float(item['revenue'] or 0)
        
        # Add membership revenue
        for item in membership_revenue_data:
            date_key = item['period'].strftime(date_format)
            revenue_by_date[date_key] += float(item['revenue'] or 0)
        
        # Sort by date and extract labels and data
        sorted_dates = sorted(revenue_by_date.items())
        
        # Format labels for better display
        labels = []
        data = []
        
        for date_str, revenue in sorted_dates:
            # Convert to more readable format
            date_obj = datetime.strptime(date_str, date_format)
            
            # Format based on period length for readability
            if len(sorted_dates) <= 7:  # 7 days or less - show full date
                label = date_obj.strftime('%b %d')
            elif len(sorted_dates) <= 31:  # Up to a month - show day
                label = date_obj.strftime('%m/%d')
            else:  # More than a month - show every few days
                if date_obj.day % 3 == 1:  # Show every 3rd day
                    label = date_obj.strftime('%m/%d')
                else:
                    label = ''  # Empty label for intermediate days
            
            labels.append(label)
            data.append(revenue)
        
        return self.format_chart_data(
            labels=labels,
            data=data,
            title=f'Daily Revenue Trends ({period})'
        )
    
    def _get_payment_status_chart(self, period_start: datetime, period_end: datetime) -> Dict[str, Any]:
        """Get payment status distribution chart data"""
        
        # Get payment status counts
        payment_stats = self._get_payment_statistics(period_start, period_end)
        
        # Group statuses into 3 main categories
        completed_count = (
            payment_stats.get('completed', 0) + 
            payment_stats.get('success', 0)  # Include success as completed
        )
        
        pending_count = (
            payment_stats.get('pending', 0) + 
            payment_stats.get('processing', 0)  # Include processing as pending
        )
        
        rejected_count = (
            payment_stats.get('failed', 0) + 
            payment_stats.get('timeout', 0) + 
            payment_stats.get('cancelled', 0) + 
            payment_stats.get('rejected', 0)  # Group all failures as rejected
        )
        
        # Only include categories with data
        labels = []
        data = []
        
        if completed_count > 0:
            labels.append('Completed')
            data.append(completed_count)
        
        if pending_count > 0:
            labels.append('Pending')
            data.append(pending_count)
        
        if rejected_count > 0:
            labels.append('Rejected')
            data.append(rejected_count)
        
        # If no data, show empty state
        if not labels:
            labels = ['No Data']
            data = [0]
        
        return self.format_chart_data(
            labels=labels,
            data=data,
            title='Payment Status Distribution'
        )
    
    def _get_revenue_sources_chart(self, period_start: datetime, period_end: datetime) -> Dict[str, Any]:
        """Get revenue sources breakdown chart data"""
        
        app_revenue = float(self._get_application_revenue(period_start, period_end))
        manual_revenue = float(self._get_manual_payment_revenue(period_start, period_end))
        membership_revenue = float(self._get_membership_revenue(period_start, period_end))
        
        labels = []
        data = []
        
        if app_revenue > 0:
            labels.append('Application Fees')
            data.append(app_revenue)
        
        if manual_revenue > 0:
            labels.append('Manual Payments')
            data.append(manual_revenue)
        
        if membership_revenue > 0:
            labels.append('Membership Renewals')
            data.append(membership_revenue)
        
        return self.format_chart_data(
            labels=labels,
            data=data,
            title='Revenue Sources'
        )