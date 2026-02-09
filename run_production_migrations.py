#!/usr/bin/env python
"""
Production Migration Runner

This script automates the process of running database migrations in production
with proper backup, verification, and rollback capabilities.

Usage:
    python run_production_migrations.py --backup-only    # Create backup only
    python run_production_migrations.py --check          # Check migration status
    python run_production_migrations.py --plan           # Show migration plan
    python run_production_migrations.py --migrate        # Run migrations
    python run_production_migrations.py --verify         # Verify migrations
    python run_production_migrations.py --rollback       # Rollback migrations
"""

import os
import sys
import subprocess
import datetime
from pathlib import Path


class Colors:
    """ANSI color codes"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}\n")


def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


def run_command(command, capture_output=True):
    """Run shell command and return result"""
    try:
        if capture_output:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout
        else:
            result = subprocess.run(command, shell=True, check=True)
            return True, ""
    except subprocess.CalledProcessError as e:
        return False, str(e)


def create_backup():
    """Create database backup"""
    print_header("CREATE DATABASE BACKUP")
    
    print_warning("CRITICAL: Creating database backup before migration")
    print_info("This may take several minutes depending on database size...\n")
    
    # Get database credentials from environment
    db_name = os.getenv('DB_NAME', 'apf_portal_production')
    db_user = os.getenv('DB_USER', 'apf_db_user')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    
    # Create backup directory
    backup_dir = Path(__file__).parent / 'backups'
    backup_dir.mkdir(exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_dir / f"{db_name}_{timestamp}.sql"
    
    print_info(f"Database: {db_name}")
    print_info(f"Host: {db_host}")
    print_info(f"Backup file: {backup_file}\n")
    
    # Create backup using pg_dump
    backup_command = f"pg_dump -h {db_host} -p {db_port} -U {db_user} -d {db_name} -F c -f {backup_file}"
    
    print_info("Running pg_dump...")
    success, output = run_command(backup_command, capture_output=False)
    
    if success and backup_file.exists():
        file_size = backup_file.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        print_success(f"Backup created successfully: {backup_file}")
        print_success(f"Backup size: {file_size_mb:.2f} MB")
        
        # Log backup
        log_file = backup_dir / 'backup_log.txt'
        with open(log_file, 'a') as f:
            f.write(f"{timestamp} - {backup_file} - {file_size_mb:.2f} MB\n")
        
        return True, str(backup_file)
    else:
        print_error("Backup failed!")
        print_error(output)
        return False, None


def check_migration_status():
    """Check current migration status"""
    print_header("CHECK MIGRATION STATUS")
    
    print_info("Checking payment migrations status...\n")
    
    success, output = run_command("python manage.py showmigrations payments")
    
    if success:
        print(output)
        
        # Parse output to determine status
        if '[X]' in output or '[x]' in output:
            print_success("Some migrations are already applied")
        else:
            print_info("No migrations applied yet")
        
        return True
    else:
        print_error("Failed to check migration status")
        print_error(output)
        return False


def show_migration_plan():
    """Show migration plan"""
    print_header("MIGRATION PLAN")
    
    print_info("Showing what migrations will be applied...\n")
    
    success, output = run_command("python manage.py migrate payments --plan")
    
    if success:
        print(output)
        
        if "No planned operations" in output or "No migrations to apply" in output:
            print_info("No migrations to apply - database is up to date")
        else:
            print_info("Migrations will be applied as shown above")
        
        return True
    else:
        print_error("Failed to show migration plan")
        print_error(output)
        return False


def run_migrations():
    """Run database migrations"""
    print_header("RUN DATABASE MIGRATIONS")
    
    # First, create backup
    print_warning("Step 1: Creating backup before migration")
    backup_success, backup_file = create_backup()
    
    if not backup_success:
        print_error("Backup failed - aborting migration!")
        print_error("Fix backup issues before running migrations")
        return False
    
    print_success(f"Backup completed: {backup_file}\n")
    
    # Show migration plan
    print_warning("Step 2: Reviewing migration plan")
    show_migration_plan()
    
    # Confirm before proceeding
    print(f"\n{Colors.BOLD}Ready to run migrations?{Colors.END}")
    print_warning("This will modify the production database!")
    response = input("Type 'yes' to continue: ")
    
    if response.lower() != 'yes':
        print_info("Migration cancelled by user")
        return False
    
    # Run migrations
    print_warning("\nStep 3: Running migrations...")
    print_info("This may take a few seconds...\n")
    
    success, output = run_command("python manage.py migrate payments", capture_output=False)
    
    if success:
        print_success("\nMigrations completed successfully!")
        
        # Verify migrations
        print_warning("\nStep 4: Verifying migrations...")
        verify_migrations()
        
        return True
    else:
        print_error("\nMigration failed!")
        print_error(output)
        print_warning(f"\nBackup available at: {backup_file}")
        print_warning("You can restore from backup if needed")
        return False


def verify_migrations():
    """Verify migrations were applied correctly"""
    print_header("VERIFY MIGRATIONS")
    
    print_info("Verifying migrations were applied correctly...\n")
    
    # Check migration status
    print(f"{Colors.BOLD}1. Checking migration status:{Colors.END}")
    success, output = run_command("python manage.py showmigrations payments")
    if success:
        print(output)
        if '[X] 0001_initial' in output and '[X] 0002_seed_payment_config' in output:
            print_success("All migrations applied\n")
        else:
            print_warning("Some migrations may not be applied\n")
    
    # Check tables exist
    print(f"{Colors.BOLD}2. Checking tables exist:{Colors.END}")
    check_tables_command = """python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute(\\\"SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'payments_%';\\\")
tables = cursor.fetchall()
for table in tables:
    print(f'  ✓ {table[0]}')
"
"""
    success, output = run_command(check_tables_command)
    if success:
        print(output)
    
    # Check seeded data
    print(f"{Colors.BOLD}3. Checking seeded data:{Colors.END}")
    check_data_command = """python manage.py shell -c "
from payments.models import PaymentConfig
try:
    fee = PaymentConfig.get_membership_fee()
    print(f'  ✓ Membership fee: {fee} UGX')
except Exception as e:
    print(f'  ✗ Error: {e}')
"
"""
    success, output = run_command(check_data_command)
    if success:
        print(output)
    
    print_success("\nVerification complete!")


def rollback_migrations():
    """Rollback migrations"""
    print_header("ROLLBACK MIGRATIONS")
    
    print_warning("This will remove all payment tables and data!")
    print_warning("Make sure you have a backup before proceeding")
    
    response = input("\nType 'yes' to rollback migrations: ")
    
    if response.lower() != 'yes':
        print_info("Rollback cancelled by user")
        return False
    
    print_info("\nRolling back migrations...")
    
    success, output = run_command("python manage.py migrate payments zero", capture_output=False)
    
    if success:
        print_success("\nMigrations rolled back successfully!")
        
        # Verify rollback
        print_info("\nVerifying rollback...")
        check_migration_status()
        
        return True
    else:
        print_error("\nRollback failed!")
        print_error(output)
        return False


def print_usage():
    """Print usage instructions"""
    print_header("PRODUCTION MIGRATION RUNNER")
    
    print(f"{Colors.BOLD}Usage:{Colors.END}")
    print(f"  python run_production_migrations.py --backup-only    # Create backup only")
    print(f"  python run_production_migrations.py --check          # Check migration status")
    print(f"  python run_production_migrations.py --plan           # Show migration plan")
    print(f"  python run_production_migrations.py --migrate        # Run migrations")
    print(f"  python run_production_migrations.py --verify         # Verify migrations")
    print(f"  python run_production_migrations.py --rollback       # Rollback migrations")
    print(f"  python run_production_migrations.py --help           # Show this help")
    print()


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print_usage()
        return
    
    command = sys.argv[1].lower()
    
    # Check we're in the right directory
    if not Path('manage.py').exists():
        print_error("Error: manage.py not found")
        print_error("Please run this script from the Backend directory")
        sys.exit(1)
    
    # Check environment
    if os.getenv('PAYMENT_ENVIRONMENT') == 'production':
        print_warning("PAYMENT_ENVIRONMENT is set to 'production'")
        print_warning("Migrations will affect PRODUCTION database with REAL money transactions!")
    
    if command in ['--help', '-h', 'help']:
        print_usage()
    
    elif command in ['--backup-only', '-b', 'backup']:
        create_backup()
    
    elif command in ['--check', '-c', 'check']:
        check_migration_status()
    
    elif command in ['--plan', '-p', 'plan']:
        show_migration_plan()
    
    elif command in ['--migrate', '-m', 'migrate']:
        success = run_migrations()
        sys.exit(0 if success else 1)
    
    elif command in ['--verify', '-v', 'verify']:
        verify_migrations()
    
    elif command in ['--rollback', '-r', 'rollback']:
        success = rollback_migrations()
        sys.exit(0 if success else 1)
    
    else:
        print_error(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == '__main__':
    main()
