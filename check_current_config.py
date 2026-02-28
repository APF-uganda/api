"""
Check what EmailJS configuration Django is currently using
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from django.conf import settings
from authentication.services import EmailService

print("=" * 60)
print("Current EmailJS Configuration")
print("=" * 60)
print(f"Service ID (settings): {settings.EMAILJS_SERVICE_ID}")
print(f"Service ID (EmailService): {EmailService.EMAILJS_SERVICE_ID}")
print()
print(f"OTP Template (settings): {settings.EMAILJS_TEMPLATE_ID_OTP}")
print(f"OTP Template (EmailService): {EmailService.EMAILJS_TEMPLATE_ID_OTP}")
print()
print(f"Approval Template (settings): {settings.EMAILJS_TEMPLATE_ID_APPROVAL}")
print(f"Approval Template (EmailService): {EmailService.EMAILJS_TEMPLATE_ID_APPROVAL}")
print()
print(f"Public Key (settings): {settings.EMAILJS_PUBLIC_KEY}")
print(f"Public Key (EmailService): {EmailService.EMAILJS_PUBLIC_KEY}")
print()
print(f"Private Key (settings): {settings.EMAILJS_PRIVATE_KEY[:20]}..." if settings.EMAILJS_PRIVATE_KEY else "Private Key: NOT SET")
print(f"Private Key (EmailService): {EmailService.EMAILJS_PRIVATE_KEY[:20]}..." if EmailService.EMAILJS_PRIVATE_KEY else "Private Key: NOT SET")
print("=" * 60)

# Check if these match your new service
print("\nExpected new values:")
print("Service ID: service_4fbgc6k")
print("OTP Template: template_okkvzy9")
print("Approval Template: template_988bvdj")
print("Public Key: gxneaZyyHF3D6Xi4F")
print("=" * 60)
