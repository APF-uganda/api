#!/usr/bin/env python
"""
Diagnostic script to find why revenue isn't showing correctly.
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from applications.models import Application
from dashboard.services import get_application_statistics
import json


def main():
    print("\n" + "="*70)
    print("REVENUE DISPLAY DIAGNOSTIC")
    print("="*70)
    
    # Step 1: Check database field
    print("\n1. CHECKING DATABASE FIELD...")
    try:
        app = Application.objects.first()
        if app:
            if hasattr(app, 'payment_amount'):
                print(f"   ✅ payment_amount field EXISTS")
                print(f"   Sample value: {app.payment_amount}")
            else:
                print(f"   ❌ payment_amount field MISSING")
                print(f"   → Run: python manage.py migrate")
                return
        else:
            print(f"   ⚠️  No applications in database")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Step 2: Check paid applications
    print("\n2. CHECKING PAID APPLICATIONS...")
    paid_apps = Application.objects.filter(payment_status='success')
    paid_count = paid_apps.count()
    print(f"   Applications with payment_status='success': {paid_count}")
    
    if paid_count == 0:
        print(f"   ⚠️  No paid applications found!")
        print(f"   → Check payment_status field values")
        
        # Show all payment statuses
        from django.db.models import Count
        statuses = Application.objects.values('payment_status').annotate(count=Count('id'))
        print(f"\n   Current payment_status distribution:")
        for status in statuses:
            print(f"      {status['payment_status']}: {status['count']}")
        return
    
    # Step 3: Check payment amounts
    print("\n3. CHECKING PAYMENT AMOUNTS...")
    amounts = [float(app.payment_amount) for app in paid_apps[:5]]
    print(f"   Sample payment amounts: {amounts}")
    
    total = sum(float(app.payment_amount) for app in paid_apps)
    print(f"   Total from {paid_count} paid apps: UGX {total:,.2f}")
    
    if total == 0:
        print(f"   ❌ All payment amounts are 0!")
        print(f"   → Run: python update_payment_stats.py")
        return
    
    # Step 4: Check API response
    print("\n4. CHECKING API RESPONSE...")
    try:
        stats = get_application_statistics()
        print(f"   API Response:")
        print(f"      paid_applications: {stats.get('paid_applications', 'MISSING')}")
        print(f"      total_revenue: {stats.get('total_revenue', 'MISSING')}")
        
        if 'total_revenue' not in stats:
            print(f"   ❌ total_revenue field MISSING from API")
            print(f"   → Check dashboard/services.py")
            return
        
        revenue = stats['total_revenue']
        print(f"   ✅ Revenue in API: UGX {revenue:,.2f}")
        
    except Exception as e:
        print(f"   ❌ Error calling API: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 5: Check formatting
    print("\n5. CHECKING FRONTEND FORMATTING...")
    
    def format_ugx(amount):
        if amount >= 1_000_000_000:
            return f"UGX {amount/1_000_000_000:.2f}B"
        elif amount >= 1_000_000:
            return f"UGX {amount/1_000_000:.2f}M"
        elif amount >= 1_000:
            return f"UGX {amount/1_000:.2f}K"
        return f"UGX {amount:,.2f}"
    
    formatted = format_ugx(revenue)
    print(f"   Dashboard should show: {formatted}")
    
    # Step 6: Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"✅ Database field exists: payment_amount")
    print(f"✅ Paid applications: {paid_count}")
    print(f"✅ Total revenue: UGX {revenue:,.2f}")
    print(f"✅ Formatted display: {formatted}")
    print(f"\n📱 Your dashboard should show: {formatted}")
    
    # Step 7: Test API endpoint
    print("\n" + "="*70)
    print("API ENDPOINT TEST")
    print("="*70)
    print(f"Test with:")
    print(f"  curl http://localhost:8000/api/v1/statistics/")
    print(f"\nExpected response should include:")
    print(json.dumps({
        "paid_applications": paid_count,
        "total_revenue": revenue,
        "trends": {
            "revenue_change": "..."
        }
    }, indent=2))
    
    # Step 8: Frontend check
    print("\n" + "="*70)
    print("FRONTEND CHECKLIST")
    print("="*70)
    print("1. ✓ Backend is returning total_revenue")
    print("2. ? Frontend is receiving the data")
    print("3. ? Frontend is formatting correctly")
    print("\nTo debug frontend:")
    print("1. Open browser console (F12)")
    print("2. Go to Network tab")
    print("3. Refresh dashboard")
    print("4. Look for request to /api/v1/statistics/")
    print("5. Check if response includes 'total_revenue'")
    print("6. Check browser console for any errors")
    
    print("\n" + "="*70)
    print("If dashboard still shows '24' instead of revenue:")
    print("="*70)
    print("1. Clear browser cache (Ctrl+Shift+Delete)")
    print("2. Hard refresh (Ctrl+Shift+R)")
    print("3. Check browser console for errors")
    print("4. Verify API response in Network tab")
    print("5. Make sure Django server was restarted")
    print("\n")


if __name__ == '__main__':
    main()
