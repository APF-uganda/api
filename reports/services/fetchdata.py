from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class ReportDataFetcher:
    @staticmethod
    def get_data(template, filters_applied=None):
        report_type = template.report_type.lower()
        filters = filters_applied or {}
        
        # Helper to get date range
        def get_date_limit(period):
            now = timezone.now()
            if period == 'Last 7 Days': return now - timedelta(days=7)
            if period == 'Last 30 Days': return now - timedelta(days=30)
            if period == 'Last 90 Days': return now - timedelta(days=90)
            if period == 'Last 12 Months': return now - timedelta(days=365)
            return None

        date_limit = get_date_limit(filters.get('period'))

        # 1. Membership Report
        if report_type == 'membership':
            queryset = User.objects.all()
            if date_limit:
                queryset = queryset.filter(created_at__gte=date_limit)
            
            return list(queryset.values(
                'email', 'first_name', 'last_name', 'membership_category', 'is_active', 'created_at'
            ))
        
        # 2. Applications Report
        elif report_type == 'applications':
            from applications.models import Application
            queryset = Application.objects.all()
            if date_limit:
                queryset = queryset.filter(created_at__gte=date_limit)
            
            return list(queryset.values(
                'id', 'user__email', 'status', 'application_type', 'created_at'
            ))
        
        #  Financial Report 
        elif report_type == 'financial' or report_type == 'system':
            from payments.models import Payment
            queryset = Payment.objects.all()
            if date_limit:
                queryset = queryset.filter(created_at__gte=date_limit)
                
            return list(queryset.values(
                'id', 'user__email', 'amount', 'status', 'created_at'
            ))

        return [{"Message": f"No data found for category: {report_type}"}]