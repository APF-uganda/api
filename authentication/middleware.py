"""
Custom middleware for authentication and security
"""

from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import logging

logger = logging.getLogger(__name__)


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware to automatically authenticate users via JWT tokens.
    
    This middleware:
    1. Extracts JWT token from Authorization header
    2. Validates and decodes the token
    3. Attaches the user to the request object
    4. Handles token errors gracefully
    
    Public endpoints (no authentication required):
    - /api/auth/login
    - /api/auth/verify-otp
    - /api/auth/refresh
    - /api/auth/password-reset-request
    - /api/auth/password-reset-confirm
    - /api/applications/ (POST only)
    - /api/contacts/submit/ (POST only)
    - / (health check)
    """
    
    # Endpoints that don't require authentication
    PUBLIC_ENDPOINTS = [
        '/api/auth/login',
        '/api/auth/verify-otp',
        '/api/auth/refresh',
        '/api/auth/password-reset-request',
        '/api/auth/password-reset-confirm',
        '/',  # Health check
    ]
    
    # Endpoints that allow public POST but require auth for other methods
    PUBLIC_POST_ENDPOINTS = [
        '/api/applications/',
        '/api/contacts/submit/',
    ]
    
    def process_request(self, request):
        """
        Process incoming request and authenticate user if JWT token is present.
        """
        # Skip authentication for public endpoints
        if self._is_public_endpoint(request):
            return None
        
        # Try to authenticate using JWT
        jwt_auth = JWTAuthentication()
        
        try:
            # Attempt to authenticate
            auth_result = jwt_auth.authenticate(request)
            
            if auth_result is not None:
                user, token = auth_result
                request.user = user
                request.auth = token
                logger.debug(f"User {user.email} authenticated via JWT")
            else:
                # No token provided - will be handled by view permissions
                logger.debug("No JWT token provided in request")
                
        except (InvalidToken, TokenError) as e:
            # Token is invalid or expired
            logger.warning(f"JWT authentication failed: {str(e)}")
            # Don't return error here - let view permissions handle it
            pass
        except Exception as e:
            # Unexpected error
            logger.error(f"Unexpected error in JWT middleware: {str(e)}")
            pass
        
        return None
    
    def _is_public_endpoint(self, request):
        """
        Check if the endpoint is public (doesn't require authentication).
        """
        path = request.path
        method = request.method
        
        # Check if path is in public endpoints
        if path in self.PUBLIC_ENDPOINTS:
            return True
        
        # Check if path allows public POST
        if method == 'POST' and path in self.PUBLIC_POST_ENDPOINTS:
            return True
        
        # Check if path starts with any public endpoint (for trailing slashes)
        for public_path in self.PUBLIC_ENDPOINTS:
            if path.rstrip('/') == public_path.rstrip('/'):
                return True
        
        return False


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers to all responses.
    
    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: max-age=31536000; includeSubDomains
    """
    
    def process_response(self, request, response):
        """
        Add security headers to response.
        """
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # Enable XSS protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Force HTTPS (only in production)
        if not request.is_secure() and not request.get_host().startswith('localhost'):
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all API requests for security monitoring.
    
    Logs:
    - Request method and path
    - User (if authenticated)
    - IP address
    - User agent
    - Response status code
    """
    
    def process_request(self, request):
        """
        Log incoming request details.
        """
        # Get client IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        # Get user agent
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
        
        # Get user email if authenticated
        user_email = 'Anonymous'
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_email = request.user.email
        
        # Log request
        logger.info(
            f"API Request: {request.method} {request.path} | "
            f"User: {user_email} | IP: {ip} | UA: {user_agent[:50]}"
        )
        
        return None
    
    def process_response(self, request, response):
        """
        Log response status code.
        """
        logger.info(
            f"API Response: {request.method} {request.path} | "
            f"Status: {response.status_code}"
        )
        
        return response
