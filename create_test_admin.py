import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from authentication.models import User

# Check if test admin exists
email = "testadmin@apf.com"
password = "TestAdmin@123"

user, created = User.objects.get_or_create(
    email=email,
    defaults={
        'first_name': 'Test',
        'last_name': 'Admin',
        'is_staff': True,
        'is_superuser': True,
        'is_active': True,
    }
)

if created:
    user.set_password(password)
    user.save()
    print(f" Created new admin user: {email}")
else:
    # Update password for existing user
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.is_active = True
    user.save()
    print(f" Updated existing admin user: {email}")

print(f"   Email: {email}")
print(f"   Password: {password}")
print(f"   Is Staff: {user.is_staff}")
print(f"   Is Superuser: {user.is_superuser}")
print(f"   Is Active: {user.is_active}")
