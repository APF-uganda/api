"""
Test sending actual emails via EmailJS
Run this to verify your EmailJS setup is working end-to-end
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from authentication.services import EmailService

print("=" * 60)
print("EmailJS Email Sending Test")
print("=" * 60)

# Get test email from user
test_email = input("Enter your email address to receive test emails: ").strip()

if not test_email or '@' not in test_email:
    print("❌ Invalid email address!")
    exit(1)

print(f"\nSending test emails to: {test_email}")
print("-" * 60)

# Test 1: OTP Email
print("\n1. Testing OTP Email...")
try:
    result = EmailService.send_otp_email(
        email=test_email,
        otp_code='123456',
        user_name='Test User'
    )
    if result:
        print("   ✅ OTP email sent successfully!")
        print("   📧 Check your inbox for verification code: 123456")
    else:
        print("   ❌ OTP email failed to send")
        print("   Check Django logs for details")
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# Test 2: Password Reset Email
print("\n2. Testing Password Reset Email...")
try:
    result = EmailService.send_password_reset_email(
        email=test_email,
        reset_token='test-token-abc123',
        user_name='Test User'
    )
    if result:
        print("   ✅ Password reset email sent successfully!")
        print("   📧 Check your inbox for reset link")
    else:
        print("   ❌ Password reset email failed to send")
        print("   Check Django logs for details")
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

print("\n" + "=" * 60)
print("Test complete! Check your email inbox.")
print("=" * 60)
