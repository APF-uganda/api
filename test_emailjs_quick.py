"""
Quick test to verify EmailJS is sending OTP emails
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from authentication.services import EmailService

def test_otp_email():
    """Test sending OTP email via EmailJS"""
    print("=" * 60)
    print("Testing EmailJS OTP Email Sending")
    print("=" * 60)
    
    # Test email
    test_email = "bashkiko@gmail.com"
    test_otp = "123456"
    test_name = "Bashkiko"
    
    print(f"\nSending OTP email to: {test_email}")
    print(f"OTP Code: {test_otp}")
    print(f"User Name: {test_name}")
    print("\nSending...")
    
    # Send email
    success = EmailService.send_otp_email(
        email=test_email,
        otp_code=test_otp,
        user_name=test_name
    )
    
    print("\n" + "=" * 60)
    if success:
        print("✅ SUCCESS! Email sent via EmailJS")
        print(f"✅ Check your inbox at {test_email}")
        print("✅ The OTP code should be: 123456")
    else:
        print("❌ FAILED! Email was not sent")
        print("❌ Check the error logs above")
        print("\nTroubleshooting:")
        print("1. Verify EmailJS credentials in .env file")
        print("2. Check EmailJS dashboard for service status")
        print("3. Verify template variables match")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    test_otp_email()
