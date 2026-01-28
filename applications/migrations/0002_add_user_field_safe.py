# Generated migration to safely add user field if it doesn't exist

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def add_fields_if_not_exist(apps, schema_editor):
    """
    Add user field to Application and application field to Document if they don't already exist.
    This handles the case where fields were added manually or in a previous migration.
    """
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Check if user_id column exists in applications_application
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='applications_application' 
            AND column_name='user_id';
        """)
        
        if cursor.fetchone() is None:
            # Column doesn't exist, add it
            cursor.execute("""
                ALTER TABLE applications_application 
                ADD COLUMN user_id INTEGER NULL 
                REFERENCES authentication_user(id) 
                ON DELETE SET NULL;
            """)
            
            # Create index
            cursor.execute("""
                CREATE INDEX applications_application_user_id_idx 
                ON applications_application(user_id);
            """)
        
        # Check if application_id column exists in applications_document
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='applications_document' 
            AND column_name='application_id';
        """)
        
        if cursor.fetchone() is None:
            # Column doesn't exist, add it
            cursor.execute("""
                ALTER TABLE applications_document 
                ADD COLUMN application_id INTEGER NOT NULL 
                REFERENCES applications_application(id) 
                ON DELETE CASCADE;
            """)
            
            # Create index
            cursor.execute("""
                CREATE INDEX applications_document_application_id_idx 
                ON applications_document(application_id);
            """)


def remove_fields(apps, schema_editor):
    """
    Remove user and application fields.
    """
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Check and remove user_id column
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='applications_application' 
            AND column_name='user_id';
        """)
        
        if cursor.fetchone() is not None:
            cursor.execute("""
                ALTER TABLE applications_application 
                DROP COLUMN user_id;
            """)
        
        # Check and remove application_id column
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='applications_document' 
            AND column_name='application_id';
        """)
        
        if cursor.fetchone() is not None:
            cursor.execute("""
                ALTER TABLE applications_document 
                DROP COLUMN application_id;
            """)


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("applications", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(
            add_fields_if_not_exist,
            remove_fields
        ),
    ]
