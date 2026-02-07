"""
Rate limiting and logging middleware for payment operations.
"""
import logging
import time
import uuid
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger(__name__)


class PaymentRateLimitMiddleware:
    """
    Rate limiting middleware for payment endpoints.
    
    Implements:
    - Per-user rate limiting (10 requests/minute)
    - Per-IP rate limiting (20 requests/minute)
    
    Returns HTTP 429 when limit exceeded.
    
    Requirements: 7.7
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limit_requests = getattr(settings, 'PAYMENT_RATE_LIMIT_REQUESTS', 10)
        self.rate_limit_window = getattr(settings, 'PAYMENT_RATE_LIMIT_WINDOW', 60)
        self.ip_rate_limit_requests = 20  # Per-IP limit
        
    def __call__(self, request):
        # Only apply rate limiting to payment endpoints
        if not request.path.startswith('/api/v1/payments/'):
            return self.get_response(request)
        
        # Skip rate limiting for webhook endpoints (external services)
        if '/webhooks/' in request.path:
            return self.get_response(request)
        
        # Skip rate limiting for GET requests (status checks, membership fee)
        if request.method == 'GET':
            return self.get_response(request)
        
        # Apply rate limiting only to POST requests (initiate, retry, cancel)
        if request.method == 'POST':
            # Check per-user rate limit (if authenticated)
            if hasattr(request, 'user') and request.user and request.user.is_authenticated:
                user_limited, user_retry_after = self._check_user_rate_limit(request.user.id)
                if user_limited:
                    logger.warning(
                        f"User rate limit exceeded",
                        extra={
                            "user_id": request.user.id,
                            "path": request.path,
                            "method": request.method
                        }
                    )
                    return JsonResponse({
                        'error': {
                            'code': 'RATE_LIMIT_EXCEEDED',
                            'message': 'Too many payment requests. Please wait a moment and try again.',
                            'retry_after': user_retry_after
                        }
                    }, status=429)
            
            # Check per-IP rate limit
            client_ip = self._get_client_ip(request)
            ip_limited, ip_retry_after = self._check_ip_rate_limit(client_ip)
            if ip_limited:
                logger.warning(
                    f"IP rate limit exceeded",
                    extra={
                        "ip_address": client_ip,
                        "path": request.path,
                        "method": request.method
                    }
                )
                return JsonResponse({
                    'error': {
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'message': 'Too many payment requests from this IP. Please wait a moment and try again.',
                        'retry_after': ip_retry_after
                    }
                }, status=429)
        
        response = self.get_response(request)
        return response
    
    def _check_user_rate_limit(self, user_id):
        """
        Check if user has exceeded rate limit.
        
        Args:
            user_id: User ID
        
        Returns:
            Tuple of (is_limited, retry_after_seconds)
        """
        cache_key = f'payment_rate_limit_user_{user_id}'
        
        # Get current request count and timestamp
        data = cache.get(cache_key)
        current_time = time.time()
        
        if data is None:
            # First request in window
            cache.set(cache_key, {
                'count': 1,
                'start_time': current_time
            }, timeout=self.rate_limit_window)
            return False, 0
        
        # Check if window has expired
        elapsed = current_time - data['start_time']
        if elapsed > self.rate_limit_window:
            # Window expired, reset counter
            cache.set(cache_key, {
                'count': 1,
                'start_time': current_time
            }, timeout=self.rate_limit_window)
            return False, 0
        
        # Check if limit exceeded
        if data['count'] >= self.rate_limit_requests:
            # Rate limit exceeded
            retry_after = int(self.rate_limit_window - elapsed)
            return True, retry_after
        
        # Increment counter
        data['count'] += 1
        cache.set(cache_key, data, timeout=self.rate_limit_window)
        return False, 0
    
    def _check_ip_rate_limit(self, ip_address):
        """
        Check if IP has exceeded rate limit.
        
        Args:
            ip_address: Client IP address
        
        Returns:
            Tuple of (is_limited, retry_after_seconds)
        """
        cache_key = f'payment_rate_limit_ip_{ip_address}'
        
        # Get current request count and timestamp
        data = cache.get(cache_key)
        current_time = time.time()
        
        if data is None:
            # First request in window
            cache.set(cache_key, {
                'count': 1,
                'start_time': current_time
            }, timeout=self.rate_limit_window)
            return False, 0
        
        # Check if window has expired
        elapsed = current_time - data['start_time']
        if elapsed > self.rate_limit_window:
            # Window expired, reset counter
            cache.set(cache_key, {
                'count': 1,
                'start_time': current_time
            }, timeout=self.rate_limit_window)
            return False, 0
        
        # Check if limit exceeded
        if data['count'] >= self.ip_rate_limit_requests:
            # Rate limit exceeded
            retry_after = int(self.rate_limit_window - elapsed)
            return True, retry_after
        
        # Increment counter
        data['count'] += 1
        cache.set(cache_key, data, timeout=self.rate_limit_window)
        return False, 0
    
    def _get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip


class PaymentLoggingMiddleware:
    """
    Logging middleware for payment operations.
    
    Logs all payment operations with:
    - Correlation IDs for request tracing
    - Masked sensitive data (phone numbers)
    - Request/response context
    
    Requirements: 15.1, 15.2, 15.3
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Only log payment endpoints
        if not request.path.startswith('/api/v1/payments/'):
            return self.get_response(request)
        
        # Generate correlation ID for request tracing
        correlation_id = str(uuid.uuid4())
        request.correlation_id = correlation_id
        
        # Log request
        self._log_request(request, correlation_id)
        
        # Process request
        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time
        
        # Log response
        self._log_response(request, response, correlation_id, duration)
        
        # Add correlation ID to response headers
        response['X-Correlation-ID'] = correlation_id
        
        return response
    
    def _log_request(self, request, correlation_id):
        """Log incoming request with context."""
        # Get user info
        user_id = None
        if hasattr(request, 'user') and request.user and request.user.is_authenticated:
            user_id = request.user.id
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Log request
        logger.info(
            f"Payment request received",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.path,
                "user_id": user_id,
                "ip_address": client_ip,
                "user_agent": request.META.get('HTTP_USER_AGENT', '')[:200]
            }
        )
    
    def _log_response(self, request, response, correlation_id, duration):
        """Log response with context."""
        # Get user info
        user_id = None
        if hasattr(request, 'user') and request.user and request.user.is_authenticated:
            user_id = request.user.id
        
        # Determine log level based on status code
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO
        
        # Log response
        logger.log(
            log_level,
            f"Payment request completed",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.path,
                "user_id": user_id,
                "status_code": response.status_code,
                "duration_ms": int(duration * 1000)
            }
        )
    
    def _get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
