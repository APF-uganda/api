# Production Build Guide

## Quick Start

### Windows (PowerShell)
```powershell
cd Backend
.\build.ps1
```

### Linux/Mac (Bash)
```bash
cd Backend
chmod +x build.sh
./build.sh
```

## What the Build Script Does

The production build script performs the following checks and operations:

### 1. ✅ Python Version Check
- Verifies Python is installed and displays version
- Recommended: Python 3.11+

### 2. 📦 Install Dependencies
- Installs all packages from `requirements.txt`
- Ensures all dependencies are up to date

### 3. 🔐 Environment Variables Check
- Verifies required environment variables are set:
  - `DATABASE_URL` - Database connection string
  - `SECRET_KEY` - Django secret key
  - `DEBUG` - Should be False for production
  - `ALLOWED_HOSTS` - List of allowed hostnames

### 4. 🛡️ Security Checks
- Runs Django's built-in security checks
- Validates deployment configuration
- Checks for common security issues

### 5. 🗄️ Database Migrations
- Checks for uncommitted migrations
- Applies all pending migrations
- Ensures database schema is up to date

### 6. 📁 Static Files
- Collects all static files
- Prepares CSS, JS, and other assets for serving
- Clears old static files

### 7. 🧪 Security Tests
- Runs comprehensive security test suite
- Validates authentication and authorization
- Ensures all 14 security tests pass

### 8. 👤 Admin User
- Creates default admin user if not exists
- Uses credentials from environment variables

### 9. ✔️ Deployment Validation
- Verifies DEBUG is False
- Checks ALLOWED_HOSTS configuration
- Validates SECRET_KEY is set
- Confirms production readiness

## Manual Build Commands

If you prefer to run commands manually:

```bash
cd Backend

# 1. Install dependencies
pip install -r requirements.txt

# 2. Run security checks
python manage.py check --deploy

# 3. Check for pending migrations
python manage.py makemigrations --check

# 4. Run migrations
python manage.py migrate

# 5. Collect static files
python manage.py collectstatic --noinput

# 6. Run tests
python -m pytest authentication/test_security_layer.py -v

# 7. Create admin user
python manage.py create_admin
```

## Environment Variables

### Required Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@host:port/database

# Django
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# CORS
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Admin User (for create_admin command)
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=secure-password-here
```

### Optional Variables

```bash
# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Redis (for rate limiting)
REDIS_URL=redis://localhost:6379/1

# EmailJS (frontend only)
EMAILJS_SERVICE_ID=your-service-id
EMAILJS_TEMPLATE_ID_OTP=your-template-id
EMAILJS_PUBLIC_KEY=your-public-key
```

## Production Checklist

Before deploying to production, ensure:

### Security
- [ ] `DEBUG = False` in production
- [ ] `SECRET_KEY` is set to a secure random value
- [ ] `ALLOWED_HOSTS` is configured with your domain
- [ ] HTTPS is enabled
- [ ] CORS is properly configured
- [ ] Database uses SSL connection
- [ ] All security tests pass

### Database
- [ ] Database migrations are applied
- [ ] Database backups are configured
- [ ] Connection pooling is enabled
- [ ] Database credentials are secure

### Static Files
- [ ] Static files are collected
- [ ] Static files are served via CDN or web server
- [ ] WhiteNoise is configured (if not using CDN)

### Authentication
- [ ] JWT tokens are properly configured
- [ ] Token expiration times are set
- [ ] Rate limiting is enabled
- [ ] Admin user is created

### Monitoring
- [ ] Error logging is configured
- [ ] Performance monitoring is set up
- [ ] Authentication logs are accessible
- [ ] Health check endpoint is working

### Testing
- [ ] All tests pass
- [ ] Security tests pass (14/14)
- [ ] Integration tests pass
- [ ] Manual testing completed

## Deployment Platforms

### Render

Your `render.yaml` is already configured. To deploy:

```bash
git push origin main
```

Render will automatically:
1. Run the build command
2. Apply migrations
3. Collect static files
4. Start the server with Gunicorn

### Manual Deployment

If deploying manually:

```bash
# 1. Run build script
./build.sh  # or .\build.ps1 on Windows

# 2. Start server with Gunicorn
gunicorn api.wsgi:application --bind 0.0.0.0:8000 --workers 4

# Or with more options
gunicorn api.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

## Troubleshooting

### Build Script Fails

**Issue: Missing environment variables**
```bash
# Set environment variables
export DATABASE_URL="postgresql://..."
export SECRET_KEY="your-secret-key"
```

**Issue: Tests fail**
```bash
# Run tests with more details
python -m pytest authentication/test_security_layer.py -v --tb=long
```

**Issue: Migration errors**
```bash
# Check migration status
python manage.py showmigrations

# Fake migrations if needed (careful!)
python manage.py migrate --fake
```

### Server Won't Start

**Issue: Port already in use**
```bash
# Find process using port 8000
lsof -i :8000  # Mac/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process or use different port
gunicorn api.wsgi:application --bind 0.0.0.0:8001
```

**Issue: Database connection fails**
```bash
# Test database connection
python manage.py dbshell

# Check DATABASE_URL format
echo $DATABASE_URL
```

### Static Files Not Loading

**Issue: Static files 404**
```bash
# Recollect static files
python manage.py collectstatic --clear --noinput

# Check STATIC_ROOT setting
python manage.py diffsettings | grep STATIC
```

## Performance Optimization

### Gunicorn Workers

Calculate optimal workers:
```
workers = (2 × CPU cores) + 1
```

For 2 CPU cores:
```bash
gunicorn api.wsgi:application --workers 5
```

### Database Connection Pooling

Already configured in `settings.py`:
```python
DATABASES = {
    'default': {
        ...
        'conn_max_age': 600,
        'conn_health_checks': True,
    }
}
```

### Caching

Redis caching is configured for rate limiting. To enable full caching:

```python
# In settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

## Monitoring

### Health Check Endpoint

```bash
curl https://your-domain.com/
```

Should return:
```json
{
  "status": "ok",
  "message": "APF Backend API is running",
  "endpoints": {...}
}
```

### Authentication Logs

Access via admin panel or API:
```bash
curl -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  https://your-domain.com/api/auth/logs
```

### Server Logs

```bash
# View Gunicorn logs
tail -f gunicorn.log

# View Django logs
tail -f django.log
```

## Rollback Procedure

If deployment fails:

```bash
# 1. Revert to previous commit
git revert HEAD
git push origin main

# 2. Or rollback migrations
python manage.py migrate app_name previous_migration_name

# 3. Restart server
sudo systemctl restart gunicorn  # or your process manager
```

## Support

For issues or questions:
1. Check logs: `GET /api/auth/logs` (admin only)
2. Review documentation: `SECURITY_IMPLEMENTATION.md`
3. Run tests: `python -m pytest authentication/test_security_layer.py -v`
4. Check environment variables: `python manage.py diffsettings`

---

**Last Updated:** January 28, 2026

**Build Script Version:** 1.0.0
