#!/usr/bin/env python3
"""
Check admin users and create one if needed
"""
import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from authentication.models import User

def check_admin_users():
    print("Checking admin users...")
    
    # Check for admin users (role='1')
    admin_users = User.objects.filter(role='1')
    print(f"Admin users found: {admin_users.count()}")
    
    if admin_users.exists():
        print("\nAdmin users:")
        for user in admin_users:
            print(f"- Email: {user.email}, Active: {user.is_active}")
    else:
        print("No admin users found. Creating one...")
        
        # Create admin user
        admin_user = User.objects.create_user(
            email='admin@apf.com',
            password='admin123',
            role='1',  # Admin role
            is_staff=True,
            is_superuser=True
        )
        print(f"Created admin user: {admin_user.email}")
    
    # Check all users
    all_users = User.objects.all()
    print(f"\nTotal users: {all_users.count()}")
    print("All users:")
    for user in all_users:
        role_name = 'Admin' if user.role == '1' else 'Member' if user.role == '2' else 'Unknown'
        print(f"- {user.email} - Role: {user.role} ({role_name})")

if __name__ == "__main__":
    check_admin_users()