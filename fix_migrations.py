import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    # Check if the migration already exists
    cursor.execute(
        "SELECT COUNT(*) FROM django_migrations WHERE app = 'authentication' AND name = '0001_initial'"
    )
    count = cursor.fetchone()[0]
    
    if count == 0:
        # Insert the authentication migration record
        cursor.execute(
            "INSERT INTO django_migrations (app, name, applied) VALUES ('authentication', '0001_initial', NOW())"
        )
        print("✓ Added authentication.0001_initial to migration history")
    else:
        print("✓ Migration authentication.0001_initial already exists")

print("\nNow run: python manage.py migrate")
