"""
Pytest configuration for authentication tests
"""

import pytest
from django.conf import settings


@pytest.fixture(scope='session', autouse=True)
def configure_test_cache():
    """Configure cache to use fakeredis for testing"""
    import fakeredis
    from django.core.cache import cache
    
    # Override the cache backend with fakeredis
    settings.CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }
    
    # Clear cache before tests
    cache.clear()
    
    yield
    
    # Clear cache after tests
    cache.clear()


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test"""
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def responses():
    """Fixture for mocking HTTP requests using responses library"""
    import responses as responses_lib
    with responses_lib.RequestsMock() as rsps:
        yield rsps
