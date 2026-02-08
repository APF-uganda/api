"""
Verification script for MTN MoMo sandbox credentials.
Checks that all required environment variables are set and tests authentication.
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from payments.services.mtn_service import MTNService, MTNConfig


def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def print_success(text):
    """Print success message."""
    print(f"✓ {text}")


def print_error(text):
    """Print error message."""
    print(f"✗ {text}")


def print_info(text):
    """Print info message."""
    print(f"ℹ {text}")


def verify_environment_variables():
    """Verify all required environment variables are set."""
    print("Checking environment variables...")
    
    required_vars = {
        'PAYMENT_ENVIRONMENT': os.getenv('PAYMENT_ENVIRONMENT'),
        'MTN_SUBSCRIPTION_KEY': os.getenv('MTN_SUBSCRIPTION_KEY'),
        'MTN_API_USER': os.getenv('MTN_API_USER'),
        'MTN_API_KEY': os.getenv('MTN_API_KEY'),
    }
    
    all_set = True
    for var_name, var_value in required_vars.items():
        if var_value:
            print_success(f"{var_name} is set")
        else:
            print_error(f"{var_name} is NOT set")
            all_set = False
    
    return all_set


def verify_sandbox_environment():
    """Verify sandbox environment is active."""
    print("\nChecking sandbox environment...")
    
    env = os.getenv('PAYMENT_ENVIRONMENT', 'sandbox')
    if env == 'sandbox':
        print_success("Sandbox environment is active")
        return True
    else:
        print_error(f"Environment is set to '{env}' (expected 'sandbox')")
        return False


def verify_mtn_config():
    """Verify MTN configuration."""
    print("\nChecking MTN configuration...")
    
    try:
        config = MTNConfig()
        
        if config.is_configured():
            print_success("MTN configuration is complete")
            print_info(f"Base URL: {config.base_url}")
            print_info(f"Target Environment: {config.target_environment}")
            print_info(f"API User: {config.api_user[:8]}...")
            return True
        else:
            print_error("MTN configuration is incomplete")
            return False
    except Exception as e:
        print_error(f"Error checking MTN configuration: {e}")
        return False


def test_mtn_authentication():
    """Test MTN authentication."""
    print("\nTesting MTN authentication...")
    
    try:
        mtn = MTNService()
        token = mtn._get_access_token()
        
        if token:
            print_success("MTN authentication successful")
            print_info(f"Access Token: {token[:30]}...")
            return True
        else:
            print_error("Failed to get access token")
            return False
    except Exception as e:
        print_error(f"Authentication failed: {e}")
        return False


def main():
    """Run all verification checks."""
    print_header("MTN MoMo Sandbox Verification")
    
    results = []
    
    # Check environment variables
    results.append(verify_environment_variables())
    
    # Check sandbox environment
    results.append(verify_sandbox_environment())
    
    # Check MTN configuration
    results.append(verify_mtn_config())
    
    # Test authentication
    results.append(test_mtn_authentication())
    
    # Summary
    print_header("Verification Summary")
    
    if all(results):
        print_success("All checks passed! MTN sandbox is ready for testing.")
        print("\nNext steps:")
        print("  1. Run sandbox tests: pytest Backend/payments/tests/sandbox/")
        print("  2. Test manually: python manage.py shell")
        print("  3. See guide: Backend/MTN_SANDBOX_TESTING_GUIDE.md")
        return 0
    else:
        print_error("Some checks failed. Please fix the issues above.")
        print("\nFor help, see:")
        print("  - Backend/MTN_SETUP_QUICK_START.md")
        print("  - Backend/MTN_SANDBOX_TESTING_GUIDE.md")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nVerification cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
