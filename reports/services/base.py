"""
Base classes for analytics services
Following SOLID principles with proper abstraction
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import QuerySet


class BaseAnalyticsService(ABC):
    """
    Abstract base class for analytics services
    Open/Closed Principle: Open for extension, closed for modification
    """
    
    def __init__(self):
        self.cache_timeout = 300  # 5 minutes default cache
    
    @abstractmethod
    def get_metrics(self, period_start: datetime, period_end: datetime, **kwargs) -> Dict[str, Any]:
        """Get analytics metrics for the specified period"""
        pass
    
    @abstractmethod
    def get_chart_data(self, chart_type: str, period: str = '30d', **kwargs) -> Dict[str, Any]:
        """Get chart data for visualizations"""
        pass
    
    def get_period_dates(self, period: str) -> tuple[datetime, datetime]:
        """
        Convert period string to start and end dates
        Dependency Inversion: Depends on abstraction, not concrete implementation
        """
        now = timezone.now()
        
        if period == '7d':
            start_date = now - timedelta(days=7)
        elif period == '30d':
            start_date = now - timedelta(days=30)
        elif period == '90d':
            start_date = now - timedelta(days=90)
        elif period == '12m':
            start_date = now - timedelta(days=365)
        else:
            start_date = now - timedelta(days=30)  # Default to 30 days
        
        return start_date, now
    
    def format_chart_data(self, labels: List[str], data: List[Union[int, float]], title: str) -> Dict[str, Any]:
        """Format data for chart consumption"""
        return {
            'labels': labels,
            'data': data,
            'title': title,
            'generated_at': timezone.now().isoformat()
        }


class BaseReportGenerator(ABC):
    """
    Abstract base class for report generators
    Single Responsibility: Each generator handles one type of report
    """
    
    def __init__(self):
        self.supported_formats = ['pdf', 'excel', 'csv', 'json']
    
    @abstractmethod
    def generate(self, template_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate report based on template and parameters"""
        pass
    
    @abstractmethod
    def get_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get data for report generation"""
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate report generation parameters"""
        required_fields = self.get_required_parameters()
        return all(field in parameters for field in required_fields)
    
    @abstractmethod
    def get_required_parameters(self) -> List[str]:
        """Get list of required parameters for this report type"""
        pass


class BaseMetricsCalculator(ABC):
    """
    Abstract base class for metrics calculators
    Interface Segregation: Specific interfaces for different metric types
    """
    
    @abstractmethod
    def calculate(self, queryset: QuerySet, period_start: datetime, period_end: datetime) -> Dict[str, Any]:
        """Calculate metrics from queryset"""
        pass
    
    @abstractmethod
    def get_metric_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get definitions of metrics this calculator provides"""
        pass


class CacheManager:
    """
    Manages caching for analytics data
    Single Responsibility: Handles all caching operations
    """
    
    def __init__(self, default_timeout: int = 300):
        self.default_timeout = default_timeout
        self._cache = {}  # In-memory cache for development
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        if key in self._cache:
            value, expiry = self._cache[key]
            if timezone.now() < expiry:
                return value
            else:
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """Set cached value"""
        timeout = timeout or self.default_timeout
        expiry = timezone.now() + timedelta(seconds=timeout)
        self._cache[key] = (value, expiry)
    
    def delete(self, key: str) -> None:
        """Delete cached value"""
        if key in self._cache:
            del self._cache[key]
    
    def clear(self) -> None:
        """Clear all cached values"""
        self._cache.clear()
    
    def generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
        return ":".join(key_parts)


class DataAggregator:
    """
    Aggregates data from multiple sources
    Single Responsibility: Data aggregation logic
    """
    
    def __init__(self):
        self.aggregation_functions = {
            'sum': lambda x: sum(x),
            'avg': lambda x: sum(x) / len(x) if x else 0,
            'count': lambda x: len(x),
            'max': lambda x: max(x) if x else 0,
            'min': lambda x: min(x) if x else 0,
        }
    
    def aggregate(self, data: List[Dict[str, Any]], group_by: str, aggregate_field: str, 
                 function: str = 'sum') -> Dict[str, Any]:
        """Aggregate data by specified field"""
        if function not in self.aggregation_functions:
            raise ValueError(f"Unsupported aggregation function: {function}")
        
        grouped_data = {}
        for item in data:
            key = item.get(group_by)
            if key not in grouped_data:
                grouped_data[key] = []
            
            value = item.get(aggregate_field, 0)
            if isinstance(value, (int, float)):
                grouped_data[key].append(value)
        
        # Apply aggregation function
        result = {}
        agg_func = self.aggregation_functions[function]
        for key, values in grouped_data.items():
            result[key] = agg_func(values)
        
        return result
    
    def time_series_aggregate(self, data: List[Dict[str, Any]], date_field: str, 
                            value_field: str, period: str = 'daily') -> List[Dict[str, Any]]:
        """Aggregate data into time series"""
        # Group data by time period
        time_groups = {}
        
        for item in data:
            date_value = item.get(date_field)
            if not date_value:
                continue
            
            # Convert to datetime if needed
            if isinstance(date_value, str):
                date_value = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            
            # Determine time period key
            if period == 'daily':
                period_key = date_value.strftime('%Y-%m-%d')
            elif period == 'weekly':
                period_key = date_value.strftime('%Y-W%U')
            elif period == 'monthly':
                period_key = date_value.strftime('%Y-%m')
            else:
                period_key = date_value.strftime('%Y-%m-%d')
            
            if period_key not in time_groups:
                time_groups[period_key] = []
            
            value = item.get(value_field, 0)
            if isinstance(value, (int, float)):
                time_groups[period_key].append(value)
        
        # Convert to time series format
        result = []
        for period_key, values in sorted(time_groups.items()):
            result.append({
                'period': period_key,
                'value': sum(values),
                'count': len(values),
                'average': sum(values) / len(values) if values else 0
            })
        
        return result