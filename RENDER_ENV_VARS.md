# Render Environment Variables Setup

After the code changes, go to your Render service and add these environment variables:

## Required Environment Variables

### 1. SECRET_KEY
- **How to set**: Click "Generate" button in Render dashboard
- **Or manually**: Use a long random string (50+ characters)
- **Example**: `django-insecure-a8f7s9d8f7a9s8d7f98as7df98as7df98as7df98as7df`

### 2. DEBUG
- **Value**: `False`
- **Important**: Always False in production

### 3. ALLOWED_HOSTS
- **Value**: `your-service-name.onrender.com`
- **Example**: `apf-backend.onrender.com`
- **Note**: Use the actual URL Render assigns to your service

### 4. DATABASE_URL
- **How to set**: 
  1. Create PostgreSQL database in Render
  2. In your web service → Environment tab
  3. Click "Add Environment Variable"
  4. Select "Add from Database"
  5. Choose your database
  6. Select "Internal Database URL"

### 5. CORS_ALLOWED_ORIGINS
- **Value**: `https://your-frontend-url.onrender.com`
- **Example**: `https://apf-portal.onrender.com`
- **Note**: Add this AFTER deploying your frontend
- **Multiple origins**: Separate with commas: `https://frontend1.com,https://frontend2.com`

## Optional Environment Variables

### PYTHON_VERSION
- **Value**: `3.11.0`
- **Note**: Render auto-detects, but you can specify if needed

## After Setting Environment Variables

1. **Trigger Manual Deploy**
   - Go to your service → Manual Deploy → Deploy latest commit

2. **Run Migrations** (in Shell tab)
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py createsuperuser
   ```

3. **Check Logs**
   - Go to Logs tab to verify successful startup
   - Look for: "Booting worker" and "Listening at: http://0.0.0.0:10000"

## Troubleshooting

If deployment still fails:
- Check all environment variables are set correctly
- Verify DATABASE_URL is connected
- Check logs for specific error messages
- Ensure ALLOWED_HOSTS matches your actual Render URL
