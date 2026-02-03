"""
System Analytics Service
Single Responsibility: Handles system-wide analytics and performance metrics
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta
from django.db.models import Count, Q
from django.db.models.functions import TruncDay, TruncHour
from django.utils import timezone
from django.contrib.auth import get_user_model

from .base import BaseAnalyticsService, BaseMetricsCalculator
from profiles.models import UserProfile

User = get_user_model()


class SystemMetricsCalculator(BaseMetricsCalculator):
    """
    Calculates system-wide metrics
    Single Responsibility: System metric calculations
    """
    
    def calculate(self, queryset=None, period_start: datetime = None, period_end: datetime = None) -> Dict[str, Any]:
        """Calculate system metrics"""
        # User activity metrics
        total_users = User.objects.count()
        
        # Active users in period
        active_users = 0
        if period_start and period_end:
            active_users = User.objects.filter(
                last_login__gte=period_start,
                last_login__lte=period_end
            ).count()
        
        # Profile metrics
        users_with_profiles = User.objects.filter(
            userprofile__isnull=False
        ).count()
        
        recent_profile_updates = 0
        if period_start and period_end:
            recent_profile_updates = UserProfile.objects.filter(
                updated_at__gte=period_start,
                updated_at__lte=period_end
            ).count()
        
        # System health metrics
        profile_adoption_rate = round((users_with_profiles / max(total_users, 1)) * 100, 2)
        
        # Login frequency analysis
        login_frequency = self._calculate_login_frequency(period_start, period_end)
        
        return {
            'total_users': total_users,
            'active_users_period': active_users,
            'users_with_profiles': users_with_profiles,
            'recent_profile_updates': recent_profile_updates,
            'profile_adoption_rate': profile_adoption_rate,
            'login_frequency': login_frequency,
            'system_health_score': self._calculate_health_score(
                total_users, active_users, users_with_profiles
            )
        }
    
    def get_metric_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get definitions of system metrics"""
        return {
            'total_users': {
                'name': 'Total Users',
                'description': 'Total number of registered users',
                'type': 'count',
                'category': 'system'
            },
            'active_users_period': {
                'name': 'Active Users (Period)',
                'description': 'Number of users active in the specified period',
                'type': 'count',
                'category': 'system'
            },
            'profile_adoption_rate': {
                'name': 'Profile Adoption Rate',
                'description': 'Percentage of users with profiles',
                'type': 'percentage',
                'category': 'system'
            },
            'system_health_score': {
                'name': 'System Health Score',
                'description': 'Overall system health based on user engagement',
                'type': 'score',
                'category': 'system'
            }
        }
    
    def _calculate_login_frequency(self, period_start: datetime, period_end: datetime) -> Dict[str, int]:
        """Calculate login frequency distribution"""
        if not period_start or not period_end:
            return {'daily': 0, 'weekly': 0, 'monthly': 0, 'inactive': 0}
        
        now = timezone.now()
        one_day_ago = now - timedelta(days=1)
        one_week_ago = now - timedelta(days=7)
        one_month_ago = now - timedelta(days=30)
        
        return {
            'daily': User.objects.filter(last_login__gte=one_day_ago).count(),
            'weekly': User.objects.filter(
                last_login__gte=one_week_ago,
                last_login__lt=one_day_ago
            ).count(),
            'monthly': User.objects.filter(
                last_login__gte=one_month_ago,
                last_login__lt=one_week_ago
            ).count(),
            'inactive': User.objects.filter(
                Q(last_login__lt=one_month_ago) | Q(last_login__isnull=True)
            ).count()
        }
    
    def _calculate_health_score(self, total_users: int, active_users: int, users_with_profiles: int) -> float:
        """Calculate system health score (0-100)"""
        if total_users == 0:
            return 0.0
        
        # Weight different factors
        activity_score = (active_users / total_users) * 40  # 40% weight
        profile_score = (users_with_profiles / total_users) * 30  # 30% weight
        engagement_score = min(total_users / 100, 1) * 30  # 30% weight (up to 100 users)
        
        total_score = activity_score + profile_score + engagement_score
        return round(min(total_score, 100), 2)


class SystemAnalyticsService(BaseAnalyticsService):
    """
    Service for system analytics
    Open/Closed Principle: Can be extended without modification
    """
    
    def __init__(self):
        super().__init__()
        self.metrics_calculator = SystemMetricsCalculator()
    
    def get_metrics(self, period_start: datetime, period_end: datetime, **kwargs) -> Dict[str, Any]:
        """Get system metrics for the specified period"""
        return self.metrics_calculator.calculate(
            period_start=period_start,
            period_end=period_end
        )
    
    def get_chart_data(self, chart_type: str, period: str = '30d', **kwargs) -> Dict[str, Any]:
        """Get chart data for system visualizations"""
        period_start, period_end = self.get_period_dates(period)
        
        if chart_type == 'daily_activity':
            return self._get_daily_activity_chart(period_start, period_end)
        elif chart_type == 'user_growth':
            return self._get_user_growth_chart(period_start, period_end, period)
        elif chart_type == 'login_frequency':
            return self._get_login_frequency_chart()
        elif chart_type == 'system_health':
            return self._get_system_health_chart(period_start, period_end)
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")
    
    def _get_daily_activity_chart(self, period_start: datetime, period_end: datetime) -> Dict[str, Any]:
        """Get daily user activity chart data"""
        activity_data = User.objects.filter(
            last_login__gte=period_start,
            last_login__lte=period_end
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
            title='Daily User Activity'
        )
    
    def _get_user_growth_chart(self, period_start: datetime, period_end: datetime, period: str) -> Dict[str, Any]:
        """Get user growth chart data"""
        if period in ['7d', '30d']:
            trunc_func = TruncDay
            date_format = '%Y-%m-%d'
        else:
            trunc_func = TruncDay  # Still use daily for longer periods
            date_format = '%Y-%m-%d'
        
        growth_data = User.objects.filter(
            created_at__gte=period_start,
            created_at__lte=period_end
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
            title=f'User Registration Growth ({period})'
        )
    
    def _get_login_frequency_chart(self) -> Dict[str, Any]:
        """Get login frequency distribution chart data"""
        now = timezone.now()
        metrics = self.metrics_calculator._calculate_login_frequency(
            now - timedelta(days=30), now
        )
        
        return self.format_chart_data(
            labels=list(metrics.keys()),
            data=list(metrics.values()),
            title='User Login Frequency Distribution'
        )
    
    def _get_system_health_chart(self, period_start: datetime, period_end: datetime) -> Dict[str, Any]:
        """Get system health metrics chart data"""
        metrics = self.get_metrics(period_start, period_end)
        
        health_metrics = {
            'Active Users': metrics['active_users_period'],
            'Profile Adoption': metrics['profile_adoption_rate'],
            'Health Score': metrics['system_health_score']
        }
        
        return self.format_chart_data(
            labels=list(health_metrics.keys()),
            data=list(health_metrics.values()),
            title='System Health Metrics'
        )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        now = timezone.now()
        
        # Response time simulation (in real app, this would come from monitoring)
        performance_data = {
            'avg_response_time_ms': 250,  # Simulated
            'uptime_percentage': 99.9,   # Simulated
            'error_rate_percentage': 0.1, # Simulated
            'concurrent_users': self._get_concurrent_users(),
            'peak_usage_hour': self._get_peak_usage_hour(),
            'database_queries_per_minute': 150,  # Simulated
            'memory_usage_percentage': 65,       # Simulated
            'cpu_usage_percentage': 45           # Simulated
        }
        
        return {
            'performance': performance_data,
            'generated_at': now.isoformat()
        }
    
    def _get_concurrent_users(self) -> int:
        """Estimate concurrent users (users active in last hour)"""
        one_hour_ago = timezone.now() - timedelta(hours=1)
        return User.objects.filter(last_login__gte=one_hour_ago).count()
    
    def _get_peak_usage_hour(self) -> int:
        """Get peak usage hour of the day"""
        # Analyze login patterns over the last 7 days
        seven_days_ago = timezone.now() - timedelta(days=7)
        
        hourly_logins = User.objects.filter(
            last_login__gte=seven_days_ago
        ).annotate(
            hour=TruncHour('last_login')
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('-count')
        
        if hourly_logins:
            peak_hour = hourly_logins[0]['hour']
            return peak_hour.hour
        
        return 12  # Default to noon
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get comprehensive system summary"""
        thirty_days_ago = timezone.now() - timedelta(days=30)
        now = timezone.now()
        
        metrics = self.get_metrics(thirty_days_ago, now)
        performance = self.get_performance_metrics()
        
        return {
            'metrics': metrics,
            'performance': performance['performance'],
            'summary_generated_at': now.isoformat()
        }