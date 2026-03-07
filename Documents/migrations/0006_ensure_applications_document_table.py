# Generated manually to repair environments missing applications_document.

from django.db import migrations


def ensure_applications_document_table(apps, schema_editor):
    connection = schema_editor.connection
    vendor = connection.vendor

    if vendor == "postgresql":
        schema_editor.execute(
            """
            CREATE TABLE IF NOT EXISTS applications_document (
                id bigserial PRIMARY KEY,
                file varchar(100) NOT NULL,
                file_name varchar(255) NOT NULL,
                file_size integer NOT NULL,
                file_type varchar(50) NOT NULL,
                document_type varchar(50) NOT NULL DEFAULT '',
                status varchar(20) NOT NULL DEFAULT 'pending',
                expiry_date date NULL,
                admin_feedback text NOT NULL DEFAULT '',
                uploaded_at timestamp with time zone NOT NULL DEFAULT NOW(),
                application_id bigint NULL
            );
            """
        )
        schema_editor.execute(
            """
            CREATE INDEX IF NOT EXISTS applications_document_application_id_idx
            ON applications_document(application_id);
            """
        )
        schema_editor.execute(
            """
            DO $$
            BEGIN
                ALTER TABLE applications_document
                ADD CONSTRAINT applications_document_application_id_fkey
                FOREIGN KEY (application_id) REFERENCES applications_application(id)
                ON DELETE CASCADE;
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    elif vendor == "sqlite":
        schema_editor.execute(
            """
            CREATE TABLE IF NOT EXISTS applications_document (
                id integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                file varchar(100) NOT NULL,
                file_name varchar(255) NOT NULL,
                file_size integer NOT NULL,
                file_type varchar(50) NOT NULL,
                document_type varchar(50) NOT NULL DEFAULT '',
                status varchar(20) NOT NULL DEFAULT 'pending',
                expiry_date date NULL,
                admin_feedback text NOT NULL DEFAULT '',
                uploaded_at datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
                application_id bigint NULL REFERENCES applications_application(id) DEFERRABLE INITIALLY DEFERRED
            );
            """
        )
        schema_editor.execute(
            """
            CREATE INDEX IF NOT EXISTS applications_document_application_id_idx
            ON applications_document(application_id);
            """
        )


class Migration(migrations.Migration):

    dependencies = [
        ("Documents", "0005_alter_memberdocument_file"),
    ]

    operations = [
        migrations.RunPython(
            ensure_applications_document_table,
            migrations.RunPython.noop,
        ),
    ]