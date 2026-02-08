"""
Manual test script for MTN sandbox.
Run this to test MTN sandbox API directly.
"""
import os
import sys
import uuid
import django
from pathlib import Path
from decimal import Decimal

# Setup Django
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from payments.services.mtn_service import MTNService


def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def print_success(text):
    print(f"✓ {text}")


def print_error(text):
    print(f"✗ {text}")


def print_info(text):
    print(f"ℹ {text}")


def test_authentication():
    """Test MTN authentication."""
    print_header("Test 1: Authentication")
    
    try:
        mtn = MTNService()
        token = mtn._get_access_token()
        
        if token:
            print_success("Authentication successful")
            print_info(f"Token: {token[:30]}...")
            return True
        else:
            print_error("Failed to get token")
            return False
    except Exception as e:
        print_error(f"Authentication failed: {e}")
        return False


def test_payment_initiation():
    """Test payment initiation."""
    print_header("Test 2: Payment Initiation")
    
    try:
        mtn = MTNService()
        reference = str(uuid.uuid4())
        
        print_info(f"Transaction Reference: {reference}")
        print_info("Phone Number: 256774000001 (sandbox test number)")
        print_info("Amount: 5000 UGX")
        
        result = mtn.request_to_pay(
            phone_number="256774000001",
            amount=Decimal("5000"),
            currency="UGX",
            reference=reference,
            payer_message="Test Payment"
        )
        
        print(f"\nResult: {result}")
        
        if result['success']:
            print_success("Payment initiated successfully")
            return reference
        else:
            print_error(f"Payment initiation failed: {result.get('message')}")
            return None
    except Exception as e:
        print_error(f"Payment initiation error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_payment_status(reference):
    """Test payment status check."""
    print_header("Test 3: Payment Status Check")
    
    if not reference:
        print_error("No reference to check")
        return False
    
    try:
        mtn = MTNService()
        
        print_info(f"Checking status for: {reference}")
        
        result = mtn.check_payment_status(reference)
        
        print(f"\nResult: {result}")
        
        if result['success']:
            print_success(f"Status check successful: {result['status']}")
            return True
        else:
            print_error(f"Status check failed: {result.get('message')}")
            return False
    except Exception as e:
        print_error(f"Status check error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print_header("MTN Sandbox Manual Testing")
    
    print("This script tests MTN sandbox API directly.")
    print("Make sure your .env file has MTN credentials configured.")
    
    input("\nPress Enter to start testing...")
    
    # Test 1: Authentication
    if not test_authentication():
        print("\n❌ Authentication failed. Cannot proceed.")
        return
    
    # Test 2: Payment Initiation
    reference = test_payment_initiation()
    
    if reference:
        # Test 3: Payment Status
        import time
        print("\nWaiting 3 seconds before checking status...")
        time.sleep(3)
        test_payment_status(reference)
    
    print_header("Testing Complete")
    
    print("\nNotes:")
    print("- MTN sandbox may have limitations")
    print("- Some test numbers may not work as expected")
    print("- Currency issues are common in sandbox")
    print("- Check MTN Developer Portal for latest sandbox status")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTesting cancelled by user.")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
