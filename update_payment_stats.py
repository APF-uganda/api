#!/usr/bin/env python
"""
Script to update payment statistics system with actual revenue tracking.
This script helps migrate existing data and test the new payment amount field.
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from applications.models import Application
from decimal import Decimal


def update_existing_payments():
    """Update existing applications with default payment amount if not set."""
    print("Updating existing applications with payment amounts...")
    
    # Get all applications without payment amount or with 0 amount
    applications = Application.objects.all()
    updated_count = 0
    
    for app in applications:
        # Set default amount if not already set
        if not hasattr(app, 'payment_amount') or app.payment_amount == 0:
            app.payment_amount = Decimal('50000.00')
            app.save(update_fields=['payment_amount'])
            updated_count += 1
    
    print(f"✓ Updated {updated_count} applications with default payment amount (50,000 UGX)")


def display_revenue_stats():
    """Display current revenue statistics."""
    from dashboard.services import get_application_statistics
    
    print("\n" + "="*60)
    print("PAYMENT STATISTICS SUMMARY")
    print("="*60)
    
    stats = get_application_statistics()
    
    print(f"\nApplications:")
    print(f"  Total: {stats['total_applications']}")
    print(f"  Pending: {stats['pending_applications']}")
    print(f"  Approved: {stats['approved_applications']}")
    print(f"  Rejected: {stats['rejected_applications']}")
    print(f"  Paid: {stats['paid_applications']}")
    
    print(f"\nRevenue:")
    total_revenue = stats['total_revenue']
    print(f"  Total Revenue: UGX {total_revenue:,.2f}")
    
    if total_revenue >= 1_000_000_000:
        print(f"  Formatted: UGX {total_revenue/1_000_000_000:.2f}B")
    elif total_revenue >= 1_000_000:
        print(f"  Formatted: UGX {total_revenue/1_000_000:.2f}M")
    elif total_revenue >= 1_000:
        print(f"  Formatted: UGX {total_revenue/1_000:.2f}K")
    
    print(f"\nTrends (vs last month):")
    print(f"  Total Applications: {stats['trends']['total_change']:+.1f}%")
    print(f"  Approved: {stats['trends']['approved_change']:+.1f}%")
    print(f"  Paid: {stats['trends']['paid_change']:+.1f}%")
    print(f"  Revenue: {stats['trends']['revenue_change']:+.1f}%")
    
    print("\n" + "="*60)


def test_payment_scenarios():
    """Test different payment scenarios."""
    print("\n" + "="*60)
    print("TESTING PAYMENT SCENARIOS")
    print("="*60)
    
    # Test formatting function
    def format_ugx(amount):
        if amount >= 1_000_000_000:
            return f"UGX {amount/1_000_000_000:.2f}B"
        elif amount >= 1_000_000:
            return f"UGX {amount/1_000_000:.2f}M"
        elif amount >= 1_000:
            return f"UGX {amount/1_000:.2f}K"
        return f"UGX {amount:,.2f}"
    
    test_amounts = [
        50000,
        1200000,  # 24 paid applications
        5000000,
        50000000,
        500000000,
    ]
    
    print("\nAmount Formatting Tests:")
    for amount in test_amounts:
        print(f"  {amount:>12,} → {format_ugx(amount)}")
    
    print("\n" + "="*60)


def main():
    """Main execution function."""
    print("\n🚀 Payment Statistics Update Script")
    print("="*60)
    
    try:
        # Step 1: Update existing data
        update_existing_payments()
        
        # Step 2: Display current stats
        display_revenue_stats()
        
        # Step 3: Test scenarios
        test_payment_scenarios()
        
        print("\n✅ Payment statistics system updated successfully!")
        print("\nNext steps:")
        print("1. Run migrations: python manage.py migrate")
        print("2. Restart your Django server")
        print("3. Refresh the admin dashboard to see exact revenue amounts")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
