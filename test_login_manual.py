"""
Manual test script to verify login functionality
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from authentication.services import AuthenticationService, OTPService
from django.contrib.auth import get_user_model

User = get_user_model()

print("Testing login functionality...")
print("-" * 50)

# Test 1: Wrong password
print("\n1. Testing with WRONG password:")
user = AuthenticationService.verify_credentials('bashkiko@gmail.com', 'wrongpassword')
if user:
    print("   ❌ FAIL: Should not authenticate with wrong password")
else:
    print("   ✅ PASS: Correctly rejected wrong password")

# Test 2: Correct password
print("\n2. Testing with CORRECT password:")
user = AuthenticationService.verify_credentials('bashkiko@gmail.com', 'Nakaye0@1')
if user:
    print(f"   ✅ PASS: Authenticated user: {user.email} (role={user.role})")
    
    # Test 3: Generate OTP
    print("\n3. Testing OTP generation:")
    try:
        otp, session_id = OTPService.generate_otp(user)
        print(f"   ✅ PASS: Generated OTP")
        print(f"   - OTP Code: {otp.code}")
        print(f"   - Session ID: {session_id}")
        print(f"   - Expires at: {otp.expires_at}")
    except Exception as e:
        print(f"   ❌ FAIL: Error generating OTP: {str(e)}")
else:
    print("   ❌ FAIL: Should authenticate with correct password")

print("\n" + "-" * 50)
print("Test complete!")
