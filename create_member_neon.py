import os
import django

# Force Neon database connection
os.environ['DB_NAME'] = 'neondb'
os.environ['DB_USER'] = 'neondb_owner'
os.environ['DB_PASSWORD'] = 'npg_7QbEFVciI3xB'
os.environ['DB_HOST'] = 'ep-dry-frog-ah8roofk-pooler.c-3.us-east-1.aws.neon.tech'
os.environ['DB_PORT'] = '5432'

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from authentication.models import User, UserRole
from django.db import connection

print("Database Connection:")
print(f"  Name: {connection.settings_dict['NAME']}")
print(f"  Host: {connection.settings_dict['HOST']}")
print()

# Check if user exists
email = 'kikomekobashir29@gmail.com'
user = User.objects.filter(email=email).first()

if user:
    print(f"User already exists: {email}")
    print("Resetting password...")
    user.set_password('member123')
    user.save()
    print("✅ Password reset successfully")
else:
    print(f"Creating new user: {email}")
    user = User.objects.create_user(
        email=email,
        password='member123',
        role=UserRole.MEMBER
    )
    print(f"✅ User created successfully")

print(f"\nUser Details:")
print(f"  Email: {user.email}")
print(f"  Role: {user.role}")
print(f"  Active: {user.is_active}")
