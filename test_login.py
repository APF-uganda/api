"""
Quick test script to verify login credentials work
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from authentication.services import AuthenticationService

# Test admin credentials
print("Testing Admin Login:")
print("=" * 50)
email = "bashkiko@gmail.com"
password = "admin123"
print(f"Email: {email}")
user = AuthenticationService.verify_credentials(email, password)
if user:
    print(f"✅ SUCCESS! User authenticated")
    print(f"   - Email: {user.email}")
    print(f"   - Role: {user.role}")
    print(f"   - Is Active: {user.is_active}")
else:
    print("❌ FAILED! Invalid credentials")

print("\n")

# Test member credentials
print("Testing Member Login:")
print("=" * 50)
email = "kikomekobashir29@gmail.com"
password = "member123"
print(f"Email: {email}")
user = AuthenticationService.verify_credentials(email, password)
if user:
    print(f"✅ SUCCESS! User authenticated")
    print(f"   - Email: {user.email}")
    print(f"   - Role: {user.role}")
    print(f"   - Is Active: {user.is_active}")
else:
    print("❌ FAILED! Invalid credentials")

