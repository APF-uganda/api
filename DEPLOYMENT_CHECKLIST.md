# Backend Deployment Checklist

Your backend is live at: **https://apf-api.onrender.com**

## ✅ Completed
- [x] Service created and deployed
- [x] Dependencies installed
- [x] Service is running

## ⚠️ To Fix

### 1. Update Build Command
Your current build command only runs `pip install`. Update it to run migrations too.

**Go to:** Render Dashboard → Your Service → Settings

**Find:** Build Command field

**Change to:**
```bash
pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput && python manage.py create_admin
```

**Save Changes** → Trigger Manual Deploy

### 2. Verify Environment Variables

**Go to:** Environment tab

**Check these are set:**
- ✅ `SECRET_KEY` - Should be auto-generated
- ✅ `PYTHON_VERSION` - `3.11.0`
- ✅ `DEBUG` - `False`
- ⚠️ `ALLOWED_HOSTS` - Add: `apf-api.onrender.com`
- ⚠️ `DATABASE_URL` - Must be connected to PostgreSQL database

**If DATABASE_URL is missing:**
1. Create PostgreSQL database (if not done)
2. Add Environment Variable → "Add from Database"
3. Select your database → "Internal Database URL"

### 3. Create/Connect Database

**If you haven't created a database yet:**

1. Go to Render Dashboard
2. Click "New +" → PostgreSQL
3. Name: `apf-database`
4. Region: Oregon (same as backend)
5. Plan: Free
6. Create Database

**Then connect it:**
1. Go to your backend service → Environment
2. Add Environment Variable
3. Click "Add from Database"
4. Select `apf-database`
5. Choose "Internal Database URL"
6. Save

### 4. Add ALLOWED_HOSTS

**Go to:** Environment tab → Add Environment Variable

**Key:** `ALLOWED_HOSTS`
**Value:** `apf-api.onrender.com`

**Save Changes**

### 5. Redeploy

After making all changes:
1. Go to Manual Deploy
2. Click "Deploy latest commit"
3. Wait for build to complete

## Verify Deployment

### Check Health Endpoint
Visit: https://apf-api.onrender.com/

Should return:
```json
{
  "status": "ok",
  "message": "APF Backend API is running",
  "endpoints": {
    "admin": "/admin/",
    "contacts": "/api/contacts/"
  }
}
```

### Check Admin Panel
Visit: https://apf-api.onrender.com/admin/

Should show Django admin login page.

### Check Logs
Go to: Logs tab

Look for:
```
Operations to perform:
  Apply all migrations...
Running migrations:
  Applying contenttypes.0001_initial... OK
  ...
Superuser "admin" created successfully
[INFO] Booting worker with pid: 56
```

## Current Issues

Based on your logs:

1. **400 Bad Request** - Likely because `ALLOWED_HOSTS` doesn't include your domain
2. **No migrations ran** - Build command needs updating
3. **Missing staticfiles** - Will be fixed when collectstatic runs

## After Successful Deployment

1. **Test the API:**
   - Visit: https://apf-api.onrender.com/
   - Should see health check response

2. **Login to Admin:**
   - Visit: https://apf-api.onrender.com/admin/
   - Username: `admin` (or your DJANGO_SUPERUSER_USERNAME)
   - Password: From DJANGO_SUPERUSER_PASSWORD env var

3. **Update Frontend:**
   - Set `VITE_API_URL=https://apf-api.onrender.com` in frontend

4. **Update CORS:**
   - After deploying frontend, add its URL to `CORS_ALLOWED_ORIGINS`

## Need Help?

Check the logs for specific error messages and refer to:
- `FREE_TIER_SETUP.md` - Free tier specific instructions
- `RENDER_ENV_VARS.md` - Environment variables guide
