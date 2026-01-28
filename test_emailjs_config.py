"""
Quick test to verify EmailJS configuration is loaded correctly
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from django.conf import settings

print("=" * 60)
print("EmailJS Configuration Test")
print("=" * 60)
print(f"✓ Service ID: {settings.EMAILJS_SERVICE_ID}")
print(f"✓ OTP Template ID: {settings.EMAILJS_TEMPLATE_ID_OTP}")
print(f"✓ Reset Template ID: {settings.EMAILJS_TEMPLATE_ID_PASSWORD_RESET}")
print(f"✓ Public Key: {settings.EMAILJS_PUBLIC_KEY}")
print(f"✓ API URL: {settings.EMAILJS_API_URL}")
print("=" * 60)

# Verify all values are set
if all([
    settings.EMAILJS_SERVICE_ID,
    settings.EMAILJS_TEMPLATE_ID_OTP,
    settings.EMAILJS_TEMPLATE_ID_PASSWORD_RESET,
    settings.EMAILJS_PUBLIC_KEY
]):
    print("✅ All EmailJS configuration values are set!")
else:
    print("❌ Some EmailJS configuration values are missing!")
    
print("=" * 60)
