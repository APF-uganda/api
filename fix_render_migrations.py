#!/usr/bin/env python
"""
Script to fix migration inconsistencies on Render deployment.
Run this before migrate command in build script.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from django.db import connection

def fix_migrations():
    """Clear migration history and let Django rebuild it."""
    with connection.cursor() as cursor:
        print("Checking if django_migrations table exists...")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'django_migrations'
            );
        """)
        exists = cursor.fetchone()[0]
        
        if exists:
            print("Clearing inconsistent migration history...")
            cursor.execute("DELETE FROM django_migrations;")
            print("Migration history cleared successfully!")
        else:
            print("No migration history found. This is a fresh database.")

if __name__ == '__main__':
    try:
        fix_migrations()
        print("\n✓ Migration fix completed. Now run: python manage.py migrate")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
