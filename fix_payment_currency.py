"""
Script to update all existing payments to use UGX currency
Run this once to fix any payments that have incorrect currency
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from payments.models import Payment

def fix_payment_currency():
    """Update all payments to use UGX currency"""
    
    # Get all payments
    payments = Payment.objects.all()
    total_count = payments.count()
    
    if total_count == 0:
        print("No payments found in database")
        return
    
    print(f"Found {total_count} payments")
    
    # Update payments with non-UGX currency
    non_ugx_payments = payments.exclude(currency='UGX')
    non_ugx_count = non_ugx_payments.count()
    
    if non_ugx_count == 0:
        print("All payments already use UGX currency")
        return
    
    print(f"Updating {non_ugx_count} payments to UGX currency...")
    
    # Update in bulk
    updated = non_ugx_payments.update(currency='UGX')
    
    print(f"✓ Successfully updated {updated} payments to UGX")
    
    # Verify
    ugx_count = Payment.objects.filter(currency='UGX').count()
    print(f"✓ Total payments with UGX: {ugx_count}/{total_count}")

if __name__ == '__main__':
    try:
        fix_payment_currency()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
