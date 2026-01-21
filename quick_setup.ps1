# Quick Setup Script for Windows PowerShell

Write-Host "=== APF Portal Backend Setup ===" -ForegroundColor Cyan

# Check if virtual environment exists
if (!(Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Create .env if it doesn't exist
if (!(Test-Path ".env")) {
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "Please edit .env file with your SECRET_KEY" -ForegroundColor Red
}

# Create database
Write-Host "Creating PostgreSQL database..." -ForegroundColor Yellow
$env:PGPASSWORD = "Nakaye0@#"
psql -U postgres -c "CREATE DATABASE apf_portal;" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Database created successfully!" -ForegroundColor Green
} else {
    Write-Host "Database might already exist or check PostgreSQL connection" -ForegroundColor Yellow
}

# Run migrations
Write-Host "Running migrations..." -ForegroundColor Yellow
python manage.py makemigrations
python manage.py migrate

Write-Host "`n=== Setup Complete! ===" -ForegroundColor Green
Write-Host "To start the server, run: python manage.py runserver" -ForegroundColor Cyan
Write-Host "To create a superuser, run: python manage.py createsuperuser" -ForegroundColor Cyan
