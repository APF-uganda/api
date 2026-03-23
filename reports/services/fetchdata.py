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
            # 1. MEMBERSHIP REPORT
            if report_type == 'membership':
                queryset = User.objects.all()
                
                if date_limit:
                    queryset = queryset.filter(created_at__gte=date_limit)
                
              
                data = list(queryset.values(
                    'email', 'first_name', 'last_name', 'role', 
                    'membership_category', 'is_active', 'created_at'
                ))
                
                for item in data:
                    # Formatting for the PDF Table and Charts
                    item['status'] = 'Active' if item.get('is_active') else 'Inactive'
                    
                    # Map role IDs to strings if they are numeric
                    role_map = {"1": "Associate", "2": "Full Member", "3": "Fellow"}
                    curr_role = str(item.get('role', ''))
                    item['role'] = role_map.get(curr_role, curr_role)

                    if item.get('created_at'):
                        item['joined_date'] = item['created_at'].strftime('%Y-%m-%d')
                return data
            
            # 2. APPLICATIONS REPORT
            elif report_type == 'applications':
                from applications.models import Application
                queryset = Application.objects.all()
                
                if date_limit:
                    queryset = queryset.filter(submitted_at__gte=date_limit)
                
                data = list(queryset.values(
                    'application_id', 'first_name', 'last_name', 
                    'organization', 'payment_status', 'status', 'submitted_at'
                ))
                
                for item in data:
                    # Clean up strings for PDF readability
                    item['status'] = str(item.get('status', 'Pending')).title()
                    item['payment'] = str(item.get('payment_status', 'Unpaid')).title()
                    
                    if item.get('submitted_at'):
                        item['date'] = item['submitted_at'].strftime('%Y-%m-%d')
                return data
            
            # 3. FINANCIAL  REPORT
            elif report_type in ['financial', 'system', 'revenue', 'payments']:
                from payments.models import Payment
                queryset = Payment.objects.all()
                
                if date_limit:
                    queryset = queryset.filter(created_at__gte=date_limit)
                    
                data = list(queryset.values(
                    'id', 'amount', 'payment_method', 'status', 'created_at'
                ))
                
                for item in data:
                    # Format Currency and Dates
                    amount = item.get('amount', 0)
                    item['amount_ugx'] = f"{amount:,}"
                    item['txn_status'] = str(item.get('status', '')).upper()
                    
                    if item.get('created_at'):
                        item['transaction_date'] = item['created_at'].strftime('%Y-%m-%d')
                return data

        except Exception as e:
            logger.error(f"Fetcher Error: {str(e)}")
            return [{"Error": f"Database Fetch Error: {str(e)}"}]

        return [{"Message": f"No data found for category: {report_type}"}]