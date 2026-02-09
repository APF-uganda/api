"""
Payment metrics tracking service.
Tracks success rate, completion time, timeout rate, and retry rate by provider.
"""
import logging
from datetime import timedelta
from decimal import Decimal
from typing import Dict, Any, Optional
from django.db.models import Count, Avg, Q, F
from django.utils import timezone

from payments.models import Payment

logger = logging.getLogger(__name__)


class PaymentMetricsService:
    """
    Service for tracking and calculating payment metrics.
    
    Tracks:
    - Success rate by provider
    - Average completion time
    - Timeout rate
    - Retry rate
    
    Requirements: 15.7
    """
    
    def get_success_rate(self, provider: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        """
        Calculate payment success rate.
        
        Args:
            provider: Optional provider filter ('mtn' or 'airtel')
            hours: Time window in hours (default 24)
        
        Returns:
            Dictionary with success rate metrics:
            {
                'total_payments': int,
                'successful_payments': int,
                'success_rate': float (0-100),
                'provider': str or 'all'
            }
        """
        try:
            # Calculate time threshold
            time_threshold = timezone.now() - timedelta(hours=hours)
            
            # Base queryset
            queryset = Payment.objects.filter(created_at__gte=time_threshold)
            
            # Apply provider filter if specified
            if provider:
                queryset = queryset.filter(provider=provider)
            
            # Count total and successful payments
            total_payments = queryset.count()
            successful_payments = queryset.filter(status=Payment.STATUS_COMPLETED).count()
            
            # Calculate success rate
            success_rate = (successful_payments / total_payments * 100) if total_payments > 0 else 0.0
            
            result = {
                'total_payments': total_payments,
                'successful_payments': successful_payments,
                'success_rate': round(success_rate, 2),
                'provider': provider or 'all',
                'time_window_hours': hours
            }
            
            logger.info(
                f"Success rate calculated",
                extra={
                    'provider': provider or 'all',
                    'success_rate': result['success_rate'],
                    'total_payments': total_payments,
                    'time_window_hours': hours
                }
            )
            
            return result
        
        except Exception as e:
            logger.error(
                f"Failed to calculate success rate",
                extra={'provider': provider, 'error': str(e)},
                exc_info=True
            )
            return {
                'total_payments': 0,
                'successful_payments': 0,
                'success_rate': 0.0,
                'provider': provider or 'all',
                'error': str(e)
            }
    
    def get_success_rate_by_provider(self, hours: int = 24) -> Dict[str, Dict[str, Any]]:
        """
        Calculate success rate for each provider separately.
        
        Args:
            hours: Time window in hours (default 24)
        
        Returns:
            Dictionary with success rates by provider:
            {
                'mtn': {'total': int, 'successful': int, 'rate': float},
                'airtel': {'total': int, 'successful': int, 'rate': float},
                'overall': {'total': int, 'successful': int, 'rate': float}
            }
        """
        try:
            mtn_metrics = self.get_success_rate(provider=Payment.PROVIDER_MTN, hours=hours)
            airtel_metrics = self.get_success_rate(provider=Payment.PROVIDER_AIRTEL, hours=hours)
            overall_metrics = self.get_success_rate(provider=None, hours=hours)
            
            return {
                'mtn': {
                    'total': mtn_metrics['total_payments'],
                    'successful': mtn_metrics['successful_payments'],
                    'rate': mtn_metrics['success_rate']
                },
                'airtel': {
                    'total': airtel_metrics['total_payments'],
                    'successful': airtel_metrics['successful_payments'],
                    'rate': airtel_metrics['success_rate']
                },
                'overall': {
                    'total': overall_metrics['total_payments'],
                    'successful': overall_metrics['successful_payments'],
                    'rate': overall_metrics['success_rate']
                },
                'time_window_hours': hours
            }
        
        except Exception as e:
            logger.error(
                f"Failed to calculate success rate by provider",
                extra={'error': str(e)},
                exc_info=True
            )
            return {
                'mtn': {'total': 0, 'successful': 0, 'rate': 0.0},
                'airtel': {'total': 0, 'successful': 0, 'rate': 0.0},
                'overall': {'total': 0, 'successful': 0, 'rate': 0.0},
                'error': str(e)
            }
    
    def get_average_completion_time(self, provider: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        """
        Calculate average payment completion time.
        
        Args:
            provider: Optional provider filter ('mtn' or 'airtel')
            hours: Time window in hours (default 24)
        
        Returns:
            Dictionary with completion time metrics:
            {
                'average_seconds': float,
                'completed_payments': int,
                'provider': str or 'all'
            }
        """
        try:
            # Calculate time threshold
            time_threshold = timezone.now() - timedelta(hours=hours)
            
            # Base queryset - only completed payments
            queryset = Payment.objects.filter(
                created_at__gte=time_threshold,
                status=Payment.STATUS_COMPLETED,
                completed_at__isnull=False
            )
            
            # Apply provider filter if specified
            if provider:
                queryset = queryset.filter(provider=provider)
            
            # Calculate completion times
            completed_payments = queryset.count()
            
            if completed_payments == 0:
                return {
                    'average_seconds': 0.0,
                    'completed_payments': 0,
                    'provider': provider or 'all',
                    'time_window_hours': hours
                }
            
            # Calculate average time difference between created_at and completed_at
            total_seconds = 0
            for payment in queryset:
                time_diff = (payment.completed_at - payment.created_at).total_seconds()
                total_seconds += time_diff
            
            average_seconds = total_seconds / completed_payments if completed_payments > 0 else 0.0
            
            result = {
                'average_seconds': round(average_seconds, 2),
                'completed_payments': completed_payments,
                'provider': provider or 'all',
                'time_window_hours': hours
            }
            
            logger.info(
                f"Average completion time calculated",
                extra={
                    'provider': provider or 'all',
                    'average_seconds': result['average_seconds'],
                    'completed_payments': completed_payments,
                    'time_window_hours': hours
                }
            )
            
            return result
        
        except Exception as e:
            logger.error(
                f"Failed to calculate average completion time",
                extra={'provider': provider, 'error': str(e)},
                exc_info=True
            )
            return {
                'average_seconds': 0.0,
                'completed_payments': 0,
                'provider': provider or 'all',
                'error': str(e)
            }
    
    def get_timeout_rate(self, provider: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        """
        Calculate payment timeout rate.
        
        Args:
            provider: Optional provider filter ('mtn' or 'airtel')
            hours: Time window in hours (default 24)
        
        Returns:
            Dictionary with timeout rate metrics:
            {
                'total_payments': int,
                'timeout_payments': int,
                'timeout_rate': float (0-100),
                'provider': str or 'all'
            }
        """
        try:
            # Calculate time threshold
            time_threshold = timezone.now() - timedelta(hours=hours)
            
            # Base queryset
            queryset = Payment.objects.filter(created_at__gte=time_threshold)
            
            # Apply provider filter if specified
            if provider:
                queryset = queryset.filter(provider=provider)
            
            # Count total and timeout payments
            total_payments = queryset.count()
            timeout_payments = queryset.filter(status=Payment.STATUS_TIMEOUT).count()
            
            # Calculate timeout rate
            timeout_rate = (timeout_payments / total_payments * 100) if total_payments > 0 else 0.0
            
            result = {
                'total_payments': total_payments,
                'timeout_payments': timeout_payments,
                'timeout_rate': round(timeout_rate, 2),
                'provider': provider or 'all',
                'time_window_hours': hours
            }
            
            logger.info(
                f"Timeout rate calculated",
                extra={
                    'provider': provider or 'all',
                    'timeout_rate': result['timeout_rate'],
                    'timeout_payments': timeout_payments,
                    'time_window_hours': hours
                }
            )
            
            return result
        
        except Exception as e:
            logger.error(
                f"Failed to calculate timeout rate",
                extra={'provider': provider, 'error': str(e)},
                exc_info=True
            )
            return {
                'total_payments': 0,
                'timeout_payments': 0,
                'timeout_rate': 0.0,
                'provider': provider or 'all',
                'error': str(e)
            }
    
    def get_retry_rate(self, provider: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        """
        Calculate payment retry rate.
        
        Identifies retries by finding payments with the same user, amount, and provider
        within a short time window (5 minutes) after a failed/timeout payment.
        
        Args:
            provider: Optional provider filter ('mtn' or 'airtel')
            hours: Time window in hours (default 24)
        
        Returns:
            Dictionary with retry rate metrics:
            {
                'failed_or_timeout_payments': int,
                'retried_payments': int,
                'retry_rate': float (0-100),
                'provider': str or 'all'
            }
        """
        try:
            # Calculate time threshold
            time_threshold = timezone.now() - timedelta(hours=hours)
            
            # Base queryset - failed or timeout payments
            failed_queryset = Payment.objects.filter(
                created_at__gte=time_threshold,
                status__in=[Payment.STATUS_FAILED, Payment.STATUS_TIMEOUT]
            )
            
            # Apply provider filter if specified
            if provider:
                failed_queryset = failed_queryset.filter(provider=provider)
            
            failed_count = failed_queryset.count()
            
            if failed_count == 0:
                return {
                    'failed_or_timeout_payments': 0,
                    'retried_payments': 0,
                    'retry_rate': 0.0,
                    'provider': provider or 'all',
                    'time_window_hours': hours
                }
            
            # Count retries by checking for subsequent payments with same user/amount/provider
            retry_count = 0
            for failed_payment in failed_queryset:
                # Look for a payment within 5 minutes after this one with same details
                retry_window_start = failed_payment.created_at
                retry_window_end = failed_payment.created_at + timedelta(minutes=5)
                
                retry_exists = Payment.objects.filter(
                    user=failed_payment.user,
                    amount=failed_payment.amount,
                    provider=failed_payment.provider,
                    created_at__gt=retry_window_start,
                    created_at__lte=retry_window_end
                ).exclude(id=failed_payment.id).exists()
                
                if retry_exists:
                    retry_count += 1
            
            # Calculate retry rate
            retry_rate = (retry_count / failed_count * 100) if failed_count > 0 else 0.0
            
            result = {
                'failed_or_timeout_payments': failed_count,
                'retried_payments': retry_count,
                'retry_rate': round(retry_rate, 2),
                'provider': provider or 'all',
                'time_window_hours': hours
            }
            
            logger.info(
                f"Retry rate calculated",
                extra={
                    'provider': provider or 'all',
                    'retry_rate': result['retry_rate'],
                    'retried_payments': retry_count,
                    'time_window_hours': hours
                }
            )
            
            return result
        
        except Exception as e:
            logger.error(
                f"Failed to calculate retry rate",
                extra={'provider': provider, 'error': str(e)},
                exc_info=True
            )
            return {
                'failed_or_timeout_payments': 0,
                'retried_payments': 0,
                'retry_rate': 0.0,
                'provider': provider or 'all',
                'error': str(e)
            }
    
    def get_all_metrics(self, provider: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        """
        Get all payment metrics in one call.
        
        Args:
            provider: Optional provider filter ('mtn' or 'airtel')
            hours: Time window in hours (default 24)
        
        Returns:
            Dictionary with all metrics:
            {
                'success_rate': {...},
                'average_completion_time': {...},
                'timeout_rate': {...},
                'retry_rate': {...},
                'timestamp': str
            }
        """
        try:
            return {
                'success_rate': self.get_success_rate(provider, hours),
                'average_completion_time': self.get_average_completion_time(provider, hours),
                'timeout_rate': self.get_timeout_rate(provider, hours),
                'retry_rate': self.get_retry_rate(provider, hours),
                'timestamp': timezone.now().isoformat()
            }
        except Exception as e:
            logger.error(
                f"Failed to get all metrics",
                extra={'provider': provider, 'error': str(e)},
                exc_info=True
            )
            return {
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }
