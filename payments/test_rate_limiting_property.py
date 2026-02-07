"""
Property-based tests for payment rate limiting.

Feature: mobile-money-payment-integration
Property 15: Rate Limiting Blocks Excessive Requests

For any user or IP address making payment initiation requests,
if more than 10 requests are made within a 60-second window,
subsequent requests should be rejected with HTTP 429 (Too Many Requests)
until the rate limit window resets.

Validates: Requirements 7.7
"""
import pytest
from hypothesis import given, strategies as st, settings, Phase, HealthCheck
from django.test import RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from payments.middleware import PaymentRateLimitMiddleware
from unittest.mock import Mock

User = get_user_model()


@pytest.fixture
def rate_limit_middleware():
    """Create rate limit middleware instance."""
    def get_response(request):
        return Mock(status_code=200)
    
    return PaymentRateLimitMiddleware(get_response)


@pytest.fixture
def request_factory():
    """Create request factory."""
    return RequestFactory()


@pytest.fixture
def test_user(db):
    """Create test user."""
    return User.objects.create_user(
        email='testuser@example.com',
        password='testpass123'
    )


@pytest.mark.django_db
@given(
    num_requests=st.integers(min_value=1, max_value=20)
)
@settings(
    max_examples=100,
    phases=[Phase.generate, Phase.target],
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_rate_limiting_blocks_excessive_user_requests(
    num_requests,
    rate_limit_middleware,
    request_factory,
    test_user
):
    """
    Property 15: Rate Limiting Blocks Excessive Requests (Per-User)
    
    For any number of payment initiation requests from a user,
    if more than 10 requests are made within a 60-second window,
    subsequent requests should be rejected with HTTP 429.
    
    Validates: Requirements 7.7
    """
    # Clear cache before test
    cache.clear()
    
    # Create payment initiation requests
    blocked_count = 0
    allowed_count = 0
    
    for i in range(num_requests):
        # Create POST request to payment initiation endpoint
        request = request_factory.post('/api/v1/payments/initiate/')
        request.user = test_user
        
        # Process request through middleware
        response = rate_limit_middleware(request)
        
        if response.status_code == 429:
            blocked_count += 1
        else:
            allowed_count += 1
    
    # Property: If num_requests <= 10, all should be allowed
    if num_requests <= 10:
        assert allowed_count == num_requests
        assert blocked_count == 0
    
    # Property: If num_requests > 10, exactly 10 should be allowed
    # and the rest should be blocked
    if num_requests > 10:
        assert allowed_count == 10
        assert blocked_count == num_requests - 10
    
    # Clear cache after test
    cache.clear()


@pytest.mark.django_db
@given(
    num_requests=st.integers(min_value=1, max_value=30)
)
@settings(
    max_examples=100,
    phases=[Phase.generate, Phase.target],
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_rate_limiting_blocks_excessive_ip_requests(
    num_requests,
    rate_limit_middleware,
    request_factory
):
    """
    Property 15: Rate Limiting Blocks Excessive Requests (Per-IP)
    
    For any number of payment initiation requests from an IP address,
    if more than 20 requests are made within a 60-second window,
    subsequent requests should be rejected with HTTP 429.
    
    Validates: Requirements 7.7
    """
    # Clear cache before test
    cache.clear()
    
    # Create payment initiation requests from same IP
    blocked_count = 0
    allowed_count = 0
    test_ip = '192.168.1.100'
    
    for i in range(num_requests):
        # Create POST request to payment initiation endpoint
        request = request_factory.post('/api/v1/payments/initiate/')
        request.user = None  # Unauthenticated request
        request.META['REMOTE_ADDR'] = test_ip
        
        # Process request through middleware
        response = rate_limit_middleware(request)
        
        if response.status_code == 429:
            blocked_count += 1
        else:
            allowed_count += 1
    
    # Property: If num_requests <= 20, all should be allowed
    if num_requests <= 20:
        assert allowed_count == num_requests
        assert blocked_count == 0
    
    # Property: If num_requests > 20, exactly 20 should be allowed
    # and the rest should be blocked
    if num_requests > 20:
        assert allowed_count == 20
        assert blocked_count == num_requests - 20
    
    # Clear cache after test
    cache.clear()


@pytest.mark.django_db
@given(
    user_requests=st.integers(min_value=1, max_value=15),
    ip_requests=st.integers(min_value=1, max_value=25)
)
@settings(
    max_examples=50,
    phases=[Phase.generate, Phase.target],
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_rate_limiting_independent_per_user_and_ip(
    user_requests,
    ip_requests,
    rate_limit_middleware,
    request_factory,
    test_user
):
    """
    Property 15: Rate Limiting is Independent for User and IP
    
    User rate limiting and IP rate limiting should be independent.
    A user can be rate limited while their IP is not, and vice versa.
    
    Validates: Requirements 7.7
    """
    # Clear cache before test
    cache.clear()
    
    # Test user requests (should be limited at 10)
    user_blocked = 0
    user_allowed = 0
    
    for i in range(user_requests):
        request = request_factory.post('/api/v1/payments/initiate/')
        request.user = test_user
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        
        response = rate_limit_middleware(request)
        
        if response.status_code == 429:
            user_blocked += 1
        else:
            user_allowed += 1
    
    # Clear user cache but keep IP cache
    cache.delete(f'payment_rate_limit_user_{test_user.id}')
    
    # Test IP requests from different user (should be limited at 20)
    ip_blocked = 0
    ip_allowed = 0
    
    for i in range(ip_requests):
        request = request_factory.post('/api/v1/payments/initiate/')
        request.user = None  # Different/no user
        request.META['REMOTE_ADDR'] = '192.168.1.200'
        
        response = rate_limit_middleware(request)
        
        if response.status_code == 429:
            ip_blocked += 1
        else:
            ip_allowed += 1
    
    # Property: User rate limit is independent of IP rate limit
    # User should be limited at 10
    if user_requests <= 10:
        assert user_allowed == user_requests
        assert user_blocked == 0
    else:
        assert user_allowed == 10
        assert user_blocked == user_requests - 10
    
    # IP should be limited at 20
    if ip_requests <= 20:
        assert ip_allowed == ip_requests
        assert ip_blocked == 0
    else:
        assert ip_allowed == 20
        assert ip_blocked == ip_requests - 20
    
    # Clear cache after test
    cache.clear()


@pytest.mark.django_db
def test_rate_limiting_does_not_apply_to_get_requests(
    rate_limit_middleware,
    request_factory,
    test_user
):
    """
    Property 15: Rate Limiting Does Not Apply to GET Requests
    
    GET requests (status checks, membership fee) should not be rate limited.
    
    Validates: Requirements 7.7
    """
    # Clear cache before test
    cache.clear()
    
    # Make 20 GET requests (more than the limit)
    for i in range(20):
        request = request_factory.get('/api/v1/payments/status/123/')
        request.user = test_user
        
        response = rate_limit_middleware(request)
        
        # All GET requests should be allowed
        assert response.status_code == 200
    
    # Clear cache after test
    cache.clear()


@pytest.mark.django_db
def test_rate_limiting_does_not_apply_to_webhooks(
    rate_limit_middleware,
    request_factory
):
    """
    Property 15: Rate Limiting Does Not Apply to Webhook Endpoints
    
    Webhook endpoints should not be rate limited (external services).
    
    Validates: Requirements 7.7
    """
    # Clear cache before test
    cache.clear()
    
    # Make 20 POST requests to webhook endpoint (more than the limit)
    for i in range(20):
        request = request_factory.post('/api/v1/payments/webhooks/mtn/')
        request.user = None
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        
        response = rate_limit_middleware(request)
        
        # All webhook requests should be allowed
        assert response.status_code == 200
    
    # Clear cache after test
    cache.clear()


@pytest.mark.django_db
@given(
    num_requests=st.integers(min_value=11, max_value=20)
)
@settings(
    max_examples=50,
    phases=[Phase.generate, Phase.target],
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_rate_limiting_returns_retry_after_header(
    num_requests,
    rate_limit_middleware,
    request_factory,
    test_user
):
    """
    Property 15: Rate Limiting Returns Retry-After Information
    
    When rate limit is exceeded, the response should include
    retry_after information indicating when to retry.
    
    Validates: Requirements 7.7
    """
    # Clear cache before test
    cache.clear()
    
    # Make requests until rate limited
    for i in range(num_requests):
        request = request_factory.post('/api/v1/payments/initiate/')
        request.user = test_user
        
        response = rate_limit_middleware(request)
        
        # After 10 requests, should be rate limited
        if i >= 10:
            assert response.status_code == 429
            
            # Check response contains retry_after
            import json
            response_data = json.loads(response.content)
            assert 'error' in response_data
            assert 'retry_after' in response_data['error']
            assert response_data['error']['retry_after'] > 0
            assert response_data['error']['retry_after'] <= 60
    
    # Clear cache after test
    cache.clear()
