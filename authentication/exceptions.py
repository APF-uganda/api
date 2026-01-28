"""
Custom exception handlers for authentication and authorization errors
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, PermissionDenied
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses.
    
    Handles:
    - Authentication errors (401)
    - Permission errors (403)
    - Not found errors (404)
    - Validation errors (400)
    - Server errors (500)
    
    Returns standardized error format:
    {
        "success": false,
        "error": {
            "code": "ERROR_CODE",
            "message": "Human readable message",
            "details": {...}
        }
    }
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    # If response is None, it's an unhandled exception
    if response is None:
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return Response(
            {
                'success': False,
                'error': {
                    'code': 'INTERNAL_SERVER_ERROR',
                    'message': 'An unexpected error occurred. Please try again later.',
                    'details': {}
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Customize response format based on exception type
    error_code = 'UNKNOWN_ERROR'
    error_message = str(exc)
    error_details = {}
    
    # Authentication errors (401)
    if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        error_code = 'AUTHENTICATION_REQUIRED'
        error_message = 'Authentication credentials were not provided or are invalid.'
        
        # Check if token is expired
        if 'expired' in str(exc).lower():
            error_code = 'TOKEN_EXPIRED'
            error_message = 'Your session has expired. Please log in again.'
        elif 'invalid' in str(exc).lower():
            error_code = 'INVALID_TOKEN'
            error_message = 'Invalid authentication token. Please log in again.'
    
    # Permission errors (403)
    elif isinstance(exc, PermissionDenied):
        error_code = 'PERMISSION_DENIED'
        error_message = 'You do not have permission to perform this action.'
        
        # Check if it's a role-based permission error
        if 'admin' in str(exc).lower():
            error_message = 'Admin access required for this operation.'
        elif 'member' in str(exc).lower():
            error_message = 'Member access required for this operation.'
    
    # Validation errors (400)
    elif response.status_code == status.HTTP_400_BAD_REQUEST:
        error_code = 'VALIDATION_ERROR'
        error_message = 'Invalid input data.'
        error_details = response.data if isinstance(response.data, dict) else {'detail': response.data}
    
    # Not found errors (404)
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        error_code = 'NOT_FOUND'
        error_message = 'The requested resource was not found.'
    
    # Method not allowed (405)
    elif response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        error_code = 'METHOD_NOT_ALLOWED'
        error_message = f'Method {context["request"].method} not allowed for this endpoint.'
    
    # Throttled/Rate limited (429)
    elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        error_code = 'RATE_LIMIT_EXCEEDED'
        error_message = 'Too many requests. Please try again later.'
        if 'wait' in response.data:
            error_details['retry_after'] = response.data['wait']
    
    # Build standardized error response
    standardized_response = {
        'success': False,
        'error': {
            'code': error_code,
            'message': error_message,
            'details': error_details
        }
    }
    
    # Log the error
    logger.warning(
        f"API Error: {error_code} | {error_message} | "
        f"Path: {context['request'].path} | "
        f"Method: {context['request'].method}"
    )
    
    return Response(standardized_response, status=response.status_code)
