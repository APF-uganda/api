#!/usr/bin/env python
"""
Script to list all payment records in the database.

Usage:
    python list_payments.py
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


def list_payments():
    """List all payment records in the database."""
    
    print("\n" + "="*60)
    print("PAYMENT RECORDS IN DATABASE")
    print("="*60 + "\n")
    
    # Count payments
    payment_count = Payment.objects.count()
    
    if payment_count == 0:
        print("✓ No payment records found in database")
        print("\nThe database is clean - no test data!")
        return
    
    print(f"Total Payment Records: {payment_count}\n")
    
    # Group by status
    statuses = Payment.objects.values_list('status', flat=True).distinct()
    for status in statuses:
        count = Payment.objects.filter(status=status).count()
        print(f"  • {status.upper()}: {count}")
    
    print("\n" + "-"*60)
    print("DETAILED PAYMENT LIST")
    print("-"*60 + "\n")
    
    # List all payments
    for idx, payment in enumerate(Payment.objects.all().order_by('-created_at'), 1):
        user_email = payment.user.email if payment.user else "No user"
        
        print(f"{idx}. Transaction: {payment.transaction_reference}")
        print(f"   User: {user_email}")
        print(f"   Amount: {payment.amount} {payment.currency}")
        print(f"   Status: {payment.status}")
        print(f"   Provider: {payment.provider.upper()}")
        print(f"   Phone: {payment.phone_number}")
        print(f"   Created: {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if payment.completed_at:
            print(f"   Completed: {payment.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if payment.error_message:
            print(f"   Error: {payment.error_message}")
        
        print()
    
    print("-"*60)
    print(f"\nTotal: {payment_count} payment record(s)")
    print("\nTo clear test data, run: python clear_test_payments.py")


if __name__ == '__main__':
    try:
        list_payments()
    except KeyboardInterrupt:
        print("\n\n✗ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        sys.exit(1)
