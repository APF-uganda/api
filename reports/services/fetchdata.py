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
            p = str(period_label or '').lower()
            if '7' in p: return now - timedelta(days=7)
            if '30' in p: return now - timedelta(days=30)
            if '90' in p: return now - timedelta(days=90)
            if '12' in p: return now - timedelta(days=365)
            return None

        date_limit = get_date_limit(filters.get('period'))

        try:
            # MEMBERSHIP REPORT
            if report_type == 'membership':
                queryset = User.objects.all().order_by('created_at')
                if date_limit:
                    queryset = queryset.filter(created_at__gte=date_limit)
                
                data = list(queryset.values('email', 'first_name', 'last_name', 'created_at'))
                for item in data:
                    if item.get('created_at'):
                        item['joined_date'] = item['created_at'].strftime('%Y-%m-%d')
                return data
            
            # APPLICATIONS REPORT
            elif report_type == 'applications':
                from applications.models import Application
                queryset = Application.objects.all().order_by('-submitted_at')
                if date_limit:
                    queryset = queryset.filter(submitted_at__gte=date_limit)
                
                data = list(queryset.values(
                    'application_id', 'first_name', 'last_name', 
                    'organization', 'payment_status', 'status', 'submitted_at'
                ))
                for item in data:
                    item['status'] = str(item.get('status', 'Pending')).title()
                    item['payment'] = str(item.get('payment_status', 'Unpaid')).title()
                    if item.get('submitted_at'):
                        item['date'] = item['submitted_at'].strftime('%Y-%m-%d')
                return data
            
            # PAYMENTS  REPORT
            elif report_type in ['financial', 'system', 'revenue', 'payments']:
                from payments.models import Payment
               
                queryset = Payment.objects.select_related('user').all().order_by('-created_at')
                
                if date_limit:
                    queryset = queryset.filter(created_at__gte=date_limit)
                
               
                data = list(queryset.values(
                    'user__email', 'amount', 'status', 'created_at', 'description'
                ))
                
                for item in data:
                 
                    item['email'] = item.pop('user__email', 'N/A')
                    
                    # Formatting Amount
                    amount = item.get('amount', 0)
                    item['amount_ugx'] = f"{amount:,}"
                    
                    # Formatting Status
                    item['status'] = str(item.get('status', '')).upper()
                    
                    # Formatting Date
                    if item.get('created_at'):
                        item['date'] = item['created_at'].strftime('%Y-%m-%d')
                    
                   
                    if not item.get('description'):
                        item['description'] = 'Membership Fee'
                        
                return data

        except Exception as e:
            logger.error(f"Fetcher Error: {str(e)}")
            return [{"Error": f"Database Fetch Error: {str(e)}"}]

        return [{"Message": f"No data found for category: {report_type}"}]