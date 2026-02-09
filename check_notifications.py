"""
Check if notifications were created
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from notifications.models import UserNotification
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 60)
print("Checking Notifications")
print("=" * 60)

total_notifications = UserNotification.objects.count()
print(f"\nTotal notifications: {total_notifications}")

total_users = User.objects.count()
print(f"Total users: {total_users}")

if total_notifications > 0:
    print("\nSample notifications:")
    for n in UserNotification.objects.all()[:10]:
        print(f"  - {n.user.email}: {n.title} (read: {n.is_read})")
    
    print("\nNotifications by user:")
    for user in User.objects.all()[:5]:
        count = UserNotification.objects.filter(user=user).count()
        print(f"  {user.email}: {count} notifications")
else:
    print("\n⚠️  No notifications found!")
    print("\nTo create a test notification:")
    print("1. Go to /admin/announcements")
    print("2. Create announcement with channel='in_app' or 'both'")
    print("3. Click 'Send Now'")
