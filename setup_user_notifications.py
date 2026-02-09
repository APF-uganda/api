"""
Script to set up UserNotification model and test announcement functionality
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from django.contrib.auth import get_user_model
from AdminNotifications.models import Announcement
from notifications.models import UserNotification

User = get_user_model()

def main():
    print("=" * 60)
    print("Setting up UserNotification Model")
    print("=" * 60)
    
    # Check if migrations are needed
    print("\n1. Checking database status...")
    try:
        count = UserNotification.objects.count()
        print(f"✓ UserNotification table exists with {count} records")
    except Exception as e:
        print(f"✗ UserNotification table not found: {e}")
        print("\nPlease run migrations:")
        print("  python manage.py makemigrations")
        print("  python manage.py migrate")
        return
    
    # Check users
    print("\n2. Checking users...")
    total_users = User.objects.count()
    members = User.objects.filter(role='2').count()
    admins = User.objects.filter(role='1').count()
    print(f"  Total users: {total_users}")
    print(f"  Members: {members}")
    print(f"  Admins: {admins}")
    
    # Check announcements
    print("\n3. Checking announcements...")
    total_announcements = Announcement.objects.count()
    sent_announcements = Announcement.objects.filter(status='sent').count()
    print(f"  Total announcements: {total_announcements}")
    print(f"  Sent announcements: {sent_announcements}")
    
    # Test creating a notification
    print("\n4. Testing notification creation...")
    admin_user = User.objects.filter(role='1').first()
    if not admin_user:
        print("✗ No admin user found")
        return
    
    test_notification = UserNotification.objects.create(
        user=admin_user,
        title="Test Notification",
        message="This is a test notification to verify the system is working.",
        notification_type='system',
        priority='medium'
    )
    print(f"✓ Created test notification: {test_notification.id}")
    
    # Clean up test notification
    test_notification.delete()
    print("✓ Cleaned up test notification")
    
    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Create an announcement from the admin panel")
    print("2. Set channel to 'In-App' or 'Both'")
    print("3. Send the announcement")
    print("4. Check user notifications in the database or API")
    print("\nAPI Endpoints:")
    print("  GET  /api/v1/notifications/user-notifications/")
    print("  GET  /api/v1/notifications/user-notifications/unread_count/")
    print("  POST /api/v1/notifications/user-notifications/{id}/mark_read/")
    print("  POST /api/v1/notifications/user-notifications/mark_all_read/")

if __name__ == '__main__':
    main()
