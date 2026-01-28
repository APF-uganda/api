# CORS Configuration Fix for Production

## Problem
Frontend at `https://apf-uganda.onrender.com` was being blocked by CORS when trying to call backend API at `https://apf-api.onrender.com`.

## Solution
Add CORS configuration to Render environment variables.

## Steps to Fix

### 1. Go to Render Dashboard
- Navigate to https://dashboard.render.com
- Select your backend service: `apf-api`

### 2. Add Environment Variables
Go to **Environment** tab and add these variables:

```
CORS_ALLOWED_ORIGINS=https://apf-uganda.onrender.com,http://localhost:5173
ALLOWED_HOSTS=apf-api.onrender.com,localhost,127.0.0.1
```

**Important Notes:**
- Use commas to separate multiple values (NO SPACES)
- Include `https://` for production URLs
- Include `http://localhost:5173` for local development testing

### 3. Save and Redeploy
- Click **Save Changes**
- Render will automatically redeploy your backend
- Wait 2-3 minutes for deployment to complete

### 4. Verify
After deployment, test your application submission from the frontend.

## What This Does

The `CORS_ALLOWED_ORIGINS` setting tells Django which domains are allowed to make requests to your API:
- `https://apf-uganda.onrender.com` - Your production frontend
- `http://localhost:5173` - Your local development frontend

Without this, browsers block the requests for security reasons (CORS policy).

## Current Configuration

Your Django settings (in `api/settings.py`) reads this from environment variables:

```python
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
)
```

The default only includes localhost, which is why production was failing.
