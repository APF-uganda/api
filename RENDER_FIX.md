# Quick Fix for Render Migration Issue

## Option 1: Update Build Command in Render Dashboard (RECOMMENDED)

1. Go to your Render dashboard: https://dashboard.render.com
2. Select your `apf-backend` service
3. Go to **Settings** tab
4. Scroll to **Build & Deploy** section
5. Update the **Build Command** to:
   ```bash
   pip install -r requirements.txt && python manage.py migrate_safe && python manage.py collectstatic --noinput && python manage.py create_admin
   ```
6. Click **Save Changes**
7. Go to **Manual Deploy** and click **Deploy latest commit**

## Option 2: Clear Database and Redeploy (NUCLEAR OPTION)

⚠️ **WARNING: This will delete all data in your database!**

1. Go to Render dashboard
2. Select your `apf-db` database
3. Go to **Settings** tab
4. Scroll down and click **Delete Database**
5. Create a new database with the same name
6. Update the DATABASE_URL in your backend service
7. Redeploy

## Option 3: Run SQL Manually via Render Shell

1. Go to your Render dashboard
2. Select your `apf-backend` service
3. Click **Shell** tab
4. Run these commands:
   ```bash
   python manage.py dbshell
   ```
5. In the PostgreSQL shell, run:
   ```sql
   DELETE FROM django_migrations;
   \q
   ```
6. Exit shell and manually deploy again

## What Caused This?

The database had Django's built-in `admin` app migrations applied before your custom `authentication` app migrations. Since `admin` depends on `auth` (which your custom User model replaces), this created a dependency conflict.

The `migrate_safe` command checks for this specific issue and clears the migration history if found, allowing Django to reapply all migrations in the correct order.
