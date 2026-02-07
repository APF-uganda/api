from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="profileactivitylog",
            name="metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
