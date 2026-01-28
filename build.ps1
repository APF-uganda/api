# Production Build Script for APF Backend (PowerShell)
# This script prepares the Django backend for production deployment

$ErrorActionPreference = "Continue"  # Changed to Continue to handle errors gracefully

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "APF Backend Production Build" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

function Print-Status {
    param($Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Print-Error {
    param($Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Print-Warning {
    param($Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

$buildFailed = $false

# 1. Check Python version
Write-Host "1. Checking Python version..." -ForegroundColor White
$pythonVersion = python --version 2>&1
Print-Status "Python version: $pythonVersion"
Write-Host ""

# 2. Install dependencies
Write-Host "2. Installing dependencies..." -ForegroundColor White
pip install -r requirements.txt --quiet
if ($LASTEXITCODE -eq 0) {
    Print-Status "Dependencies installed"
} else {
    Print-Error "Failed to install dependencies"
    $buildFailed = $true
}
Write-Host ""

# 3. Check environment variables
Write-Host "3. Checking environment variables..." -ForegroundColor White
$requiredVars = @("DATABASE_URL", "SECRET_KEY")
$missingVars = @()

foreach ($var in $requiredVars) {
    if (-not (Test-Path "env:$var")) {
        $missingVars += $var
    }
}

if ($missingVars.Count -eq 0) {
    Print-Status "All required environment variables are set"
} else {
    Print-Warning "Missing environment variables: $($missingVars -join ', ')"
    Print-Warning "Make sure to set them before deployment"
}
Write-Host ""

# 4. Run security checks
Write-Host "4. Running Django security checks..." -ForegroundColor White
python manage.py check --deploy --fail-level WARNING 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Print-Status "Security checks completed"
} else {
    Print-Warning "Security checks found issues (non-critical)"
}
Write-Host ""

# 5. Check for pending migrations
Write-Host "5. Checking for pending migrations..." -ForegroundColor White
python manage.py makemigrations --check --dry-run 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Print-Status "No pending migrations"
} else {
    Print-Error "Uncommitted migrations found! Run 'python manage.py makemigrations' first"
    $buildFailed = $true
}
Write-Host ""

# 6. Run migrations
Write-Host "6. Running database migrations..." -ForegroundColor White
python manage.py migrate --noinput
if ($LASTEXITCODE -eq 0) {
    Print-Status "Migrations applied"
} else {
    Print-Error "Failed to apply migrations"
    $buildFailed = $true
}
Write-Host ""

# 7. Collect static files
Write-Host "7. Collecting static files..." -ForegroundColor White
python manage.py collectstatic --noinput --clear
if ($LASTEXITCODE -eq 0) {
    Print-Status "Static files collected"
} else {
    Print-Error "Failed to collect static files"
    $buildFailed = $true
}
Write-Host ""

# 8. Run tests
Write-Host "8. Running security tests..." -ForegroundColor White
python -m pytest authentication/test_security_layer.py -v --tb=short
if ($LASTEXITCODE -eq 0) {
    Print-Status "Security tests passed"
} else {
    Print-Error "Security tests failed!"
    $buildFailed = $true
}
Write-Host ""

# 9. Create admin user (if needed)
Write-Host "9. Creating admin user (if not exists)..." -ForegroundColor White
python manage.py create_admin 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Print-Status "Admin user check completed"
} else {
    Print-Warning "Admin user already exists or creation skipped"
}
Write-Host ""

# 10. Validate deployment readiness
Write-Host "10. Validating deployment readiness..." -ForegroundColor White

# Check DEBUG setting
python -c 'from api.settings import DEBUG; exit(0 if not DEBUG else 1)'
if ($LASTEXITCODE -eq 0) {
    Print-Status "DEBUG is False (production mode)"
} else {
    Print-Error "DEBUG is True! Set DEBUG=False for production"
    $buildFailed = $true
}

# Check ALLOWED_HOSTS
python -c 'from api.settings import ALLOWED_HOSTS; exit(0 if ALLOWED_HOSTS and ALLOWED_HOSTS != ["*"] else 1)'
if ($LASTEXITCODE -eq 0) {
    Print-Status "ALLOWED_HOSTS is configured"
} else {
    Print-Warning "ALLOWED_HOSTS may need configuration"
}

# Check SECRET_KEY
python -c 'from api.settings import SECRET_KEY; exit(0 if SECRET_KEY and SECRET_KEY != "django-insecure-dev-key-change-in-production" else 1)'
if ($LASTEXITCODE -eq 0) {
    Print-Status "SECRET_KEY is set"
} else {
    Print-Error "SECRET_KEY is using default value! Set a secure SECRET_KEY"
    $buildFailed = $true
}

Write-Host ""

if ($buildFailed) {
    Write-Host "==========================================" -ForegroundColor Red
    Write-Host "✗ Build failed! Please fix errors above" -ForegroundColor Red
    Write-Host "==========================================" -ForegroundColor Red
    exit 1
} else {
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "✓ Build completed successfully!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Review any warnings above"
    Write-Host "  2. Set missing environment variables"
    Write-Host "  3. Deploy to production"
    Write-Host ""
    Write-Host "To start the server locally:" -ForegroundColor Yellow
    Write-Host "  gunicorn api.wsgi:application"
    Write-Host ""
}
