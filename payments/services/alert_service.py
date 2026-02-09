"""
Payment alert service.
Monitors payment metrics and triggers alerts when thresholds are exceeded.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache

from payments.services.metrics_service import PaymentMetricsService

logger = logging.getLogger(__name__)


class AlertService:
    """
    Service for monitoring payment metrics and triggering alerts.
    
    Alerts on:
    - Success rate < 90%
    - API response time > 5 seconds
    - Authentication failures
    - Webhook verification failures
    
    Requirements: 15.8
    """
    
    # Alert thresholds
    SUCCESS_RATE_THRESHOLD = 90.0  # Percentage
    API_RESPONSE_TIME_THRESHOLD = 5.0  # Seconds
    AUTH_FAILURE_THRESHOLD = 10  # Count within time window
    AUTH_FAILURE_WINDOW = 5  # Minutes
    WEBHOOK_VERIFICATION_FAILURE_THRESHOLD = 5  # Count within time window
    WEBHOOK_FAILURE_WINDOW = 10  # Minutes
    
    # Cache keys for tracking failures
    AUTH_FAILURE_CACHE_KEY = 'payment_auth_failures'
    WEBHOOK_FAILURE_CACHE_KEY = 'payment_webhook_failures'
    ALERT_COOLDOWN_KEY_PREFIX = 'payment_alert_cooldown_'
    
    # Alert cooldown period (don't send same alert within this time)
    ALERT_COOLDOWN_MINUTES = 15
    
    def __init__(self):
        """Initialize alert service with metrics service."""
        self.metrics_service = PaymentMetricsService()
    
    def check_success_rate_alert(self, provider: Optional[str] = None, hours: int = 1) -> Optional[Dict[str, Any]]:
        """
        Check if success rate is below threshold and trigger alert.
        
        Args:
            provider: Optional provider filter ('mtn' or 'airtel')
            hours: Time window in hours (default 1)
        
        Returns:
            Alert dictionary if threshold exceeded, None otherwise
        """
        try:
            # Get success rate metrics
            metrics = self.metrics_service.get_success_rate(provider, hours)
            
            # Check if we have enough data (at least 10 payments)
            if metrics['total_payments'] < 10:
                return None
            
            # Check if success rate is below threshold
            if metrics['success_rate'] < self.SUCCESS_RATE_THRESHOLD:
                alert_key = f"success_rate_{provider or 'all'}"
                
                # Check cooldown
                if self._is_alert_in_cooldown(alert_key):
                    return None
                
                alert = {
                    'type': 'success_rate_low',
                    'severity': 'high',
                    'provider': provider or 'all',
                    'current_rate': metrics['success_rate'],
                    'threshold': self.SUCCESS_RATE_THRESHOLD,
                    'total_payments': metrics['total_payments'],
                    'successful_payments': metrics['successful_payments'],
                    'time_window_hours': hours,
                    'message': f"Payment success rate ({metrics['success_rate']}%) is below threshold ({self.SUCCESS_RATE_THRESHOLD}%) for {provider or 'all providers'}",
                    'timestamp': timezone.now().isoformat()
                }
                
                # Log alert
                logger.critical(
                    f"ALERT: Success rate below threshold",
                    extra=alert
                )
                
                # Set cooldown
                self._set_alert_cooldown(alert_key)
                
                return alert
            
            return None
        
        except Exception as e:
            logger.error(
                f"Failed to check success rate alert",
                extra={'provider': provider, 'error': str(e)},
                exc_info=True
            )
            return None
    
    def check_api_response_time_alert(self, response_time: float, provider: str, endpoint: str) -> Optional[Dict[str, Any]]:
        """
        Check if API response time exceeds threshold and trigger alert.
        
        Args:
            response_time: Response time in seconds
            provider: Provider name ('mtn' or 'airtel')
            endpoint: API endpoint called
        
        Returns:
            Alert dictionary if threshold exceeded, None otherwise
        """
        try:
            if response_time > self.API_RESPONSE_TIME_THRESHOLD:
                alert_key = f"api_response_time_{provider}_{endpoint}"
                
                # Check cooldown
                if self._is_alert_in_cooldown(alert_key):
                    return None
                
                alert = {
                    'type': 'api_response_time_high',
                    'severity': 'medium',
                    'provider': provider,
                    'endpoint': endpoint,
                    'response_time': response_time,
                    'threshold': self.API_RESPONSE_TIME_THRESHOLD,
                    'message': f"API response time ({response_time}s) exceeds threshold ({self.API_RESPONSE_TIME_THRESHOLD}s) for {provider} {endpoint}",
                    'timestamp': timezone.now().isoformat()
                }
                
                # Log alert
                logger.warning(
                    f"ALERT: API response time high",
                    extra=alert
                )
                
                # Set cooldown
                self._set_alert_cooldown(alert_key)
                
                return alert
            
            return None
        
        except Exception as e:
            logger.error(
                f"Failed to check API response time alert",
                extra={'provider': provider, 'endpoint': endpoint, 'error': str(e)},
                exc_info=True
            )
            return None
    
    def record_authentication_failure(self, provider: str, error: str) -> Optional[Dict[str, Any]]:
        """
        Record an authentication failure and check if alert threshold is exceeded.
        
        Args:
            provider: Provider name ('mtn' or 'airtel')
            error: Error message
        
        Returns:
            Alert dictionary if threshold exceeded, None otherwise
        """
        try:
            # Get current failure count from cache
            cache_key = f"{self.AUTH_FAILURE_CACHE_KEY}_{provider}"
            failures = cache.get(cache_key, [])
            
            # Add new failure with timestamp
            failures.append({
                'timestamp': timezone.now().isoformat(),
                'error': error
            })
            
            # Remove failures outside the time window
            cutoff_time = timezone.now() - timedelta(minutes=self.AUTH_FAILURE_WINDOW)
            failures = [
                f for f in failures
                if timezone.datetime.fromisoformat(f['timestamp']) > cutoff_time
            ]
            
            # Update cache
            cache.set(cache_key, failures, timeout=self.AUTH_FAILURE_WINDOW * 60)
            
            # Check if threshold exceeded
            if len(failures) >= self.AUTH_FAILURE_THRESHOLD:
                alert_key = f"auth_failures_{provider}"
                
                # Check cooldown
                if self._is_alert_in_cooldown(alert_key):
                    return None
                
                alert = {
                    'type': 'authentication_failures',
                    'severity': 'critical',
                    'provider': provider,
                    'failure_count': len(failures),
                    'threshold': self.AUTH_FAILURE_THRESHOLD,
                    'time_window_minutes': self.AUTH_FAILURE_WINDOW,
                    'recent_errors': [f['error'] for f in failures[-3:]],  # Last 3 errors
                    'message': f"Authentication failures ({len(failures)}) exceed threshold ({self.AUTH_FAILURE_THRESHOLD}) for {provider} in {self.AUTH_FAILURE_WINDOW} minutes",
                    'timestamp': timezone.now().isoformat()
                }
                
                # Log alert
                logger.critical(
                    f"ALERT: Authentication failures threshold exceeded",
                    extra=alert
                )
                
                # Set cooldown
                self._set_alert_cooldown(alert_key)
                
                return alert
            
            return None
        
        except Exception as e:
            logger.error(
                f"Failed to record authentication failure",
                extra={'provider': provider, 'error': str(e)},
                exc_info=True
            )
            return None
    
    def record_webhook_verification_failure(self, provider: str, reason: str) -> Optional[Dict[str, Any]]:
        """
        Record a webhook verification failure and check if alert threshold is exceeded.
        
        Args:
            provider: Provider name ('mtn' or 'airtel')
            reason: Failure reason
        
        Returns:
            Alert dictionary if threshold exceeded, None otherwise
        """
        try:
            # Get current failure count from cache
            cache_key = f"{self.WEBHOOK_FAILURE_CACHE_KEY}_{provider}"
            failures = cache.get(cache_key, [])
            
            # Add new failure with timestamp
            failures.append({
                'timestamp': timezone.now().isoformat(),
                'reason': reason
            })
            
            # Remove failures outside the time window
            cutoff_time = timezone.now() - timedelta(minutes=self.WEBHOOK_FAILURE_WINDOW)
            failures = [
                f for f in failures
                if timezone.datetime.fromisoformat(f['timestamp']) > cutoff_time
            ]
            
            # Update cache
            cache.set(cache_key, failures, timeout=self.WEBHOOK_FAILURE_WINDOW * 60)
            
            # Check if threshold exceeded
            if len(failures) >= self.WEBHOOK_VERIFICATION_FAILURE_THRESHOLD:
                alert_key = f"webhook_failures_{provider}"
                
                # Check cooldown
                if self._is_alert_in_cooldown(alert_key):
                    return None
                
                alert = {
                    'type': 'webhook_verification_failures',
                    'severity': 'high',
                    'provider': provider,
                    'failure_count': len(failures),
                    'threshold': self.WEBHOOK_VERIFICATION_FAILURE_THRESHOLD,
                    'time_window_minutes': self.WEBHOOK_FAILURE_WINDOW,
                    'recent_reasons': [f['reason'] for f in failures[-3:]],  # Last 3 reasons
                    'message': f"Webhook verification failures ({len(failures)}) exceed threshold ({self.WEBHOOK_VERIFICATION_FAILURE_THRESHOLD}) for {provider} in {self.WEBHOOK_FAILURE_WINDOW} minutes",
                    'timestamp': timezone.now().isoformat()
                }
                
                # Log alert
                logger.critical(
                    f"ALERT: Webhook verification failures threshold exceeded",
                    extra=alert
                )
                
                # Set cooldown
                self._set_alert_cooldown(alert_key)
                
                return alert
            
            return None
        
        except Exception as e:
            logger.error(
                f"Failed to record webhook verification failure",
                extra={'provider': provider, 'error': str(e)},
                exc_info=True
            )
            return None
    
    def check_all_alerts(self, hours: int = 1) -> List[Dict[str, Any]]:
        """
        Check all alert conditions and return list of active alerts.
        
        Args:
            hours: Time window for metrics-based alerts (default 1)
        
        Returns:
            List of alert dictionaries
        """
        alerts = []
        
        try:
            # Check success rate for all providers
            overall_alert = self.check_success_rate_alert(provider=None, hours=hours)
            if overall_alert:
                alerts.append(overall_alert)
            
            # Check success rate for MTN
            mtn_alert = self.check_success_rate_alert(provider='mtn', hours=hours)
            if mtn_alert:
                alerts.append(mtn_alert)
            
            # Check success rate for Airtel
            airtel_alert = self.check_success_rate_alert(provider='airtel', hours=hours)
            if airtel_alert:
                alerts.append(airtel_alert)
            
            return alerts
        
        except Exception as e:
            logger.error(
                f"Failed to check all alerts",
                extra={'error': str(e)},
                exc_info=True
            )
            return alerts
    
    def _is_alert_in_cooldown(self, alert_key: str) -> bool:
        """
        Check if an alert is in cooldown period.
        
        Args:
            alert_key: Unique key for the alert type
        
        Returns:
            True if alert is in cooldown, False otherwise
        """
        cache_key = f"{self.ALERT_COOLDOWN_KEY_PREFIX}{alert_key}"
        return cache.get(cache_key) is not None
    
    def _set_alert_cooldown(self, alert_key: str) -> None:
        """
        Set cooldown period for an alert.
        
        Args:
            alert_key: Unique key for the alert type
        """
        cache_key = f"{self.ALERT_COOLDOWN_KEY_PREFIX}{alert_key}"
        cache.set(cache_key, True, timeout=self.ALERT_COOLDOWN_MINUTES * 60)
    
    def clear_alert_cooldown(self, alert_key: str) -> None:
        """
        Clear cooldown period for an alert (for testing or manual reset).
        
        Args:
            alert_key: Unique key for the alert type
        """
        cache_key = f"{self.ALERT_COOLDOWN_KEY_PREFIX}{alert_key}"
        cache.delete(cache_key)
    
    def get_alert_status(self) -> Dict[str, Any]:
        """
        Get current alert status and recent alerts.
        
        Returns:
            Dictionary with alert status information
        """
        try:
            # Get recent metrics
            metrics = self.metrics_service.get_all_metrics(hours=1)
            
            # Check for active alerts
            active_alerts = self.check_all_alerts(hours=1)
            
            return {
                'active_alerts': active_alerts,
                'alert_count': len(active_alerts),
                'metrics': metrics,
                'timestamp': timezone.now().isoformat()
            }
        
        except Exception as e:
            logger.error(
                f"Failed to get alert status",
                extra={'error': str(e)},
                exc_info=True
            )
            return {
                'active_alerts': [],
                'alert_count': 0,
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }
