"""
Quick script to check if UserNotifications exist in the database
Run with: python manage.py shell < check_notifications.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from django.contrib.auth import get_user_model
from notifications.models import UserNotification

User = get_user_model()

print("\n" + "="*60)
print("CHECKING USER NOTIFICATIONS")
print("="*60 + "\n")

# Get all UserNotifications
all_notifications = UserNotification.objects.all()
print(f"Total UserNotifications in database: {all_notifications.count()}")

if all_notifications.count() == 0:
    print("\n❌ NO NOTIFICATIONS FOUND!")
    print("This means admin hasn't sent any announcements yet.")
    print("\nTo fix:")
    print("1. Login as admin")
    print("2. Go to Admin Notifications")
    print("3. Create an announcement")
    print("4. Set audience to 'Members'")
    print("5. Set status to 'Sent'")
else:
    print("\n✅ Notifications found!\n")
    
    # Show sample notifications
    print("Sample notifications:")
    for notif in all_notifications[:5]:
        print(f"\n  ID: {notif.id}")
        print(f"  User: {notif.user.email}")
        print(f"  Title: {notif.title}")
        print(f"  Type: {notif.notification_type}")
        print(f"  Read: {notif.is_read}")
        print(f"  Created: {notif.created_at}")
    
    # Check member users
    members = User.objects.filter(role='2')
    print(f"\n\nTotal members: {members.count()}")
    
    if members.count() > 0:
        test_member = members.first()
        member_notifs = UserNotification.objects.filter(user=test_member)
        print(f"\nNotifications for {test_member.email}: {member_notifs.count()}")
        
        if member_notifs.count() == 0:
            print("❌ This member has no notifications!")
        else:
            print("✅ This member has notifications")

print("\n" + "="*60 + "\n")
