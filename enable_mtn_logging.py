#!/usr/bin/env python
"""
Enable detailed HTTP logging for MTN API requests.
This script patches the requests library to log all HTTP traffic.

Usage:
    # In your Django shell or script:
    import enable_mtn_logging
    enable_mtn_logging.enable()
    
    # Now all MTN API requests will be logged
    from payments.services.mtn_service import MTNService
    service = MTNService()
    service._get_access_token()  # You'll see the HTTP request/response
"""
import logging
import http.client as http_client

def enable(level=logging.DEBUG):
    """
    Enable detailed HTTP logging.
    
    Args:
        level: Logging level (default: logging.DEBUG)
    """
    # Enable HTTP connection debugging
    http_client.HTTPConnection.debuglevel = 1
    
    # Configure logging
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Enable requests library logging
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(level)
    requests_log.propagate = True
    
    # Enable urllib3 logging
    urllib3_log = logging.getLogger("urllib3")
    urllib3_log.setLevel(level)
    urllib3_log.propagate = True
    
    # Enable payments logging
    payments_log = logging.getLogger("payments")
    payments_log.setLevel(level)
    payments_log.propagate = True
    
    print("✓ HTTP logging enabled!")
    print("  All MTN API requests will now be logged with full details")
    print("  You will see:")
    print("    - Request URLs")
    print("    - Request headers")
    print("    - Request body")
    print("    - Response status")
    print("    - Response headers")
    print("    - Response body")
    print()

def disable():
    """Disable HTTP logging."""
    http_client.HTTPConnection.debuglevel = 0
    logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    print("✓ HTTP logging disabled")

# Example usage
if __name__ == '__main__':
    import os
    import django
    
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
    django.setup()
    
    # Enable logging
    enable()
    
    # Test MTN API
    from payments.services.mtn_service import MTNService
    
    print("=" * 70)
    print("Testing MTN API with detailed logging enabled")
    print("=" * 70)
    print()
    
    service = MTNService()
    
    print("1. Getting access token...")
    print("-" * 70)
    try:
        token = service._get_access_token(force_refresh=True)
        print(f"\n✓ Token obtained: {token[:30]}...")
    except Exception as e:
        print(f"\n✗ Error: {e}")
    
    print("\n" + "=" * 70)
    print("Logging test complete!")
    print("=" * 70)
    print("\nYou should see detailed HTTP logs above showing:")
    print("  - The exact URL being called")
    print("  - All request headers")
    print("  - The response from MTN's server")
    print("\nThis confirms your app is hitting MTN's API!")
