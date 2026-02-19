from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils import timezone

User = get_user_model()

class ReportDataFetcher:
    """Logic to query the database based on template settings"""
    
    @staticmethod
    def get_data(template, filters_applied=None):
        report_type = template.report_type
        
        
        if report_type == 'membership':
            return User.objects.all().values(
                'email', 'first_name', 'last_name', 'is_active', 'date_joined'
            )
            
        elif report_type == 'system':
            return User.objects.values('role').annotate(total_users=Count('id'))

     
        return [{"message": "No data found for this category"}]