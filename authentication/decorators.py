"""
Decorators for authentication views
"""

from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from authentication.services import RateLimitService, AuditLoggingService, AuthenticationService
from authentication.models import AuthEventType


def rate_limit(func):
    """
    Decorator to apply rate limiting to authentication views
    
    Checks if the client IP or email has exceeded the rate limit.
    Returns 429 status with Retry-After header if rate limited.
    Logs rate limit events via AuditLoggingService.
    
    Usage:
        @rate_limit
        def post(self, request):
            ...
    """
    @wraps(func)
    def wrapper(view_instance, request, *args, **kwargs):
        # Extract IP address and email from request
        ip_address = AuthenticationService.get_client_ip(request)
        
        # Safely get email from request data
        email = ''
        try:
            if hasattr(request, 'data') and request.data:
                email = request.data.get('email', '')
            elif hasattr(request, 'POST') and request.POST:
                email = request.POST.get('email', '')
        except:
            email = ''
        
        # Check if rate limited
        is_limited, retry_after = RateLimitService.is_rate_limited(ip_address, email)
        
        if is_limited:
            # Log rate limit event
            user_agent = AuthenticationService.get_user_agent(request)
            AuditLoggingService.log_auth_event(
                user=None,
                email=email,
                event_type=AuthEventType.RATE_LIMIT_TRIGGERED,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                details={
                    'retry_after': retry_after,
                    'endpoint': request.path
                }
            )
            
            # Return 429 response with Retry-After header
            response = Response(
                {
                    'success': False,
                    'error': {
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'message': f'Too many failed attempts. Please try again in {retry_after} seconds.',
                        'details': {
                            'retry_after': retry_after
                        }
                    }
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
            response['Retry-After'] = str(retry_after)
            return response
        
        # Not rate limited, proceed with the view
        return func(view_instance, request, *args, **kwargs)
    
    return wrapper
