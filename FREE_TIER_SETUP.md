# Render Free Tier Setup Guide

Since you're using the **Free tier** (no Shell access), everything is automated in the build process.

## What Happens Automatically on Deploy

The `buildCommand` in `render.yaml` runs these steps:

1. ✅ `pip install -r requirements.txt` - Install dependencies
2. ✅ `python manage.py migrate` - Run database migrations
3. ✅ `python manage.py collectstatic --noinput` - Collect static files
4. ✅ `python manage.py create_admin` - Create superuser (if doesn't exist)

## Required Environment Variables

Set these in Render Dashboard → Your Service → Environment:

### Must Have:
1. **SECRET_KEY** - Generate in Render (click Generate button)
2. **DEBUG** - Set to `False`
3. **ALLOWED_HOSTS** - Your service URL (e.g., `apf-backend.onrender.com`)
4. **DATABASE_URL** - Add from your PostgreSQL database

### Optional (for admin access):
5. **DJANGO_SUPERUSER_USERNAME** - Default: `admin`
6. **DJANGO_SUPERUSER_EMAIL** - Default: `admin@example.com`
7. **DJANGO_SUPERUSER_PASSWORD** - Default: `changeme123` (CHANGE THIS!)

### After Frontend Deploy:
8. **CORS_ALLOWED_ORIGINS** - Your frontend URL (e.g., `https://apf-portal.onrender.com`)

## Admin User Setup

### Option 1: Use Environment Variables (Recommended)
Set these before first deploy:
```
DJANGO_SUPERUSER_USERNAME=yourusername
DJANGO_SUPERUSER_EMAIL=your@email.com
DJANGO_SUPERUSER_PASSWORD=YourStrongPassword123!
```

### Option 2: Use Defaults
If you don't set the env vars, a default admin will be created:
- Username: `admin`
- Email: `admin@example.com`
- Password: `changeme123`

**⚠️ IMPORTANT**: Change the password immediately after first login!

## Access Your Admin Panel

After successful deployment:
1. Go to: `https://your-backend-url.onrender.com/admin`
2. Login with your superuser credentials
3. Change password if using defaults

## Checking Deployment Status

### View Logs
Go to: Your Service → Logs tab

Look for these success messages:
```
==> Build successful 🎉
==> Deploying...
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, sessions, contacts
Running migrations:
  Applying contenttypes.0001_initial... OK
  ...
Superuser "admin" created successfully
[INFO] Booting worker
[INFO] Listening at: http://0.0.0.0:10000
```

### Common Issues

**"Set the SECRET_KEY environment variable"**
- Add SECRET_KEY in Environment tab

**"DisallowedHost"**
- Add your Render URL to ALLOWED_HOSTS

**"could not connect to server"**
- DATABASE_URL not set or incorrect
- Make sure database is in same region

**"Superuser already exists"**
- This is fine! Admin was created on previous deploy

## Free Tier Limitations

- ❌ No Shell/SSH access
- ❌ Service spins down after 15 min inactivity
- ❌ First request after spin-down takes 30-60 seconds
- ❌ Database expires after 90 days
- ✅ Perfect for testing and development!

## Upgrade Options

If you need Shell access or better performance:
- **Starter**: $7/month (includes Shell, zero downtime, persistent disks)
- **Database**: $7/month (permanent, with backups)

## Re-running Migrations

Migrations run automatically on every deploy. To trigger:
1. Make any small change to your code (or just redeploy)
2. Push to GitHub
3. Render auto-deploys and runs migrations

Or manually trigger:
- Go to: Your Service → Manual Deploy → "Deploy latest commit"
