from django.contrib.auth import get_user_model
from django.db.models import Count

User = get_user_model()

class ReportDataFetcher:
    """Logic to query the database based on template settings"""
    
    @staticmethod
    def get_data(template, filters_applied=None):
        report_type = template.report_type.lower()
        
        # 1. Membership Report
        if report_type == 'membership':
            queryset = User.objects.all().values(
                'email', 'first_name', 'last_name', 'phone_number', 
                'membership_category', 'practising_status', 'is_active', 'created_at'
            )
            data = list(queryset)
            return data if data else [{"Message": "No members found in system"}]
        
        # 2. Applications Report
        elif report_type == 'applications':
            from applications.models import Application
            queryset = Application.objects.all().values(
                'id', 'user__email', 'user__first_name', 'user__last_name',
                'status', 'application_type', 'created_at', 'updated_at'
            )
            data = list(queryset)
            return data if data else [{"Message": "No applications found"}]
        
        # 3. Financial Report
        elif report_type == 'financial':
            from payments.models import Payment
            queryset = Payment.objects.all().values(
                'id', 'user__email', 'amount', 'currency', 'status',
                'payment_method', 'transaction_id', 'created_at'
            )
            data = list(queryset)
            return data if data else [{"Message": "No payment records found"}]
            
        # 4. System Report 
        elif report_type == 'system':
            queryset = User.objects.values('is_staff', 'is_superuser', 'role').annotate(total_users=Count('id'))
            data = list(queryset)
            return data if data else [{"Message": "No system data available"}]

        # 5. Growth Analysis Report
        elif report_type == 'growth':
            from django.db.models.functions import TruncDate
            queryset = User.objects.annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(
                new_members=Count('id')
            ).order_by('date')
            data = list(queryset)
            return data if data else [{"Message": "No growth data available"}]

        # 6. Fallback
        return [{"Message": f"No data found for category: {report_type}"}]