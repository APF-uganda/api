# Generated migration to safely add user field if it doesn't exist

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def add_user_field_if_not_exists(apps, schema_editor):
    """
    Add user field to Application model if it doesn't already exist.
    This handles the case where the field was added manually or in a previous migration.
    """
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Check if user_id column exists
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


def remove_user_field(apps, schema_editor):
    """
    Remove user field from Application model.
    """
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Check if user_id column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='applications_application' 
            AND column_name='user_id';
        """)
        
        if cursor.fetchone() is not None:
            # Column exists, remove it
            cursor.execute("""
                ALTER TABLE applications_application 
                DROP COLUMN user_id;
            """)


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("applications", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(
            add_user_field_if_not_exists,
            remove_user_field
        ),
        # Also add the document foreign key if needed
        migrations.AddField(
            model_name="document",
            name="application",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="documents",
                to="applications.application",
            ),
        ),
    ]
