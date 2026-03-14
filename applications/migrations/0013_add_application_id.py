# Generated migration to add unique application_id field

from django.db import migrations, models
import uuid


def generate_application_ids(apps, schema_editor):
    """Generate unique application IDs for existing applications"""
    Application = apps.get_model('applications', 'Application')
    from datetime import datetime
    
    for i, application in enumerate(Application.objects.all().order_by('submitted_at'), 1):
        year = application.submitted_at.year if application.submitted_at else datetime.now().year
        application_id = f"APF-{year}-{i:06d}"
        application.application_id = application_id
        application.save()


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0012_application_organization'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='application_id',
            field=models.CharField(
                max_length=20,
                unique=True,
                null=True,
                blank=True,
                help_text='Unique application identifier (e.g., APF-2026-000123)'
            ),
        ),
        migrations.RunPython(generate_application_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='application',
            name='application_id',
            field=models.CharField(
                max_length=20,
                unique=True,
                help_text='Unique application identifier (e.g., APF-2026-000123)'
            ),
        ),
    ]