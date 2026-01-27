import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname='public' AND tablename LIKE 'auth_%' 
        ORDER BY tablename
    """)
    tables = cursor.fetchall()
    
    print("✓ Authentication tables in database:")
    for table in tables:
        print(f"  - {table[0]}")

print("\n✓ Database schema verification complete!")
