# Generated migration for adding payment_amount field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0006_relax_unique_for_rejected'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='payment_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=50000.0,
                help_text='Payment amount in UGX',
                max_digits=12
            ),
        ),
    ]
