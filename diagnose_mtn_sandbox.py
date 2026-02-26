"""
Quick diagnostic script for MTN sandbox issues.
Checks common problems and provides solutions.
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()


def check_env_vars():
    """Check environment variables."""
    print("🔍 Checking Environment Variables...")
    print("-" * 50)
    
    vars_to_check = {
        'PAYMENT_ENVIRONMENT': 'Should be "sandbox"',
        'MTN_SUBSCRIPTION_KEY': 'Your MTN subscription key',
        'MTN_API_USER': 'Your MTN API user ID',
        'MTN_API_KEY': 'Your MTN API key',
    }
    
    issues = []
    
    for var, description in vars_to_check.items():
        value = os.getenv(var)
        if value:
            masked = f"{value[:8]}..." if len(value) > 8 else value
            print(f"✓ {var}: {masked}")
        else:
            print(f"✗ {var}: NOT SET")
            print(f"  → {description}")
            issues.append(var)
    
    return len(issues) == 0


def check_django_settings():
    """Check Django settings."""
    print("\n🔍 Checking Django Settings...")
    print("-" * 50)
    
    try:
        from django.conf import settings
        
        # Check CORS
        if hasattr(settings, 'CORS_ALLOWED_ORIGINS'):
            print(f"✓ CORS configured")
            if 'http://localhost:3000' in settings.CORS_ALLOWED_ORIGINS:
                print(f"  → Frontend origin allowed")
            else:
                print(f"  ⚠️  Frontend origin (http://localhost:3000) not in CORS_ALLOWED_ORIGINS")
        
        # Check database
        print(f"✓ Database: {settings.DATABASES['default']['ENGINE']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error checking settings: {e}")
        return False


def check_mtn_service():
    """Check MTN service."""
    print("\n🔍 Checking MTN Service...")
    print("-" * 50)
    
    try:
        from payments.services.mtn_service import MTNService, MTNConfig
        
        config = MTNConfig()
        
        if not config.is_configured():
            print("✗ MTN not configured")
            return False
        
        print(f"✓ MTN configured")
        print(f"  → Environment: {config.target_environment}")
        print(f"  → Base URL: {config.base_url}")
        
        # Test authentication
        print("\n  Testing authentication...")
        mtn = MTNService()
        
        try:
            token = mtn._get_access_token()
            if token:
                print(f"  ✓ Authentication successful")
                print(f"    → Token: {token[:30]}...")
                return True
            else:
                print(f"  ✗ Authentication failed - no token")
                return False
        except Exception as e:
            print(f"  ✗ Authentication failed: {e}")
            
            # Check for common errors
            error_str = str(e).lower()
            if 'unauthorized' in error_str or '401' in error_str:
                print("\n  💡 Solution: Check your MTN_API_USER and MTN_API_KEY")
                print("     They should match the credentials from MTN developer portal")
            elif 'subscription' in error_str or '403' in error_str:
                print("\n  💡 Solution: Check your MTN_SUBSCRIPTION_KEY")
                print("     It should be the Primary Key from your MTN product subscription")
            elif 'timeout' in error_str or 'connection' in error_str:
                print("\n  💡 Solution: Check your internet connection")
                print("     MTN sandbox may also be temporarily unavailable")
            
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def check_database():
    """Check database and migrations."""
    print("\n🔍 Checking Database...")
    print("-" * 50)
    
    try:
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        
        # Check connection
        connection.ensure_connection()
        print("✓ Database connection successful")
        
        # Check migrations
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        
        if plan:
            print(f"⚠️  {len(plan)} unapplied migrations")
            print("  → Run: python manage.py migrate")
            return False
        else:
            print("✓ All migrations applied")
            return True
            
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False


def check_payment_endpoint():
    """Check if payment endpoint is accessible."""
    print("\n🔍 Checking Payment Endpoint...")
    print("-" * 50)
    
    try:
        from django.urls import reverse
        from django.test import RequestFactory
        from payments.views import PaymentInitiationView
        
        print("✓ Payment views imported successfully")
        
        # Try to create a test request
        factory = RequestFactory()
        request = factory.post('/api/v1/payments/initiate/', 
                              data={'phone_number': '256774000001', 'provider': 'mtn', 'amount': 50000},
                              content_type='application/json')
        
        print("✓ Payment endpoint is accessible")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def provide_recommendations(results):
    """Provide recommendations based on results."""
    print("\n" + "=" * 50)
    print("📋 RECOMMENDATIONS")
    print("=" * 50)
    
    if all(results.values()):
        print("\n✅ Everything looks good!")
        print("\nNext steps:")
        print("  1. Run: python Backend/test_mtn_sandbox_complete.py")
        print("  2. Or use: .\\test_payment_initiation.ps1")
        print("  3. Check logs if payment fails")
    else:
        print("\n⚠️  Issues found. Fix these first:")
        
        if not results['env_vars']:
            print("\n1. Set environment variables:")
            print("   - Copy .env.example to .env")
            print("   - Fill in your MTN credentials")
            print("   - Set PAYMENT_ENVIRONMENT=sandbox")
        
        if not results['database']:
            print("\n2. Run database migrations:")
            print("   cd Backend")
            print("   python manage.py migrate")
        
        if not results['mtn_service']:
            print("\n3. Verify MTN credentials:")
            print("   - Check MTN developer portal")
            print("   - Ensure credentials are correct")
            print("   - Test authentication manually")
    
    print("\n📚 Documentation:")
    print("  - Backend/mtn-momo-api-integration-documentations/")
    print("  - Backend/MTN_SANDBOX_TEST_RESULTS.md")


def main():
    """Run all diagnostics."""
    print("=" * 50)
    print("MTN SANDBOX DIAGNOSTICS")
    print("=" * 50)
    
    results = {
        'env_vars': check_env_vars(),
        'django_settings': check_django_settings(),
        'mtn_service': check_mtn_service(),
        'database': check_database(),
        'payment_endpoint': check_payment_endpoint(),
    }
    
    provide_recommendations(results)
    
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nDiagnostics cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
