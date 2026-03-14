# Generated migration to add ManualPayment model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0013_add_application_id'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ManualPayment',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(default='UGX', max_length=3)),
                ('reference', models.CharField(help_text='Payment reference (should match Application ID)', max_length=100)),
                ('proof_of_payment', models.FileField(help_text='Upload screenshot or receipt of payment', upload_to='payment_proofs/')),
                ('status', models.CharField(choices=[('pending', 'Pending Verification'), ('verified', 'Verified'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('verification_notes', models.TextField(blank=True)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='manual_payments', to='applications.application')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='manual_payments', to=settings.AUTH_USER_MODEL)),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_payments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Manual Payment',
                'verbose_name_plural': 'Manual Payments',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='manualpayment',
            index=models.Index(fields=['status', 'created_at'], name='payments_man_status_b8e7c5_idx'),
        ),
        migrations.AddIndex(
            model_name='manualpayment',
            index=models.Index(fields=['application', 'status'], name='payments_man_applica_4a8b9c_idx'),
        ),
    ]