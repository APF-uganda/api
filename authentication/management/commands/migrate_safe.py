"""
Custom migrate command that fixes migration inconsistencies before running migrations.
"""
from django.core.management.commands.migrate import Command as MigrateCommand
from django.db import connection


class Command(MigrateCommand):
    help = 'Safely run migrations by fixing inconsistencies first'

    def handle(self, *args, **options):
        """Clear inconsistent migration history before migrating."""
        self.stdout.write("Checking for migration inconsistencies...")
        
        try:
            with connection.cursor() as cursor:
                # Check if django_migrations table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'django_migrations'
                    );
                """)
                exists = cursor.fetchone()[0]
                
                if exists:
                    # Check for the specific inconsistency
                    cursor.execute("""
                        SELECT COUNT(*) FROM django_migrations 
                        WHERE app = 'admin' AND name = '0001_initial';
                    """)
                    admin_exists = cursor.fetchone()[0] > 0
                    
                    cursor.execute("""
                        SELECT COUNT(*) FROM django_migrations 
                        WHERE app = 'authentication' AND name = '0001_initial';
                    """)
                    auth_exists = cursor.fetchone()[0] > 0
                    
                    if admin_exists and not auth_exists:
                        self.stdout.write(
                            self.style.WARNING(
                                "Found inconsistent migration history. Clearing..."
                            )
                        )
                        cursor.execute("DELETE FROM django_migrations;")
                        self.stdout.write(
                            self.style.SUCCESS("Migration history cleared!")
                        )
                    else:
                        self.stdout.write("Migration history is consistent.")
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Could not check migrations: {e}")
            )
        
        # Now run the normal migrate command
        super().handle(*args, **options)
