#!/usr/bin/env python
"""
Production Environment Configuration Helper

This script helps configure and validate production environment variables
for the mobile money payment integration.

Usage:
    python configure_production_env.py --check          # Check current configuration
    python configure_production_env.py --generate       # Generate secure keys
    python configure_production_env.py --validate       # Validate production config
"""

import os
import sys
import secrets
from pathlib import Path
from cryptography.fernet import Fernet
from django.core.management.utils import get_random_secret_key


class Colors:
    """ANSI color codes for terminal output"""
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


def generate_django_secret_key():
    """Generate Django secret key"""
    return get_random_secret_key()


def generate_fernet_key():
    """Generate Fernet encryption key"""
    return Fernet.generate_key().decode()


def generate_webhook_secret():
    """Generate webhook secret"""
    return secrets.token_urlsafe(32)


def generate_secure_keys():
    """Generate all required secure keys"""
    print_header("GENERATE SECURE KEYS")
    
    print_info("Generating secure keys for production environment...\n")
    
    keys = {
        'SECRET_KEY': generate_django_secret_key(),
        'PHONE_ENCRYPTION_KEY': generate_fernet_key(),
        'MTN_WEBHOOK_SECRET': generate_webhook_secret(),
        'AIRTEL_WEBHOOK_SECRET': generate_webhook_secret(),
    }
    
    print(f"{Colors.BOLD}Generated Keys:{Colors.END}\n")
    
    for key_name, key_value in keys.items():
        print(f"{Colors.BOLD}{key_name}:{Colors.END}")
        print(f"{key_value}\n")
    
    print_warning("IMPORTANT: Store these keys securely!")
    print_warning("Add them to your .env file and never commit them to version control.")
    print_warning("Keep a backup of PHONE_ENCRYPTION_KEY - losing it means losing access to encrypted data.\n")
    
    return keys


def check_env_variable(var_name, required=True, secure=False):
    """Check if environment variable is set and valid"""
    value = os.getenv(var_name)
    
    if value is None or value == '':
        if required:
            print_error(f"{var_name}: NOT SET (Required)")
            return False
        else:
            print_warning(f"{var_name}: NOT SET (Optional)")
            return True
    
    # Check for placeholder values
    placeholder_indicators = [
        'REPLACE_WITH_',
        'your-',
        'REPLACE',
        'TODO',
        'CHANGEME',
        'example',
    ]
    
    if any(indicator in value for indicator in placeholder_indicators):
        print_error(f"{var_name}: Contains placeholder value")
        return False
    
    # Check minimum length for secure values
    if secure and len(value) < 20:
        print_warning(f"{var_name}: Value seems too short for a secure key")
        return False
    
    print_success(f"{var_name}: Configured")
    return True


def validate_production_config():
    """Validate production environment configuration"""
    print_header("VALIDATE PRODUCTION CONFIGURATION")
    
    print_info("Checking production environment variables...\n")
    
    all_valid = True
    
    # Django Configuration
    print(f"\n{Colors.BOLD}Django Configuration:{Colors.END}")
    all_valid &= check_env_variable('SECRET_KEY', required=True, secure=True)
    all_valid &= check_env_variable('DEBUG', required=True)
    
    # Check DEBUG is False
    if os.getenv('DEBUG', '').lower() in ['true', '1', 'yes']:
        print_error("DEBUG: Must be False in production!")
        all_valid = False
    
    # Database Configuration
    print(f"\n{Colors.BOLD}Database Configuration:{Colors.END}")
    all_valid &= check_env_variable('DB_NAME', required=True)
    all_valid &= check_env_variable('DB_USER', required=True)
    all_valid &= check_env_variable('DB_PASSWORD', required=True, secure=True)
    all_valid &= check_env_variable('DB_HOST', required=True)
    all_valid &= check_env_variable('DB_PORT', required=True)
    all_valid &= check_env_variable('DB_SSL_MODE', required=True)
    
    # Check SSL mode is 'require'
    if os.getenv('DB_SSL_MODE') != 'require':
        print_warning("DB_SSL_MODE: Should be 'require' in production")
    
    # Payment Configuration
    print(f"\n{Colors.BOLD}Payment Configuration:{Colors.END}")
    all_valid &= check_env_variable('PAYMENT_ENVIRONMENT', required=True)
    
    # Check payment environment
    payment_env = os.getenv('PAYMENT_ENVIRONMENT', '')
    if payment_env == 'production':
        print_warning("PAYMENT_ENVIRONMENT: Set to 'production' - REAL money transactions will be processed!")
    elif payment_env == 'sandbox':
        print_info("PAYMENT_ENVIRONMENT: Set to 'sandbox' - Test mode")
    else:
        print_error(f"PAYMENT_ENVIRONMENT: Invalid value '{payment_env}' (must be 'sandbox' or 'production')")
        all_valid = False
    
    # MTN Configuration
    print(f"\n{Colors.BOLD}MTN Mobile Money Configuration:{Colors.END}")
    all_valid &= check_env_variable('MTN_API_USER', required=True)
    all_valid &= check_env_variable('MTN_API_KEY', required=True, secure=True)
    all_valid &= check_env_variable('MTN_SUBSCRIPTION_KEY', required=True, secure=True)
    
    # Airtel Configuration
    print(f"\n{Colors.BOLD}Airtel Money Configuration:{Colors.END}")
    all_valid &= check_env_variable('AIRTEL_CLIENT_ID', required=True)
    all_valid &= check_env_variable('AIRTEL_CLIENT_SECRET', required=True, secure=True)
    
    # Encryption Configuration
    print(f"\n{Colors.BOLD}Encryption Configuration:{Colors.END}")
    all_valid &= check_env_variable('PHONE_ENCRYPTION_KEY', required=True, secure=True)
    
    # Validate Fernet key format
    encryption_key = os.getenv('PHONE_ENCRYPTION_KEY')
    if encryption_key:
        try:
            Fernet(encryption_key.encode())
            print_success("PHONE_ENCRYPTION_KEY: Valid Fernet key format")
        except Exception as e:
            print_error(f"PHONE_ENCRYPTION_KEY: Invalid Fernet key format - {e}")
            all_valid = False
    
    # Webhook Configuration
    print(f"\n{Colors.BOLD}Webhook Configuration:{Colors.END}")
    all_valid &= check_env_variable('MTN_WEBHOOK_SECRET', required=True, secure=True)
    all_valid &= check_env_variable('AIRTEL_WEBHOOK_SECRET', required=True, secure=True)
    
    # Rate Limiting Configuration
    print(f"\n{Colors.BOLD}Rate Limiting Configuration:{Colors.END}")
    all_valid &= check_env_variable('PAYMENT_RATE_LIMIT_REQUESTS', required=False)
    all_valid &= check_env_variable('PAYMENT_RATE_LIMIT_WINDOW', required=False)
    
    # Redis Configuration
    print(f"\n{Colors.BOLD}Redis Configuration:{Colors.END}")
    check_env_variable('REDIS_URL', required=False)
    
    # Summary
    print(f"\n{Colors.BOLD}{'=' * 80}{Colors.END}")
    if all_valid:
        print_success("All required environment variables are configured correctly!")
        print_info("Run 'python manage.py check --deploy' for additional Django checks.")
    else:
        print_error("Some environment variables are missing or invalid.")
        print_info("Please review the errors above and update your .env file.")
    print(f"{Colors.BOLD}{'=' * 80}{Colors.END}\n")
    
    return all_valid


def check_current_config():
    """Check current environment configuration"""
    print_header("CURRENT ENVIRONMENT CONFIGURATION")
    
    # Load environment variables from .env if it exists
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        print_success(f"Found .env file: {env_file}")
        print_info("Loading environment variables from .env file...\n")
        
        # Simple .env parser
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and not os.getenv(key):
                        os.environ[key] = value
    else:
        print_warning(f".env file not found: {env_file}")
        print_info("Using system environment variables only.\n")
    
    # Show current configuration (masked)
    config_vars = [
        'DEBUG',
        'PAYMENT_ENVIRONMENT',
        'DB_NAME',
        'DB_HOST',
        'DB_SSL_MODE',
    ]
    
    print(f"{Colors.BOLD}Current Configuration:{Colors.END}\n")
    for var in config_vars:
        value = os.getenv(var, 'NOT SET')
        print(f"{var}: {value}")
    
    print(f"\n{Colors.BOLD}Secure Variables (masked):{Colors.END}\n")
    secure_vars = [
        'SECRET_KEY',
        'DB_PASSWORD',
        'MTN_API_KEY',
        'MTN_SUBSCRIPTION_KEY',
        'AIRTEL_CLIENT_SECRET',
        'PHONE_ENCRYPTION_KEY',
        'MTN_WEBHOOK_SECRET',
        'AIRTEL_WEBHOOK_SECRET',
    ]
    
    for var in secure_vars:
        value = os.getenv(var)
        if value:
            masked = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "****"
            print(f"{var}: {masked}")
        else:
            print(f"{var}: NOT SET")
    
    print()


def print_usage():
    """Print usage instructions"""
    print_header("PRODUCTION ENVIRONMENT CONFIGURATION HELPER")
    
    print(f"{Colors.BOLD}Usage:{Colors.END}")
    print(f"  python configure_production_env.py --check      # Check current configuration")
    print(f"  python configure_production_env.py --generate   # Generate secure keys")
    print(f"  python configure_production_env.py --validate   # Validate production config")
    print(f"  python configure_production_env.py --help       # Show this help message")
    print()


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print_usage()
        return
    
    command = sys.argv[1].lower()
    
    if command in ['--help', '-h', 'help']:
        print_usage()
    
    elif command in ['--check', '-c', 'check']:
        check_current_config()
    
    elif command in ['--generate', '-g', 'generate']:
        generate_secure_keys()
    
    elif command in ['--validate', '-v', 'validate']:
        check_current_config()
        valid = validate_production_config()
        sys.exit(0 if valid else 1)
    
    else:
        print_error(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == '__main__':
    main()
