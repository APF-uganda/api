"""
Quick test to verify profile updates are saving to database.
Run with: python quick_test_save.py (with venv activated)
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from profiles.models import UserProfile
from authentication.models import User
from django.db import connection

def test_save():
    print("\n" + "=" * 70)
    print("QUICK PROFILE SAVE TEST")
    print("=" * 70 + "\n")
    
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("✓ Database connection OK\n")
        
        # Get first admin user
        admin = User.objects.filter(role='1').first()
        if not admin:
            print("❌ No admin user found")
            return
        
        print(f"Testing with: {admin.email}\n")
        
        # Get or create profile
        profile, created = UserProfile.objects.get_or_create(user=admin)
        
        print("BEFORE UPDATE:")
        print(f"  first_name: '{profile.first_name}'")
        print(f"  last_name: '{profile.last_name}'")
        print(f"  phone_number: '{profile.phone_number}'")
        print()
        
        # Try to update
        print("Updating profile...")
        profile.first_name = "TestFirstName"
        profile.last_name = "TestLastName"
        profile.phone_number = "+256770999888"
        profile.save()
        print("✓ Save called\n")
        
        # Check if it saved
        print("AFTER SAVE (same instance):")
        print(f"  first_name: '{profile.first_name}'")
        print(f"  last_name: '{profile.last_name}'")
        print(f"  phone_number: '{profile.phone_number}'")
        print()
        
        # Get fresh from database
        fresh = UserProfile.objects.get(user=admin)
        print("FRESH FROM DATABASE:")
        print(f"  first_name: '{fresh.first_name}'")
        print(f"  last_name: '{fresh.last_name}'")
        print(f"  phone_number: '{fresh.phone_number}'")
        print()
        
        # Verify
        if (fresh.first_name == "TestFirstName" and 
            fresh.last_name == "TestLastName" and
            fresh.phone_number == "+256770999888"):
            print("✅ SUCCESS! Data saved to database correctly")
        else:
            print("❌ FAILED! Data did not save")
            print(f"   Expected: TestFirstName, TestLastName, +256770999888")
            print(f"   Got: {fresh.first_name}, {fresh.last_name}, {fresh.phone_number}")
        
        print("\n" + "=" * 70 + "\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_save()
