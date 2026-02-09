# Generated migration for UserNotification model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('notification_type', models.CharField(choices=[('announcement', 'Announcement'), ('system', 'System'), ('info', 'Info'), ('success', 'Success'), ('warning', 'Warning'), ('error', 'Error')], default='info', max_length=20)),
                ('priority', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='medium', max_length=20)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='usernotification',
            index=models.Index(fields=['user', '-created_at'], name='notificatio_user_id_f8e9a3_idx'),
        ),
        migrations.AddIndex(
            model_name='usernotification',
            index=models.Index(fields=['user', 'is_read'], name='notificatio_user_id_a1b2c3_idx'),
        ),
    ]
