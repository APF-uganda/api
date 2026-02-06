# Migration to add expired_members to audience choices

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('AdminNotifications', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='announcement',
            name='audience',
            field=models.CharField(
                choices=[
                    ('all_users', 'All Users'),
                    ('members', 'Members'),
                    ('applicants', 'Applicants'),
                    ('admins', 'Admins'),
                    ('expired_members', 'Expired Members')
                ],
                default='all_users',
                max_length=50
            ),
        ),
    ]
