from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("Documents", "0002_create_applications_document_table"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE applications_document "
                "ADD COLUMN IF NOT EXISTS user_id bigint;"
                "ALTER TABLE applications_document "
                "ALTER COLUMN application_id DROP NOT NULL;"
                "CREATE INDEX IF NOT EXISTS applications_document_user_id_idx "
                "ON applications_document(user_id);"
                "DO $$ BEGIN "
                "ALTER TABLE applications_document "
                "ADD CONSTRAINT applications_document_user_id_fkey "
                "FOREIGN KEY (user_id) REFERENCES auth_users(id) "
                "ON DELETE CASCADE; "
                "EXCEPTION WHEN duplicate_object THEN END $$;"
            ),
            reverse_sql=(
                "DO $$ BEGIN "
                "ALTER TABLE applications_document "
                "DROP CONSTRAINT applications_document_user_id_fkey; "
                "EXCEPTION WHEN undefined_object THEN END $$;"
                "DROP INDEX IF EXISTS applications_document_user_id_idx;"
                "ALTER TABLE applications_document "
                "ALTER COLUMN application_id SET NOT NULL;"
                "ALTER TABLE applications_document "
                "DROP COLUMN IF EXISTS user_id;"
            ),
        ),
    ]
