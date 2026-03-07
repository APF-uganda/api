"""
Migration to register the Announcement model in the notifications app.
The underlying table (AdminNotifications_announcement) already exists,
so we use SeparateDatabaseAndState to only update Django's internal state
without touching the database.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("notifications", "0003_rename_notificatio_user_id_f8e9a3_idx_notificatio_user_id_776dd3_idx_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="Announcement",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("title", models.CharField(max_length=255)),
                        ("content", models.TextField()),
                        ("audience", models.CharField(
                            choices=[
                                ("all_users", "All Users"),
                                ("members", "Members"),
                                ("applicants", "Applicants"),
                                ("admins", "Admins"),
                                ("expired_members", "Expired Members"),
                            ],
                            default="all_users",
                            max_length=20,
                        )),
                        ("channel", models.CharField(
                            choices=[("email", "Email"), ("in_app", "In-App"), ("both", "Both")],
                            default="both",
                            max_length=10,
                        )),
                        ("status", models.CharField(
                            choices=[("draft", "Draft"), ("scheduled", "Scheduled"), ("sent", "Sent")],
                            default="draft",
                            max_length=10,
                        )),
                        ("created_by", models.ForeignKey(
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name="created_announcements",
                            to=settings.AUTH_USER_MODEL,
                        )),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        ("scheduled_for", models.DateTimeField(blank=True, null=True)),
                        ("sent_at", models.DateTimeField(blank=True, null=True)),
                        ("priority", models.CharField(
                            choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")],
                            default="medium",
                            max_length=10,
                        )),
                    ],
                    options={
                        "db_table": "AdminNotifications_announcement",
                        "ordering": ["-created_at"],
                    },
                ),
            ],
            database_operations=[],  # Table already exists — no DB changes
        ),
    ]
