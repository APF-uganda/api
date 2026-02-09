"""
Structured logging utilities for payment operations.
Implements correlation IDs, performance metrics, and sensitive data masking.
"""
import logging
import time
import uuid
from typing import Dict, Any, Optional
from functools import wraps
from contextvars import ContextVar

# Context variable for correlation ID (thread-safe)
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class CorrelationIdFilter(logging.Filter):
    """
    Logging filter that adds correlation ID to log records.
    
    Requirements: 15.1, 15.6
    """
    
    def filter(self, record):
        """Add correlation ID to log record."""
        record.correlation_id = correlation_id_var.get() or 'no-correlation-id'
        return True


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that masks sensitive data in log records.
    
    Masks:
    - Phone numbers (shows only first 3 and last 4 digits)
    - API keys and tokens
    - Passwords
    
    Requirements: 15.2, 7.5, 9.7
    """
    
    SENSITIVE_FIELDS = [
        'phone_number',
        'phone',
        'msisdn',
        'api_key',
        'api_secret',
        'access_token',
        'password',
        'secret',
        'authorization'
    ]
    
    def filter(self, record):
        """Mask sensitive data in log record."""
        # Mask sensitive data in extra fields
        if hasattr(record, '__dict__'):
            for field in self.SENSITIVE_FIELDS:
                if field in record.__dict__:
                    record.__dict__[field] = self._mask_value(record.__dict__[field], field)
        
        # Mask sensitive data in message
        if hasattr(record, 'msg'):
            record.msg = self._mask_message(str(record.msg))
        
        return True
    
    def _mask_value(self, value: Any, field: str) -> str:
        """
        Mask a sensitive value.
        
        Args:
            value: Value to mask
            field: Field name
        
        Returns:
            Masked value
        """
        if value is None:
            return None
        
        value_str = str(value)
        
        # Phone number masking (256XXXXXXXXX -> 256****3456)
        if field in ['phone_number', 'phone', 'msisdn']:
            if len(value_str) >= 8:
                return f"{value_str[:3]}****{value_str[-4:]}"
            return '****'
        
        # API key/token masking (show first 4 chars)
        if field in ['api_key', 'api_secret', 'access_token', 'authorization']:
            if len(value_str) > 8:
                return f"{value_str[:4]}...{value_str[-4:]}"
            return '****'
        
        # Complete masking for passwords and secrets
        if field in ['password', 'secret']:
            return '****'
        
        return value_str
    
    def _mask_message(self, message: str) -> str:
        """
        Mask sensitive data in log message.
        
        Args:
            message: Log message
        
        Returns:
            Message with sensitive data masked
        """
        # Simple pattern matching for phone numbers (256XXXXXXXXX)
        import re
        
        # Mask phone numbers
        message = re.sub(
            r'256\d{9}',
            lambda m: f"{m.group()[:3]}****{m.group()[-4:]}",
            message
        )
        
        return message


class PerformanceLoggingMixin:
    """
    Mixin for adding performance logging to service methods.
    
    Requirements: 15.7
    """
    
    @staticmethod
    def log_performance(operation_name: str):
        """
        Decorator for logging method performance.
        
        Args:
            operation_name: Name of the operation being logged
        
        Usage:
            @log_performance('payment_initiation')
            def initiate_payment(self, ...):
                ...
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                correlation_id = correlation_id_var.get()
                
                logger = logging.getLogger(func.__module__)
                
                try:
                    # Log operation start
                    logger.info(
                        f"Starting {operation_name}",
                        extra={
                            'operation': operation_name,
                            'correlation_id': correlation_id,
                            'function': func.__name__
                        }
                    )
                    
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    # Calculate duration
                    duration = time.time() - start_time
                    
                    # Log operation completion
                    logger.info(
                        f"Completed {operation_name}",
                        extra={
                            'operation': operation_name,
                            'correlation_id': correlation_id,
                            'function': func.__name__,
                            'duration_seconds': round(duration, 3),
                            'success': True
                        }
                    )
                    
                    return result
                
                except Exception as e:
                    # Calculate duration
                    duration = time.time() - start_time
                    
                    # Log operation failure
                    logger.error(
                        f"Failed {operation_name}",
                        extra={
                            'operation': operation_name,
                            'correlation_id': correlation_id,
                            'function': func.__name__,
                            'duration_seconds': round(duration, 3),
                            'success': False,
                            'error': str(e)
                        },
                        exc_info=True
                    )
                    
                    raise
            
            return wrapper
        return decorator


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set correlation ID for current context.
    
    Args:
        correlation_id: Optional correlation ID (generates new UUID if not provided)
    
    Returns:
        The correlation ID that was set
    
    Requirements: 15.6
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    
    correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """
    Get correlation ID for current context.
    
    Returns:
        Current correlation ID or None
    """
    return correlation_id_var.get()


def clear_correlation_id() -> None:
    """Clear correlation ID for current context."""
    correlation_id_var.set(None)


def create_log_context(
    operation: str,
    payment_id: Optional[str] = None,
    transaction_reference: Optional[str] = None,
    provider: Optional[str] = None,
    user_id: Optional[int] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create structured log context dictionary.
    
    Args:
        operation: Operation name
        payment_id: Optional payment ID
        transaction_reference: Optional transaction reference
        provider: Optional provider name
        user_id: Optional user ID
        **kwargs: Additional context fields
    
    Returns:
        Dictionary with log context
    
    Requirements: 15.1, 15.3
    """
    context = {
        'operation': operation,
        'correlation_id': get_correlation_id() or 'no-correlation-id',
        'timestamp': time.time()
    }
    
    if payment_id:
        context['payment_id'] = payment_id
    
    if transaction_reference:
        context['transaction_reference'] = transaction_reference
    
    if provider:
        context['provider'] = provider
    
    if user_id:
        context['user_id'] = user_id
    
    # Add any additional context
    context.update(kwargs)
    
    return context


def log_api_call(
    logger: logging.Logger,
    provider: str,
    endpoint: str,
    method: str,
    duration: float,
    status_code: Optional[int] = None,
    success: bool = True,
    error: Optional[str] = None
) -> None:
    """
    Log API call with performance metrics.
    
    Args:
        logger: Logger instance
        provider: Provider name ('mtn' or 'airtel')
        endpoint: API endpoint
        method: HTTP method
        duration: Request duration in seconds
        status_code: Optional HTTP status code
        success: Whether the call was successful
        error: Optional error message
    
    Requirements: 15.2, 15.7
    """
    context = create_log_context(
        operation='api_call',
        provider=provider,
        endpoint=endpoint,
        method=method,
        duration_seconds=round(duration, 3),
        success=success
    )
    
    if status_code:
        context['status_code'] = status_code
    
    if error:
        context['error'] = error
    
    if success:
        logger.info(f"API call to {provider} {endpoint}", extra=context)
    else:
        logger.error(f"API call failed to {provider} {endpoint}", extra=context)


def log_payment_event(
    logger: logging.Logger,
    event_type: str,
    payment_id: str,
    transaction_reference: str,
    provider: str,
    status: str,
    amount: Optional[str] = None,
    user_id: Optional[int] = None,
    error: Optional[str] = None,
    **kwargs
) -> None:
    """
    Log payment event with structured context.
    
    Args:
        logger: Logger instance
        event_type: Type of event (e.g., 'initiated', 'completed', 'failed')
        payment_id: Payment ID
        transaction_reference: Transaction reference
        provider: Provider name
        status: Payment status
        amount: Optional payment amount
        user_id: Optional user ID
        error: Optional error message
        **kwargs: Additional context
    
    Requirements: 15.1, 15.3
    """
    context = create_log_context(
        operation='payment_event',
        event_type=event_type,
        payment_id=payment_id,
        transaction_reference=transaction_reference,
        provider=provider,
        status=status,
        user_id=user_id,
        **kwargs
    )
    
    if amount:
        context['amount'] = amount
    
    if error:
        context['error'] = error
    
    log_level = logging.INFO
    if event_type in ['failed', 'timeout', 'error']:
        log_level = logging.ERROR
    elif event_type == 'completed':
        log_level = logging.INFO
    
    logger.log(
        log_level,
        f"Payment {event_type}: {transaction_reference}",
        extra=context
    )


def configure_payment_logging():
    """
    Configure logging for payment operations.
    
    Adds:
    - Correlation ID filter
    - Sensitive data filter
    - Structured logging format
    
    Requirements: 15.1-15.6
    """
    # Get payment logger
    payment_logger = logging.getLogger('payments')
    
    # Add correlation ID filter
    correlation_filter = CorrelationIdFilter()
    payment_logger.addFilter(correlation_filter)
    
    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()
    payment_logger.addFilter(sensitive_filter)
    
    # Configure format for structured logging
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s'
    )
    
    # Apply formatter to all handlers
    for handler in payment_logger.handlers:
        handler.setFormatter(formatter)
    
    return payment_logger
