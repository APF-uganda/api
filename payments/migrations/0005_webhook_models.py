# Generated manually to create webhook tracking tables.

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0004_payment_card_expiry_payment_card_last_four_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="WebhookNotification",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("provider", models.CharField(max_length=20)),
                ("transaction_reference", models.CharField(db_index=True, max_length=100)),
                ("webhook_status", models.CharField(max_length=50)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("received", "Received"),
                            ("processed", "Processed"),
                            ("failed", "Failed"),
                        ],
                        default="received",
                        max_length=20,
                    ),
                ),
                ("error_message", models.TextField(blank=True, null=True)),
                ("payload", models.JSONField()),
                ("signature", models.CharField(max_length=500)),
                ("signature_valid", models.BooleanField(default=False)),
                ("received_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "payment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="webhook_notifications",
                        to="payments.payment",
                    ),
                ),
            ],
            options={
                "ordering": ["-received_at"],
                "verbose_name": "Webhook Notification",
                "verbose_name_plural": "Webhook Notifications",
                "indexes": [
                    models.Index(
                        fields=["transaction_reference", "received_at"],
                        name="payments_we_transac_8e3de0_idx",
                    ),
                    models.Index(
                        fields=["payment", "status"],
                        name="payments_we_payment_b102df_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="PaymentStatusCheck",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "check_type",
                    models.CharField(
                        choices=[
                            ("webhook", "Webhook"),
                            ("polling", "Polling"),
                            ("manual", "Manual"),
                        ],
                        max_length=20,
                    ),
                ),
                ("status_before", models.CharField(max_length=20)),
                ("status_after", models.CharField(max_length=20)),
                ("success", models.BooleanField(default=False)),
                ("message", models.TextField(blank=True, null=True)),
                ("response_data", models.JSONField(blank=True, null=True)),
                ("checked_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "payment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="status_checks",
                        to="payments.payment",
                    ),
                ),
            ],
            options={
                "ordering": ["-checked_at"],
                "verbose_name": "Payment Status Check",
                "verbose_name_plural": "Payment Status Checks",
                "indexes": [
                    models.Index(
                        fields=["payment", "check_type", "checked_at"],
                        name="payments_pa_payment_510b0d_idx",
                    ),
                ],
            },
        ),
    ]
