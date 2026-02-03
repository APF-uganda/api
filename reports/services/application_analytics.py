"""
Application Analytics Service
Single Responsibility: Handles all application-related analytics
"""

from typing import Dict, List, Any
from datetime import datetime
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.utils import timezone

from .base import BaseAnalyticsService, BaseMetricsCalculator
from applications.models import Application


class ApplicationMetricsCalculator(BaseMetricsCalculator):
    """
    Calculates application-specific metrics
    Single Responsibility: Application metric calculations
    """
    
    def calculate(self, queryset=None, period_start: datetime = None, period_end: datetime = None) -> Dict[str, Any]:
        """Calculate application metrics"""
        # Total applications
        total_applications = Application.objects.count()
        
        # Applications by status
        status_breakdown = {
            'pending': Application.objects.filter(status='pending').count(),
            'approved': Application.objects.filter(status='approved').count(),
            'rejected': Application.objects.filter(status='rejected').count(),
        }
        
        # Applications in period
        applications_period = 0
        if period_start and period_end:
            applications_period = Application.objects.filter(
                submitted_at__gte=period_start,
                submitted_at__lte=period_end
            ).count()
        
        # Processing metrics
        avg_processing_time = self._calculate_avg_processing_time()
        approval_rate = self._calculate_approval_rate()
        
        return {
            'total_applications': total_applications,
            'status_breakdown': status_breakdown,
            'applications_period': applications_period,
            'avg_processing_time_days': avg_processing_time,
            'approval_rate': approval_rate,
            'rejection_rate': 100 - approval_rate if approval_rate else 0
        }
    
    def get_metric_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get definitions of application metrics"""
        return {
            'total_applications': {
                'name': 'Total Applications',
                'description': 'Total number of membership applications',
                'type': 'count',
                'category': 'applications'
            },
            'pending_applications': {
                'name': 'Pending Applications',
                'description': 'Number of applications awaiting review',
                'type': 'count',
                'category': 'applications'
            },
            'approved_applications': {
                'name': 'Approved Applications',
                'description': 'Number of approved applications',
                'type': 'count',
                'category': 'applications'
            },
            'approval_rate': {
                'name': 'Approval Rate',
                'description': 'Percentage of applications that are approved',
                'type': 'percentage',
                'category': 'applications'
            },
            'avg_processing_time': {
                'name': 'Average Processing Time',
                'description': 'Average time to process an application',
                'type': 'duration',
                'category': 'applications'
            }
        }
    
    def _calculate_avg_processing_time(self) -> float:
        """Calculate average processing time in days"""
        processed_applications = Application.objects.filter(
            status__in=['approved', 'rejected'],
            updated_at__isnull=False
        )
        
        if not processed_applications.exists():
            return 0.0
        
        total_days = 0
        count = 0
        
        for app in processed_applications:
            if app.submitted_at and app.updated_at:
                processing_time = app.updated_at - app.submitted_at
                total_days += processing_time.days
                count += 1
        
        return round(total_days / count, 2) if count > 0 else 0.0
    
    def _calculate_approval_rate(self) -> float:
        """Calculate approval rate percentage"""
        total_processed = Application.objects.filter(
            status__in=['approved', 'rejected']
        ).count()
        
        if total_processed == 0:
            return 0.0
        
        approved_count = Application.objects.filter(status='approved').count()
        return round((approved_count / total_processed) * 100, 2)


class ApplicationAnalyticsService(BaseAnalyticsService):
    """
    Service for application analytics
    Open/Closed Principle: Can be extended without modification
    """
    
    def __init__(self):
        super().__init__()
        self.metrics_calculator = ApplicationMetricsCalculator()
    
    def get_metrics(self, period_start: datetime, period_end: datetime, **kwargs) -> Dict[str, Any]:
        """Get application metrics for the specified period"""
        return self.metrics_calculator.calculate(
            period_start=period_start,
            period_end=period_end
        )
    
    def get_chart_data(self, chart_type: str, period: str = '30d', **kwargs) -> Dict[str, Any]:
        """Get chart data for application visualizations"""
        period_start, period_end = self.get_period_dates(period)
        
        if chart_type == 'application_status':
            return self._get_application_status_chart()
        elif chart_type == 'application_trends':
            return self._get_application_trends_chart(period_start, period_end, period)
        elif chart_type == 'processing_time':
            return self._get_processing_time_chart()
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")
    
    def _get_application_status_chart(self) -> Dict[str, Any]:
        """Get application status distribution chart data"""
        status_data = Application.objects.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        labels = [item['status'].title() for item in status_data]
        data = [item['count'] for item in status_data]
        
        return self.format_chart_data(
            labels=labels,
            data=data,
            title='Application Status Distribution'
        )
    
    def _get_application_trends_chart(self, period_start: datetime, period_end: datetime, period: str) -> Dict[str, Any]:
        """Get application submission trends chart data"""
        if period in ['7d', '30d']:
            trunc_func = TruncDay
            date_format = '%Y-%m-%d'
        else:
            trunc_func = TruncMonth
            date_format = '%Y-%m'
        
        trends_data = Application.objects.filter(
            submitted_at__gte=period_start,
            submitted_at__lte=period_end
        ).annotate(
            period=trunc_func('submitted_at')
        ).values('period').annotate(
            count=Count('id')
        ).order_by('period')
        
        labels = [item['period'].strftime(date_format) for item in trends_data]
        data = [item['count'] for item in trends_data]
        
        return self.format_chart_data(
            labels=labels,
            data=data,
            title=f'Application Submission Trends ({period})'
        )
    
    def _get_processing_time_chart(self) -> Dict[str, Any]:
        """Get processing time distribution chart data"""
        # Group applications by processing time ranges
        processed_apps = Application.objects.filter(
            status__in=['approved', 'rejected'],
            updated_at__isnull=False
        )
        
        time_ranges = {
            '0-1 days': 0,
            '2-7 days': 0,
            '8-14 days': 0,
            '15-30 days': 0,
            '30+ days': 0
        }
        
        for app in processed_apps:
            if app.submitted_at and app.updated_at:
                processing_time = (app.updated_at - app.submitted_at).days
                
                if processing_time <= 1:
                    time_ranges['0-1 days'] += 1
                elif processing_time <= 7:
                    time_ranges['2-7 days'] += 1
                elif processing_time <= 14:
                    time_ranges['8-14 days'] += 1
                elif processing_time <= 30:
                    time_ranges['15-30 days'] += 1
                else:
                    time_ranges['30+ days'] += 1
        
        return self.format_chart_data(
            labels=list(time_ranges.keys()),
            data=list(time_ranges.values()),
            title='Application Processing Time Distribution'
        )
    
    def get_application_pipeline(self) -> Dict[str, Any]:
        """Get application pipeline analysis"""
        # Applications by status with additional metrics
        pipeline_data = {}
        
        for status in ['pending', 'approved', 'rejected']:
            applications = Application.objects.filter(status=status)
            count = applications.count()
            
            # Calculate average time in this status
            avg_time_in_status = 0
            if applications.exists():
                total_time = 0
                valid_count = 0
                
                for app in applications:
                    if app.submitted_at:
                        if status == 'pending':
                            time_diff = timezone.now() - app.submitted_at
                        else:
                            time_diff = app.updated_at - app.submitted_at if app.updated_at else timezone.timedelta(0)
                        
                        total_time += time_diff.days
                        valid_count += 1
                
                avg_time_in_status = round(total_time / valid_count, 2) if valid_count > 0 else 0
            
            pipeline_data[status] = {
                'count': count,
                'avg_time_days': avg_time_in_status
            }
        
        return {
            'pipeline': pipeline_data,
            'total_applications': sum(data['count'] for data in pipeline_data.values()),
            'generated_at': timezone.now().isoformat()
        }
    
    def get_recent_applications(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent applications with basic info"""
        recent_apps = Application.objects.order_by('-submitted_at')[:limit]
        
        return [
            {
                'id': app.id,
                'first_name': app.first_name,
                'last_name': app.last_name,
                'email': app.email,
                'status': app.status,
                'submitted_at': app.submitted_at.isoformat() if app.submitted_at else None,
                'updated_at': app.updated_at.isoformat() if app.updated_at else None
            }
            for app in recent_apps
        ]