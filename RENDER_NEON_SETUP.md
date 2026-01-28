# Render + Neon Database Setup Guide

## ✅ Database Successfully Configured

Your application is now using the Neon database:
- **Host**: ep-dry-frog-ah8roofk-pooler.c-3.us-east-1.aws.neon.tech
- **Database**: neondb
- **User**: neondb_owner
- **All migrations applied**: ✅
- **Admin user created**: admin@apf.com / admin123

## Render Environment Variable Setup

### For Render Deployment

Add this **DATABASE_URL** environment variable in your Render dashboard:

**Key**: `DATABASE_URL`  
**Value**: 
```
postgresql://neondb_owner:npg_7QbEFVciI3xB@ep-dry-frog-ah8roofk-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require
```

⚠️ **Note**: Remove `&channel_binding=require` from the connection string for Render. Use only `?sslmode=require`

### Alternative: Individual Environment Variables

If you prefer individual variables, add these to Render:

```
DB_NAME=neondb
DB_USER=neondb_owner
DB_PASSWORD=npg_7QbEFVciI3xB
DB_HOST=ep-dry-frog-ah8roofk-pooler.c-3.us-east-1.aws.neon.tech
DB_PORT=5432
```

## Other Required Render Environment Variables

```
SECRET_KEY=your-production-secret-key-here-change-this
DEBUG=False
ALLOWED_HOSTS=your-app-name.onrender.com,yourdomain.com
CORS_ALLOWED_ORIGINS=https://your-frontend.onrender.com,https://yourdomain.com

EMAILJS_SERVICE_ID=service_algcmhn
EMAILJS_TEMPLATE_ID_OTP=template_le2zqzf
EMAILJS_TEMPLATE_ID_PASSWORD_RESET=template_wdn5ia7
EMAILJS_PUBLIC_KEY=cA_eld2ezDC7RRjxD

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

REDIS_URL=redis://your-redis-url-if-needed
```

## What Was Done

✅ Updated `.env` with Neon database credentials  
✅ Fixed SSL configuration in Django settings  
✅ Applied all migrations to Neon database  
✅ Created superuser account (admin@apf.com / admin123)  
✅ Verified database connection works

## Local Development

Your local `.env` file is now configured to use Neon. To run locally:

```bash
cd Backend
python manage.py runserver
```

## For Render: Connection String

Use this exact connection string in Render's DATABASE_URL:

```
postgresql://neondb_owner:npg_7QbEFVciI3xB@ep-dry-frog-ah8roofk-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require
```

Your database is ready for production! 🚀
