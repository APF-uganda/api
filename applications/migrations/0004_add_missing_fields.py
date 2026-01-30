# Generated manually for adding missing fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0003_remove_application_date_of_birth_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='national_id_number',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='application',
            name='icpau_certificate_number',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]