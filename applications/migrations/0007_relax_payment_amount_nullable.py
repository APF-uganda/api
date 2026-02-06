# Generated manually to relax payment_amount constraint (legacy/mocked column)

from django.db import migrations


def _column_exists(connection, table_name: str, column_name: str) -> bool:
    if connection.vendor == "sqlite":
        with connection.cursor() as cursor:
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            return any(row[1] == column_name for row in cursor.fetchall())
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name=%s AND column_name=%s;
            """,
            [table_name, column_name],
        )
        return cursor.fetchone() is not None


def relax_payment_amount_nullable(apps, schema_editor):
    connection = schema_editor.connection
    table_name = "applications_application"
    column_name = "payment_amount"

    if not _column_exists(connection, table_name, column_name):
        return

    # Best-effort: allow NULLs and set a default for legacy column.
    try:
        if connection.vendor == "postgresql":
            schema_editor.execute(
                f"ALTER TABLE {table_name} ALTER COLUMN {column_name} DROP NOT NULL;"
            )
            schema_editor.execute(
                f"ALTER TABLE {table_name} ALTER COLUMN {column_name} SET DEFAULT 0;"
            )
        elif connection.vendor == "mysql":
            schema_editor.execute(
                f"ALTER TABLE {table_name} MODIFY {column_name} DECIMAL(12,2) NULL DEFAULT 0;"
            )
        else:
            # SQLite doesn't support altering NOT NULL easily; ignore if present.
            pass
    except Exception:
        # Don't block migrations if DB doesn't support this operation.
        pass


def restore_payment_amount_not_null(apps, schema_editor):
    connection = schema_editor.connection
    table_name = "applications_application"
    column_name = "payment_amount"

    if not _column_exists(connection, table_name, column_name):
        return

    try:
        if connection.vendor == "postgresql":
            schema_editor.execute(
                f"ALTER TABLE {table_name} ALTER COLUMN {column_name} DROP DEFAULT;"
            )
            schema_editor.execute(
                f"ALTER TABLE {table_name} ALTER COLUMN {column_name} SET NOT NULL;"
            )
        elif connection.vendor == "mysql":
            schema_editor.execute(
                f"ALTER TABLE {table_name} MODIFY {column_name} DECIMAL(12,2) NOT NULL;"
            )
        else:
            pass
    except Exception:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ("applications", "0006_relax_unique_for_rejected"),
    ]

    operations = [
        migrations.RunPython(
            relax_payment_amount_nullable,
            restore_payment_amount_not_null,
        ),
    ]
