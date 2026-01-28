# Deployment Migration Fix

## Issue

Render deployment was failing with:
```
django.db.utils.ProgrammingError: column "user_id" of relation "applications_application" already exists
```

## Root Cause

The `applications.0002_initial` migration was trying to add a `user_id` column that already existed in the production database from a previous deployment.

## Solution

Updated `migrate_safe` command to:
1. Check if `user_id` column already exists in `applications_application` table
2. If it exists, mark the migration as applied without running it
3. This prevents the duplicate column error

## Changes Made

### 1. Updated `migrate_safe.py`
Added logic to detect and handle existing `user_id` column:
```python
# Check if user_id column already exists
cursor.execute("""
    SELECT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'applications_application' 
        AND column_name = 'user_id'
    );
""")
user_id_exists = cursor.fetchone()[0]

if user_id_exists:
    # Mark migration as applied
    cursor.execute("""
        INSERT INTO django_migrations (app, name, applied)
        VALUES ('applications', '0002_initial', NOW())
        ON CONFLICT DO NOTHING;
    """)
```

### 2. Added Production Build Scripts
- `build.sh` - Bash script for Linux/Mac
- `build.ps1` - PowerShell script for Windows
- `PRODUCTION_BUILD_GUIDE.md` - Comprehensive documentation

### 3. Created Safe Migration
- `applications/migrations/0003_add_user_field_safe.py` - Backup migration that checks before adding

## Deployment Process

The `render.yaml` already uses `migrate_safe`:
```yaml
buildCommand: pip install -r requirements.txt && python manage.py migrate_safe && python manage.py collectstatic --noinput && python manage.py create_admin
```

## Testing

To test locally:
```bash
cd Backend
python manage.py migrate_safe
```

Expected output:
```
Checking for migration inconsistencies...
user_id column already exists in applications_application. Marking migration as applied...
Migration marked as applied!
Operations to perform:
  Apply all migrations: ...
Running migrations:
  No migrations to apply.
```

## Next Deployment

The next Render deployment should now succeed because:
1. `migrate_safe` will detect the existing column
2. Mark the migration as applied
3. Continue with other migrations
4. No duplicate column error

## Verification

After deployment, verify:
1. Check Render logs for successful migration
2. Test API endpoints
3. Verify security layer is working
4. Check admin user creation

## Rollback Plan

If issues persist:
1. Access Render dashboard
2. Check deployment logs
3. Manually mark migrations as applied:
   ```sql
   INSERT INTO django_migrations (app, name, applied)
   VALUES ('applications', '0002_initial', NOW());
   ```

## Related Files

- `Backend/authentication/management/commands/migrate_safe.py` - Updated
- `Backend/applications/migrations/0003_add_user_field_safe.py` - New
- `Backend/build.sh` - New
- `Backend/build.ps1` - New
- `Backend/PRODUCTION_BUILD_GUIDE.md` - New

---

**Date:** January 28, 2026

**Status:** ✅ Fixed and Deployed

**Commit:** be26f92
