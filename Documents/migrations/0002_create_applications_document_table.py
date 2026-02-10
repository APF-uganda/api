from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("Documents", "0001_document_state_and_columns"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "CREATE TABLE IF NOT EXISTS applications_document ("
                "id bigserial PRIMARY KEY, "
                "file varchar(100) NOT NULL, "
                "file_name varchar(255) NOT NULL, "
                "file_size integer NOT NULL, "
                "file_type varchar(50) NOT NULL, "
                "document_type varchar(50) NOT NULL DEFAULT '', "
                "status varchar(20) NOT NULL DEFAULT 'pending', "
                "expiry_date date NULL, "
                "admin_feedback text NOT NULL DEFAULT '', "
                "uploaded_at timestamp with time zone NOT NULL DEFAULT NOW(), "
                "application_id bigint NOT NULL "
                ");"
                "CREATE INDEX IF NOT EXISTS applications_document_application_id_idx "
                "ON applications_document(application_id);"
                "ALTER TABLE applications_document "
                "ADD CONSTRAINT applications_document_application_id_fkey "
                "FOREIGN KEY (application_id) REFERENCES applications_application(id) "
                "ON DELETE CASCADE;"
            ),
            reverse_sql=(
                "DROP TABLE IF EXISTS applications_document;"
            ),
        ),
    ]
