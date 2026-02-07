#!/usr/bin/env python
"""
Quick setup script for announcements system
Run this after setting up the backend to create initial data
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from django.contrib.auth import get_user_model
from AdminNotifications.models import Announcement

User = get_user_model()

def setup_announcements():
    print("Setting up announcements system...")
    
    # Get or create an admin user
    admin_user = User.objects.filter(role='1').first()
    
    if not admin_user:
        print("No admin user found. Please create an admin user first.")
        return
    
    print(f"Using admin user: {admin_user.email}")
    
    # Create sample announcements
    announcements_data = [
        {
            'title': 'Welcome to the New Announcements System',
            'content': 'We are excited to introduce our new announcements system. You can now create, schedule, and send announcements to different user groups.',
            'audience': 'all_users',
            'channel': 'both',
            'status': 'sent',
            'priority': 'high',
        },
        {
            'title': 'Upcoming System Maintenance',
            'content': 'Our system will undergo scheduled maintenance on the weekend. Please save your work and expect brief interruptions.',
            'audience': 'all_users',
            'channel': 'email',
            'status': 'scheduled',
            'priority': 'medium',
        },
        {
            'title': 'New Member Benefits Available',
            'content': 'We have added new benefits for our members. Check your dashboard to learn more about the exclusive perks.',
            'audience': 'members',
            'channel': 'in_app',
            'status': 'draft',
            'priority': 'low',
        },
    ]
    
    created_count = 0
    for data in announcements_data:
        announcement, created = Announcement.objects.get_or_create(
            title=data['title'],
            defaults={
                **data,
                'created_by': admin_user,
            }
        )
        if created:
            created_count += 1
            print(f"✓ Created: {announcement.title}")
        else:
            print(f"- Already exists: {announcement.title}")
    
    print(f"\nSetup complete! Created {created_count} new announcements.")
    print(f"Total announcements: {Announcement.objects.count()}")

if __name__ == '__main__':
    setup_announcements()
