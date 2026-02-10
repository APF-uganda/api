from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("Documents", "0003_add_user_and_nullable_application"),
        ("authentication", "0004_user_date_of_birth_user_first_name_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="MemberDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="application_documents/")),
                ("file_name", models.CharField(max_length=255)),
                ("file_size", models.IntegerField()),
                ("file_type", models.CharField(max_length=50)),
                ("document_type", models.CharField(blank=True, default="", max_length=50)),
                ("status", models.CharField(choices=[("approved", "Approved"), ("pending", "Pending")], default="pending", max_length=20)),
                ("expiry_date", models.DateField(blank=True, null=True)),
                ("admin_feedback", models.TextField(blank=True)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="member_documents", to="authentication.user")),
            ],
            options={
                "verbose_name": "Member Document",
                "verbose_name_plural": "Member Documents",
                "ordering": ["uploaded_at"],
            },
        ),
        migrations.RunSQL(
            sql=(
                "INSERT INTO \"Documents_memberdocument\" "
                "(file, file_name, file_size, file_type, document_type, status, expiry_date, admin_feedback, uploaded_at, user_id) "
                "SELECT file, file_name, file_size, file_type, document_type, "
                "COALESCE(status, 'pending'), expiry_date, admin_feedback, uploaded_at, user_id "
                "FROM applications_document "
                "WHERE application_id IS NULL AND user_id IS NOT NULL;"
                "DELETE FROM applications_document "
                "WHERE application_id IS NULL AND user_id IS NOT NULL;"
            ),
            reverse_sql=(
                "INSERT INTO applications_document "
                "(file, file_name, file_size, file_type, document_type, status, expiry_date, admin_feedback, uploaded_at, application_id, user_id) "
                "SELECT file, file_name, file_size, file_type, document_type, status, expiry_date, admin_feedback, uploaded_at, NULL, user_id "
                "FROM \"Documents_memberdocument\";"
                "DELETE FROM \"Documents_memberdocument\";"
            ),
        ),
    ]
