#!/usr/bin/env python
"""
Script to clear test payment data from the database.
This will remove all payment records, allowing you to start fresh.

Usage:
    python clear_test_payments.py
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from payments.models import Payment
from django.contrib.auth import get_user_model

User = get_user_model()


def clear_test_payments():
    """Clear all test payment data from the database."""
    
    print("\n" + "="*60)
    print("CLEAR TEST PAYMENT DATA")
    print("="*60 + "\n")
    
    # Count existing payments
    payment_count = Payment.objects.count()
    
    if payment_count == 0:
        print("✓ No payment records found in database")
        print("\nDatabase is already clean!")
        return
    
    print(f"Found {payment_count} payment record(s) in database\n")
    
    # Show payment details
    print("Payment Records:")
    print("-" * 60)
    for payment in Payment.objects.all().order_by('-created_at'):
        user_email = payment.user.email if payment.user else "No user"
        print(f"  • {payment.transaction_reference}")
        print(f"    User: {user_email}")
        print(f"    Amount: {payment.amount} {payment.currency}")
        print(f"    Status: {payment.status}")
        print(f"    Provider: {payment.provider}")
        print(f"    Created: {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    # Confirm deletion
    print("-" * 60)
    response = input(f"\nDo you want to delete all {payment_count} payment record(s)? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("\n✗ Operation cancelled")
        return
    
    # Delete all payments
    try:
        deleted_count, _ = Payment.objects.all().delete()
        print(f"\n✓ Successfully deleted {deleted_count} payment record(s)")
        print("\nDatabase is now clean!")
        print("\nNote: Payment configuration (membership fee) was preserved.")
        
    except Exception as e:
        print(f"\n✗ Error deleting payments: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    try:
        clear_test_payments()
    except KeyboardInterrupt:
        print("\n\n✗ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}")
        sys.exit(1)
