"""
Analytics Coordinator - Facade Pattern
Single Responsibility: Coordinates all analytics services
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from django.utils import timezone

from .base import CacheManager
from .membership_analytics import MembershipAnalyticsService
from .application_analytics import ApplicationAnalyticsService
from .system_analytics import SystemAnalyticsService


class AnalyticsCoordinator:
    """
    Coordinates all analytics services using Facade pattern
    Single Responsibility: Provides unified interface to all analytics
    """
    
    def __init__(self):
        # Initialize services
        self.membership_service = MembershipAnalyticsService()
        self.application_service = ApplicationAnalyticsService()
        self.system_service = SystemAnalyticsService()
        
        # Initialize cache manager
        self.cache_manager = CacheManager(default_timeout=300)  # 5 minutes
    
    def get_comprehensive_analytics(self, period: str = '30d', use_cache: bool = True) -> Dict[str, Any]:
        """
        Get comprehensive analytics from all services
        Facade Pattern: Simplifies complex subsystem interactions
        """
        cache_key = f"comprehensive_analytics:{period}"
        
        if use_cache:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                return cached_data
        
        # Get period dates
        period_start, period_end = self._get_period_dates(period)
        
        # Collect data from all services
        analytics_data = {
            'membership': self.membership_service.get_metrics(period_start, period_end),
            'applications': self.application_service.get_metrics(period_start, period_end),
            'system': self.system_service.get_metrics(period_start, period_end),
            'period': {
                'start': period_start.isoformat(),
                'end': period_end.isoformat(),
                'period_string': period
            },
            'generated_at': timezone.now().isoformat()
        }
        
        # Cache the result
        if use_cache:
            self.cache_manager.set(cache_key, analytics_data)
        
        return analytics_data
    
    def get_chart_data(self, chart_type: str, period: str = '30d', category: Optional[str] = None) -> Dict[str, Any]:
        """
        Get chart data from appropriate service
        Strategy Pattern: Delegates to appropriate service based on chart type
        """
        cache_key = f"chart_data:{chart_type}:{period}:{category or 'all'}"
        
        cached_data = self.cache_manager.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # Determine which service to use based on chart type or category
            if category == 'membership' or chart_type in ['membership_growth', 'member_distribution', 'profile_completion']:
                chart_data = self.membership_service.get_chart_data(chart_type, period)
            elif category == 'applications' or chart_type in ['application_status', 'application_trends', 'processing_time']:
                chart_data = self.application_service.get_chart_data(chart_type, period)
            elif category == 'system' or chart_type in ['daily_activity', 'user_growth', 'login_frequency', 'system_health']:
                chart_data = self.system_service.get_chart_data(chart_type, period)
            else:
                # Try to infer from chart type name
                if 'member' in chart_type.lower():
                    chart_data = self.membership_service.get_chart_data(chart_type, period)
                elif 'application' in chart_type.lower():
                    chart_data = self.application_service.get_chart_data(chart_type, period)
                else:
                    chart_data = self.system_service.get_chart_data(chart_type, period)
            
            # Cache the result
            self.cache_manager.set(cache_key, chart_data)
            return chart_data
            
        except ValueError as e:
            return {
                'error': str(e),
                'chart_type': chart_type,
                'period': period,
                'category': category
            }
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Get summary data for admin dashboard
        Template Method Pattern: Defines algorithm structure
        """
        cache_key = "dashboard_summary"
        
        cached_data = self.cache_manager.get(cache_key)
        if cached_data:
            return cached_data
        
        # Get 30-day period
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        now = timezone.now()
        
        # Collect key metrics from each service
        summary_data = {
            'key_metrics': {
                'total_members': self.membership_service.get_metrics(thirty_days_ago, now)['total_members'],
                'total_applications': self.application_service.get_metrics(thirty_days_ago, now)['total_applications'],
                'pending_applications': self.application_service.get_metrics(thirty_days_ago, now)['status_breakdown']['pending'],
                'active_users_30d': self.system_service.get_metrics(thirty_days_ago, now)['active_users_period'],
                'system_health_score': self.system_service.get_metrics(thirty_days_ago, now)['system_health_score']
            },
            'recent_activity': {
                'new_members_30d': self.membership_service.get_metrics(thirty_days_ago, now)['new_members_period'],
                'new_applications_30d': self.application_service.get_metrics(thirty_days_ago, now)['applications_period'],
                'profile_updates_30d': self.system_service.get_metrics(thirty_days_ago, now)['recent_profile_updates']
            },
            'trends': {
                'membership_growth': self.membership_service.get_chart_data('membership_growth', '30d'),
                'application_status': self.application_service.get_chart_data('application_status'),
                'daily_activity': self.system_service.get_chart_data('daily_activity', '7d')
            },
            'generated_at': now.isoformat()
        }
        
        # Cache for 5 minutes
        self.cache_manager.set(cache_key, summary_data, timeout=300)
        
        return summary_data
    
    def get_service_metrics(self, service_name: str, period: str = '30d') -> Dict[str, Any]:
        """
        Get metrics from a specific service
        Factory Method Pattern: Creates appropriate service instance
        """
        period_start, period_end = self._get_period_dates(period)
        
        if service_name == 'membership':
            return self.membership_service.get_metrics(period_start, period_end)
        elif service_name == 'applications':
            return self.application_service.get_metrics(period_start, period_end)
        elif service_name == 'system':
            return self.system_service.get_metrics(period_start, period_end)
        else:
            raise ValueError(f"Unknown service: {service_name}")
    
    def get_available_charts(self) -> Dict[str, List[str]]:
        """Get list of available chart types by category"""
        return {
            'membership': [
                'membership_growth',
                'member_distribution',
                'profile_completion'
            ],
            'applications': [
                'application_status',
                'application_trends',
                'processing_time'
            ],
            'system': [
                'daily_activity',
                'user_growth',
                'login_frequency',
                'system_health'
            ]
        }
    
    def clear_cache(self, pattern: Optional[str] = None) -> None:
        """Clear analytics cache"""
        if pattern:
            # In a real implementation, you'd clear keys matching the pattern
            # For now, clear all cache
            self.cache_manager.clear()
        else:
            self.cache_manager.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        # In a real implementation, you'd return actual cache stats
        return {
            'cache_size': len(self.cache_manager._cache),
            'cache_timeout': self.cache_manager.default_timeout,
            'cache_type': 'in_memory'
        }
    
    def _get_period_dates(self, period: str) -> tuple[datetime, datetime]:
        """Convert period string to start and end dates"""
        now = timezone.now()
        
        if period == '7d':
            start_date = now - timezone.timedelta(days=7)
        elif period == '30d':
            start_date = now - timezone.timedelta(days=30)
        elif period == '90d':
            start_date = now - timezone.timedelta(days=90)
        elif period == '12m':
            start_date = now - timezone.timedelta(days=365)
        else:
            start_date = now - timezone.timedelta(days=30)  # Default to 30 days
        
        return start_date, now
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of all analytics services"""
        health_status = {
            'overall_status': 'healthy',
            'services': {},
            'cache_status': 'healthy',
            'checked_at': timezone.now().isoformat()
        }
        
        # Check each service
        services = {
            'membership': self.membership_service,
            'applications': self.application_service,
            'system': self.system_service
        }
        
        for service_name, service in services.items():
            try:
                # Try to get basic metrics
                thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
                service.get_metrics(thirty_days_ago, timezone.now())
                health_status['services'][service_name] = 'healthy'
            except Exception as e:
                health_status['services'][service_name] = f'error: {str(e)}'
                health_status['overall_status'] = 'degraded'
        
        return health_status


# Global instance for use across the application
analytics_coordinator = AnalyticsCoordinator()