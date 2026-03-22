from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class ReportDataFetcher:
    @staticmethod
    def get_data(template, filters_applied=None):
        report_type = str(template.report_type).lower()
        filters = filters_applied or {}
        
        def get_date_limit(period_label):
            now = timezone.now()
            p = str(period_label).lower()
            if '7' in p: return now - timedelta(days=7)
            if '30' in p: return now - timedelta(days=30)
            if '90' in p: return now - timedelta(days=90)
            if '12' in p: return now - timedelta(days=365)
            return None

        date_limit = get_date_limit(filters.get('period'))

        try:
            # 1. MEMBERSHIP REPORT
            if report_type == 'membership':
                queryset = User.objects.all()
                
                # FIX: Using 'created_at' as identified in your DB error log
                if date_limit:
                    queryset = queryset.filter(created_at__gte=date_limit)
                
                # Fetching fields that actually exist on your User model
                data = list(queryset.values(
                    'id', 'email', 'first_name', 'last_name', 'role', 
                    'membership_category', 'is_active', 'created_at'
                ))
                
                # Format for the Chart Generator
                for item in data:
                    item['status'] = 'Active' if item.get('is_active') else 'Inactive'
                    # Convert datetime to string for CSV/JSON compatibility
                    if item.get('created_at'):
                        item['joined_date'] = item['created_at'].strftime('%Y-%m-%d')
                return data
            
            # 2. APPLICATIONS REPORT
            elif report_type == 'applications':
                # Use absolute import to avoid issues in background tasks
                from applications.models import Application
                queryset = Application.objects.all()
                
                if date_limit:
                    queryset = queryset.filter(submitted_at__gte=date_limit)
                
                # Selecting fields available in your Application model choices
                data = list(queryset.values(
                    'application_id', 'first_name', 'last_name', 
                    'organization', 'payment_status', 'status', 'submitted_at'
                ))
                
                for item in data:
                    # 'status' will be used by ReportGenerator for the bar chart
                    if item.get('submitted_at'):
                        item['date'] = item['submitted_at'].strftime('%Y-%m-%d')
                return data
            
            # 3. FINANCIAL / REVENUE REPORT
            elif report_type in ['financial', 'system', 'revenue', 'payments']:
                from payments.models import Payment
                queryset = Payment.objects.all()
                
                if date_limit:
                    queryset = queryset.filter(created_at__gte=date_limit)
                    
                data = list(queryset.values(
                    'id', 'amount', 'payment_method', 'status', 'created_at'
                ))
                
                for item in data:
                    if item.get('created_at'):
                        item['transaction_date'] = item['created_at'].strftime('%Y-%m-%d')
                return data

        except Exception as e:
            logger.error(f"Fetcher Error: {str(e)}")
           
            return [{"Error": f"Database Fetch Error: {str(e)}"}]

        return [{"Message": f"No data found for category: {report_type}"}]