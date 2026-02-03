"""
Membership Analytics Service
Single Responsibility: Handles all membership-related analytics
"""

from typing import Dict, List, Any
from datetime import datetime
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.utils import timezone

from .base import BaseAnalyticsService, BaseMetricsCalculator
from authentication.models import User
from profiles.models import UserProfile


class MembershipMetricsCalculator(BaseMetricsCalculator):
    """
    Calculates membership-specific metrics
    Single Responsibility: Membership metric calculations
    """
    
    def calculate(self, queryset=None, period_start: datetime = None, period_end: datetime = None) -> Dict[str, Any]:
        """Calculate membership metrics"""
        # Total counts
        total_members = User.objects.filter(role='0').count()
        total_admins = User.objects.filter(role='1').count()
        
        # New members in period
        new_members_period = 0
        if period_start and period_end:
            new_members_period = User.objects.filter(
                role='0',
                created_at__gte=period_start,
                created_at__lte=period_end
            ).count()
        
        # Profile completion metrics
        profiles_with_picture = UserProfile.objects.filter(
            profile_picture__isnull=False
        ).count()
        total_profiles = UserProfile.objects.count()
        
        # Active members (logged in within period)
        active_members = 0
        if period_start and period_end:
            active_members = User.objects.filter(
                role='0',
                last_login__gte=period_start,
                last_login__lte=period_end
            ).count()
        
        return {
            'total_members': total_members,
            'total_admins': total_admins,
            'new_members_period': new_members_period,
            'active_members_period': active_members,
            'profile_completion': {
                'with_picture': profiles_with_picture,
                'total_profiles': total_profiles,
                'completion_rate': round((profiles_with_picture / max(total_profiles, 1)) * 100, 2)
            },
            'growth_rate': self._calculate_growth_rate(period_start, period_end) if period_start and period_end else 0
        }
    
    def get_metric_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get definitions of membership metrics"""
        return {
            'total_members': {
                'name': 'Total Members',
                'description': 'Total number of registered members',
                'type': 'count',
                'category': 'membership'
            },
            'total_admins': {
                'name': 'Total Administrators',
                'description': 'Total number of admin users',
                'type': 'count',
                'category': 'membership'
            },
            'new_members_period': {
                'name': 'New Members (Period)',
                'description': 'Number of new members in the specified period',
                'type': 'count',
                'category': 'membership'
            },
            'active_members_period': {
                'name': 'Active Members (Period)',
                'description': 'Number of members active in the specified period',
                'type': 'count',
                'category': 'membership'
            },
            'profile_completion_rate': {
                'name': 'Profile Completion Rate',
                'description': 'Percentage of members with complete profiles',
                'type': 'percentage',
                'category': 'membership'
            }
        }
    
    def _calculate_growth_rate(self, period_start: datetime, period_end: datetime) -> float:
        """Calculate membership growth rate"""
        # Get members at start of period
        members_start = User.objects.filter(
            role='0',
            created_at__lt=period_start
        ).count()
        
        # Get members at end of period
        members_end = User.objects.filter(
            role='0',
            created_at__lte=period_end
        ).count()
        
        if members_start == 0:
            return 100.0 if members_end > 0 else 0.0
        
        growth_rate = ((members_end - members_start) / members_start) * 100
        return round(growth_rate, 2)


class MembershipAnalyticsService(BaseAnalyticsService):
    """
    Service for membership analytics
    Open/Closed Principle: Can be extended without modification
    """
    
    def __init__(self):
        super().__init__()
        self.metrics_calculator = MembershipMetricsCalculator()
    
    def get_metrics(self, period_start: datetime, period_end: datetime, **kwargs) -> Dict[str, Any]:
        """Get membership metrics for the specified period"""
        return self.metrics_calculator.calculate(
            period_start=period_start,
            period_end=period_end
        )
    
    def get_chart_data(self, chart_type: str, period: str = '30d', **kwargs) -> Dict[str, Any]:
        """Get chart data for membership visualizations"""
        period_start, period_end = self.get_period_dates(period)
        
        if chart_type == 'membership_growth':
            return self._get_membership_growth_chart(period_start, period_end, period)
        elif chart_type == 'member_distribution':
            return self._get_member_distribution_chart()
        elif chart_type == 'profile_completion':
            return self._get_profile_completion_chart()
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")
    
    def _get_membership_growth_chart(self, period_start: datetime, period_end: datetime, period: str) -> Dict[str, Any]:
        """Get membership growth chart data"""
        if period in ['7d', '30d']:
            trunc_func = TruncDay
            date_format = '%Y-%m-%d'
        else:
            trunc_func = TruncMonth
            date_format = '%Y-%m'
        
        growth_data = User.objects.filter(
            created_at__gte=period_start,
            created_at__lte=period_end,
            role='0'
        ).annotate(
            period=trunc_func('created_at')
        ).values('period').annotate(
            count=Count('id')
        ).order_by('period')
        
        labels = [item['period'].strftime(date_format) for item in growth_data]
        data = [item['count'] for item in growth_data]
        
        return self.format_chart_data(
            labels=labels,
            data=data,
            title=f'Membership Growth ({period})'
        )
    
    def _get_member_distribution_chart(self) -> Dict[str, Any]:
        """Get member distribution by role chart data"""
        distribution_data = User.objects.values('role').annotate(
            count=Count('id')
        ).order_by('role')
        
        labels = []
        data = []
        
        for item in distribution_data:
            role_label = 'Administrator' if item['role'] == '1' else 'Member'
            labels.append(role_label)
            data.append(item['count'])
        
        return self.format_chart_data(
            labels=labels,
            data=data,
            title='Member Distribution by Role'
        )
    
    def _get_profile_completion_chart(self) -> Dict[str, Any]:
        """Get profile completion status chart data"""
        total_profiles = UserProfile.objects.count()
        completed_profiles = UserProfile.objects.filter(
            profile_picture__isnull=False,
            phone_number__isnull=False,
            bio__isnull=False
        ).exclude(
            phone_number='',
            bio=''
        ).count()
        
        incomplete_profiles = total_profiles - completed_profiles
        
        return self.format_chart_data(
            labels=['Completed', 'Incomplete'],
            data=[completed_profiles, incomplete_profiles],
            title='Profile Completion Status'
        )
    
    def get_member_activity_trends(self, period: str = '30d') -> Dict[str, Any]:
        """Get member activity trends"""
        period_start, period_end = self.get_period_dates(period)
        
        # Daily login activity
        activity_data = User.objects.filter(
            last_login__gte=period_start,
            last_login__lte=period_end,
            role='0'
        ).annotate(
            day=TruncDay('last_login')
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')
        
        labels = [item['day'].strftime('%Y-%m-%d') for item in activity_data]
        data = [item['count'] for item in activity_data]
        
        return self.format_chart_data(
            labels=labels,
            data=data,
            title=f'Member Activity Trends ({period})'
        )
    
    def get_membership_summary(self) -> Dict[str, Any]:
        """Get comprehensive membership summary"""
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        
        metrics = self.get_metrics(thirty_days_ago, timezone.now())
        
        # Additional summary data
        recent_members = User.objects.filter(
            role='0',
            created_at__gte=thirty_days_ago
        ).order_by('-created_at')[:5]
        
        return {
            'metrics': metrics,
            'recent_members': [
                {
                    'id': member.id,
                    'email': member.email,
                    'created_at': member.created_at.isoformat(),
                    'full_name': getattr(member.userprofile, 'full_name', '') if hasattr(member, 'userprofile') else ''
                }
                for member in recent_members
            ],
            'summary_generated_at': timezone.now().isoformat()
        }