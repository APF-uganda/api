from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("applications", "0008_merge_20260208_0012"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="Document",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("file", models.FileField(upload_to="application_documents/")),
                        ("file_name", models.CharField(max_length=255)),
                        ("file_size", models.IntegerField()),
                        ("file_type", models.CharField(max_length=50)),
                        ("document_type", models.CharField(blank=True, default="", max_length=50)),
                        ("status", models.CharField(choices=[("approved", "Approved"), ("pending", "Pending"), ("rejected", "Rejected"), ("expired", "Expired")], default="pending", max_length=20)),
                        ("expiry_date", models.DateField(blank=True, null=True)),
                        ("admin_feedback", models.TextField(blank=True)),
                        ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                        ("application", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="documents", to="applications.application")),
                    ],
                    options={
                        "verbose_name": "Application Document",
                        "verbose_name_plural": "Application Documents",
                        "db_table": "applications_document",
                        "ordering": ["uploaded_at"],
                        "managed": False,
                    },
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE applications_document "
                        "ADD COLUMN IF NOT EXISTS status varchar(20) NOT NULL DEFAULT 'pending';"
                    ),
                    reverse_sql=(
                        "ALTER TABLE applications_document "
                        "DROP COLUMN IF EXISTS status;"
                    ),
                ),
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE applications_document "
                        "ADD COLUMN IF NOT EXISTS expiry_date date;"
                    ),
                    reverse_sql=(
                        "ALTER TABLE applications_document "
                        "DROP COLUMN IF EXISTS expiry_date;"
                    ),
                ),
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE applications_document "
                        "ADD COLUMN IF NOT EXISTS admin_feedback text;"
                    ),
                    reverse_sql=(
                        "ALTER TABLE applications_document "
                        "DROP COLUMN IF EXISTS admin_feedback;"
                    ),
                ),
            ],
        ),
    ]
