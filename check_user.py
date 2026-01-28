import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from authentication.models import User
from django.db import connection

print("Database Connection:")
print(f"  Name: {connection.settings_dict['NAME']}")
print(f"  Host: {connection.settings_dict['HOST']}")
print()

email = 'kikomekobashir29@gmail.com'
print(f"Checking for user: {email}")

user = User.objects.filter(email=email).first()

if user:
    print(f"✅ User found!")
    print(f"  Email: {user.email}")
    print(f"  Role: {user.role}")
    print(f"  Active: {user.is_active}")
    print(f"  Password hash: {user.password[:20]}...")
else:
    print(f"❌ User NOT found in database")
    print()
    print("All users in database:")
    for u in User.objects.all():
        print(f"  - {u.email}")
