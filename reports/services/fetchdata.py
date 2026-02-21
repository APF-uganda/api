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
                'email', 'first_name', 'last_name', 'is_active', 'date_joined'
            )
            data = list(queryset)
            return data if data else [{"Message": "No members found in system"}]
            
        # 2. System Report 
        elif report_type == 'system':
           
            queryset = User.objects.values('is_staff', 'is_superuser').annotate(total_users=Count('id'))
            data = list(queryset)
            return data if data else [{"Message": "No system data available"}]

        # 3. Fallback
        return [{"Message": f"No data found for category: {report_type}"}]