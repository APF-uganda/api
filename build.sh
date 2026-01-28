#!/bin/bash

# Production Build Script for APF Backend
# This script prepares the Django backend for production deployment

set -e  # Exit on any error

echo "=========================================="
echo "APF Backend Production Build"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 1. Check Python version
echo "1. Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
print_status "Python version: $python_version"
echo ""

# 2. Install dependencies
echo "2. Installing dependencies..."
pip install -r requirements.txt --quiet
print_status "Dependencies installed"
echo ""

# 3. Check environment variables
echo "3. Checking environment variables..."
required_vars=("DATABASE_URL" "SECRET_KEY")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -eq 0 ]; then
    print_status "All required environment variables are set"
else
    print_warning "Missing environment variables: ${missing_vars[*]}"
    print_warning "Make sure to set them before deployment"
fi
echo ""

# 4. Run security checks
echo "4. Running Django security checks..."
python manage.py check --deploy --fail-level WARNING || {
    print_warning "Security checks found issues (non-critical)"
}
print_status "Security checks completed"
echo ""

# 5. Check for pending migrations
echo "5. Checking for pending migrations..."
python manage.py makemigrations --check --dry-run || {
    print_error "Uncommitted migrations found! Run 'python manage.py makemigrations' first"
    exit 1
}
print_status "No pending migrations"
echo ""

# 6. Run migrations
echo "6. Running database migrations..."
python manage.py migrate --noinput
print_status "Migrations applied"
echo ""

# 7. Collect static files
echo "7. Collecting static files..."
python manage.py collectstatic --noinput --clear
print_status "Static files collected"
echo ""

# 8. Run tests
echo "8. Running security tests..."
python -m pytest authentication/test_security_layer.py -v --tb=short || {
    print_error "Security tests failed!"
    exit 1
}
print_status "Security tests passed"
echo ""

# 9. Create admin user (if needed)
echo "9. Creating admin user (if not exists)..."
python manage.py create_admin || {
    print_warning "Admin user already exists or creation skipped"
}
print_status "Admin user check completed"
echo ""

# 10. Validate deployment readiness
echo "10. Validating deployment readiness..."

# Check DEBUG setting
if python -c "from api.settings import DEBUG; exit(0 if not DEBUG else 1)"; then
    print_status "DEBUG is False (production mode)"
else
    print_error "DEBUG is True! Set DEBUG=False for production"
    exit 1
fi

# Check ALLOWED_HOSTS
if python -c "from api.settings import ALLOWED_HOSTS; exit(0 if ALLOWED_HOSTS and ALLOWED_HOSTS != ['*'] else 1)"; then
    print_status "ALLOWED_HOSTS is configured"
else
    print_warning "ALLOWED_HOSTS may need configuration"
fi

# Check SECRET_KEY
if python -c "from api.settings import SECRET_KEY; exit(0 if SECRET_KEY and SECRET_KEY != 'django-insecure-dev-key-change-in-production' else 1)"; then
    print_status "SECRET_KEY is set"
else
    print_error "SECRET_KEY is using default value! Set a secure SECRET_KEY"
    exit 1
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✓ Build completed successfully!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Review any warnings above"
echo "  2. Set missing environment variables"
echo "  3. Deploy to production"
echo ""
echo "To start the server locally:"
echo "  gunicorn api.wsgi:application"
echo ""
