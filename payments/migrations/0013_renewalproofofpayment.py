from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0012_alter_manualpayment_user'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RenewalProofOfPayment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invoice_number', models.CharField(db_index=True, max_length=50)),
                ('amount', models.DecimalField(decimal_places=2, default=Decimal('150000.00'), max_digits=10)),
                ('provider', models.CharField(choices=[('mtn', 'MTN Mobile Money'), ('airtel', 'Airtel Money'), ('bank', 'Bank Transfer')], default='mtn', max_length=20)),
                ('phone_number', models.CharField(blank=True, help_text='Phone used for mobile money', max_length=30)),
                ('proof_file', models.FileField(upload_to='renewal_proofs/')),
                ('reference_note', models.CharField(blank=True, max_length=200)),
                ('status', models.CharField(choices=[('pending_verification', 'Pending Verification'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending_verification', max_length=30)),
                ('review_notes', models.TextField(blank=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_renewal_proofs', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='renewal_proofs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Renewal Proof of Payment',
                'verbose_name_plural': 'Renewal Proofs of Payment',
                'ordering': ['-created_at'],
            },
        ),
    ]
