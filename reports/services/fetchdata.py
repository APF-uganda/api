from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class ReportDataFetcher:
    @staticmethod
    def get_data(template, filters_applied=None):
        report_type = str(template.report_type).lower()
        filters = filters_applied or {}
        
        def get_date_limit(period):
            now = timezone.now()
            p = str(period).lower()
            if '7 days' in p: return now - timedelta(days=7)
            if '30 days' in p: return now - timedelta(days=30)
            if '90 days' in p: return now - timedelta(days=90)
            if '12 months' in p: return now - timedelta(days=365)
            return None

        date_limit = get_date_limit(filters.get('period'))

        try:
            # 1. Membership Report
            if report_type == 'membership':
                queryset = User.objects.all()
                if date_limit:
                    queryset = queryset.filter(date_joined__gte=date_limit)
                
               
                data = list(queryset.values(
                    'email', 'first_name', 'last_name', 'is_active', 'date_joined'
                ))
                # Map is_active to a string so the chart can group by it
                for item in data:
                    item['status'] = 'Active' if item['is_active'] else 'Inactive'
                return data
            
            # 2. Applications Report
            elif report_type == 'applications':
                from applications.models import Application
                queryset = Application.objects.all()
                if date_limit:
                    queryset = queryset.filter(submitted_at__gte=date_limit)
                
                return list(queryset.values(
                    'id', 'status', 'first_name', 'last_name', 'submitted_at'
                ))
            
            # 3. Financial/System Report 
            elif report_type in ['financial', 'system', 'revenue']:
                from payments.models import Payment
                queryset = Payment.objects.all()
                if date_limit:
                    queryset = queryset.filter(created_at__gte=date_limit)
                    
                return list(queryset.values(
                    'id', 'amount', 'status', 'created_at'
                ))

        except Exception as e:
            # Return error as data so the generator can log it
            return [{"Error": f"Database Fetch Error: {str(e)}"}]

        return [{"Message": f"No data found for category: {report_type}"}]