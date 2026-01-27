import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from django.db import connection

# Read the SQL file
with open('create_auth_tables.sql', 'r', encoding='utf-8') as f:
    sql = f.read()

# Execute the SQL
with connection.cursor() as cursor:
    cursor.execute(sql)
    print("✓ Authentication tables created successfully")

print("\nNow run: python manage.py migrate")
