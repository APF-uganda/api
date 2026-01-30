#!/usr/bin/env python3
"""
Create test data for applications
"""
import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from applications.models import Application
from authentication.models import User

def create_test_applications():
    print("Creating test applications...")
    
    # Create some test applications
    test_apps = [
        {
            'username': 'john_doe',
            'email': 'john.doe@example.com',
            'password_hash': 'hashed_password_123',
            'first_name': 'John',
            'last_name': 'Doe',
            'age_range': '25 – 34',
            'phone_number': '+256700123456',
            'address': '123 Main St, Kampala',
            'national_id_number': 'CM12345678901234',
            'icpau_certificate_number': 'ICPAU001',
            'payment_method': 'mtn',
            'payment_phone': '+256700123456',
            'payment_status': 'success',
            'status': 'pending'
        },
        {
            'username': 'jane_smith',
            'email': 'jane.smith@example.com',
            'password_hash': 'hashed_password_456',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'age_range': '35 – 44',
            'phone_number': '+256700654321',
            'address': '456 Oak Ave, Entebbe',
            'national_id_number': 'CM98765432109876',
            'icpau_certificate_number': 'ICPAU002',
            'payment_method': 'airtel',
            'payment_phone': '+256700654321',
            'payment_status': 'success',
            'status': 'approved'
        },
        {
            'username': 'bob_wilson',
            'email': 'bob.wilson@example.com',
            'password_hash': 'hashed_password_789',
            'first_name': 'Bob',
            'last_name': 'Wilson',
            'age_range': '45 – 54',
            'phone_number': '+256700987654',
            'address': '789 Pine Rd, Jinja',
            'national_id_number': 'CM11223344556677',
            'icpau_certificate_number': 'ICPAU003',
            'payment_method': 'credit_card',
            'payment_status': 'pending',
            'status': 'pending'
        }
    ]
    
    created_count = 0
    for app_data in test_apps:
        # Check if application already exists
        if not Application.objects.filter(email=app_data['email']).exists():
            Application.objects.create(**app_data)
            created_count += 1
            print(f"Created application for {app_data['first_name']} {app_data['last_name']}")
        else:
            print(f"Application for {app_data['email']} already exists")
    
    print(f"\nCreated {created_count} new applications")
    
    # Show total count
    total_apps = Application.objects.count()
    print(f"Total applications in database: {total_apps}")
    
    # List all applications
    print("\nAll applications:")
    for app in Application.objects.all():
        print(f"- {app.first_name} {app.last_name} ({app.email}) - Status: {app.status}")

if __name__ == "__main__":
    create_test_applications()