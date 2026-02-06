#!/usr/bin/env python
"""
Quick setup script for announcements system
Checks everything and helps fix issues
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import connection
from AdminNotifications.models import Announcement

User = get_user_model()

def check_database():
    """Check if database tables exist"""
    print("\n" + "="*60)
    print("1. Checking Database Tables...")
    print("="*60)
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='AdminNotifications_announcement';
            """)
            result = cursor.fetchone()
            
            if result:
                print("✓ AdminNotifications_announcement table exists")
                
                # Check count
                count = Announcement.objects.count()
                print(f"✓ Found {count} announcements in database")
                return True
            else:
                print("✗ AdminNotifications_announcement table NOT found")
                print("\n  FIX: Run migrations:")
                print("  python manage.py migrate AdminNotifications")
                return False
    except Exception as e:
        print(f"✗ Error checking database: {e}")
        return False

def check_admin_user():
    """Check if admin user exists"""
    print("\n" + "="*60)
    print("2. Checking Admin User...")
    print("="*60)
    
    try:
        admin_count = User.objects.filter(role='1').count()
        
        if admin_count > 0:
            admin = User.objects.filter(role='1').first()
            print(f"✓ Found {admin_count} admin user(s)")
            print(f"  Admin email: {admin.email}")
            return True
        else:
            print("✗ No admin user found")
            print("\n  FIX: Create an admin user:")
            print("  python manage.py createsuperuser")
            return False
    except Exception as e:
        print(f"✗ Error checking admin user: {e}")
        return False

def check_installed_apps():
    """Check if AdminNotifications is in INSTALLED_APPS"""
    print("\n" + "="*60)
    print("3. Checking Django Settings...")
    print("="*60)
    
    from django.conf import settings
    
    if 'AdminNotifications' in settings.INSTALLED_APPS:
        print("✓ AdminNotifications is in INSTALLED_APPS")
        return True
    else:
        print("✗ AdminNotifications NOT in INSTALLED_APPS")
        print("\n  FIX: Add to settings.py INSTALLED_APPS:")
        print("  'AdminNotifications',")
        return False

def check_urls():
    """Check if URLs are configured"""
    print("\n" + "="*60)
    print("4. Checking URL Configuration...")
    print("="*60)
    
    try:
        from django.urls import resolve
        from django.urls.exceptions import Resolver404
        
        try:
            resolve('/api/v1/notifications/announcements/')
            print("✓ Announcements URL is configured")
            return True
        except Resolver404:
            print("✗ Announcements URL NOT configured")
            print("\n  FIX: Add to api/urls.py:")
            print('  path("api/v1/notifications/", include("AdminNotifications.urls")),')
            return False
    except Exception as e:
        print(f"✗ Error checking URLs: {e}")
        return False

def create_sample_data():
    """Create sample announcements"""
    print("\n" + "="*60)
    print("5. Creating Sample Data...")
    print("="*60)
    
    try:
        admin_user = User.objects.filter(role='1').first()
        
        if not admin_user:
            print("✗ Cannot create sample data: No admin user found")
            return False
        
        # Check if sample data already exists
        if Announcement.objects.filter(title__contains='Welcome to the New Announcements System').exists():
            print("✓ Sample data already exists")
            return True
        
        # Create sample announcements
        announcements = [
            {
                'title': 'Welcome to the New Announcements System',
                'content': 'We are excited to introduce our new announcements system.',
                'audience': 'all_users',
                'channel': 'both',
                'status': 'sent',
                'priority': 'high',
            },
            {
                'title': 'Upcoming System Maintenance',
                'content': 'Our system will undergo scheduled maintenance this weekend.',
                'audience': 'all_users',
                'channel': 'email',
                'status': 'scheduled',
                'priority': 'medium',
            },
            {
                'title': 'New Member Benefits',
                'content': 'Check out the new benefits available to members.',
                'audience': 'members',
                'channel': 'in_app',
                'status': 'draft',
                'priority': 'low',
            },
        ]
        
        created = 0
        for data in announcements:
            Announcement.objects.create(
                **data,
                created_by=admin_user
            )
            created += 1
        
        print(f"✓ Created {created} sample announcements")
        return True
        
    except Exception as e:
        print(f"✗ Error creating sample data: {e}")
        return False

def test_api():
    """Test if API is accessible"""
    print("\n" + "="*60)
    print("6. Testing API Endpoints...")
    print("="*60)
    
    try:
        from django.test import Client
        
        client = Client()
        
        # Test stats endpoint (should require auth)
        response = client.get('/api/v1/notifications/announcements/stats/')
        
        if response.status_code in [200, 401, 403]:
            print("✓ API endpoint is accessible")
            print(f"  Status code: {response.status_code}")
            if response.status_code == 401:
                print("  (401 is expected - authentication required)")
            return True
        else:
            print(f"✗ API endpoint returned unexpected status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing API: {e}")
        return False

def main():
    """Run all checks"""
    print("\n" + "="*60)
    print("ANNOUNCEMENTS SYSTEM - QUICK SETUP")
    print("="*60)
    
    results = []
    
    # Run checks
    results.append(("Database Tables", check_database()))
    results.append(("Admin User", check_admin_user()))
    results.append(("Django Settings", check_installed_apps()))
    results.append(("URL Configuration", check_urls()))
    
    # Only create sample data if previous checks passed
    if all(r[1] for r in results):
        results.append(("Sample Data", create_sample_data()))
        results.append(("API Endpoints", test_api()))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n" + "="*60)
        print("✓ ALL CHECKS PASSED!")
        print("="*60)
        print("\nYour announcements system is ready to use!")
        print("\nNext steps:")
        print("1. Start the server: python manage.py runserver")
        print("2. Start the frontend: cd ../../portal && npm run dev")
        print("3. Login as admin and go to /admin/announcements")
    else:
        print("\n" + "="*60)
        print("✗ SOME CHECKS FAILED")
        print("="*60)
        print("\nPlease fix the issues above and run this script again.")
        print("\nCommon fixes:")
        print("1. Run migrations: python manage.py migrate AdminNotifications")
        print("2. Create admin user: python manage.py createsuperuser")
        print("3. Check settings.py and urls.py configuration")
    
    print("\n" + "="*60)
    print("For more help, see: ANNOUNCEMENTS_TROUBLESHOOTING.md")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()
