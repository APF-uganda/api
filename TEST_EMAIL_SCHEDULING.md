# Testing Email Scheduling - Verify Renewal Reminders Are Removed

## What We Removed
- ❌ Daily renewal reminder emails for overdue accounts
- ❌ The `send_renewal_reminders` management command
- ❌ The `_run_daily_renewal_reminders()` function from scheduler

## What Should Still Work
- ✅ March 1st: Bulk invoice reminder emails (annual)
- ✅ March 31st: Generate invoices (annual)
- ✅ Monday & Thursday: ICPAU news fetch (twice weekly)

---

## Test 1: Verify Command No Longer Exists

### On Server (SSH):
```bash
# Try to run the removed command - should fail
python manage.py send_renewal_reminders
```

**Expected Result:**
```
Unknown command: 'send_renewal_reminders'
Type 'manage.py help' for usage.
```

✅ **PASS:** Command not found (it's been deleted)
❌ **FAIL:** Command runs (it still exists - not properly removed)

---

## Test 2: Check Available Management Commands

### On Server:
```bash
# List all available commands
python manage.py help
```

**Expected Result:**
You should see these commands but **NOT** `send_renewal_reminders`:
- ✅ `check_expired_subscriptions`
- ✅ `generate_annual_invoices`
- ✅ `send_renewal_invoices`
- ✅ `newsfetch`
- ❌ `send_renewal_reminders` (should NOT appear)

---

## Test 3: Search Codebase for References

### On Your Local Machine:
```bash
# Search for any references to send_renewal_reminders
grep -r "send_renewal_reminders" . --exclude-dir=venv --exclude-dir=node_modules --exclude-dir=.git

# Or on Windows PowerShell:
Select-String -Path . -Pattern "send_renewal_reminders" -Recurse -Exclude *.pyc,*.git
```

**Expected Result:**
```
No matches found
```

✅ **PASS:** No references found
❌ **FAIL:** References found (need to remove them)

---

## Test 4: Check Scheduler Logs

### On Server:
```bash
# Check Django logs for scheduler activity
# Look for the last 100 lines
tail -n 100 /path/to/your/logs/django.log | grep -i "scheduler"

# Or if using Docker:
docker logs apf-backend --tail 100 | grep -i "scheduler"
```

**Expected Log Entries (GOOD):**
```
[Scheduler] Starting membership renewal scheduler (polling every 24 hours)
[Scheduler] Running ICPAU news fetch
[Scheduler] ICPAU news fetch completed
```

**Should NOT See (BAD):**
```
[Scheduler] Running daily renewal reminders
[Scheduler] Daily renewal reminders done
```

---

## Test 5: Verify Scheduler Code

### Check the scheduler.py file:

```bash
# View the scheduler file
cat admin_management/scheduler.py | grep -A 5 "def _run"
```

**Expected Functions:**
- ✅ `_run_news_fetch()` - for ICPAU news
- ✅ `_run_send_reminders()` - for March 1st bulk emails
- ✅ `_run_generate_invoices()` - for March 31st invoices
- ❌ `_run_daily_renewal_reminders()` - should NOT exist

---

## Test 6: Check Scheduler Poll Loop

### View the poll loop logic:
```bash
cat admin_management/scheduler.py | grep -A 30 "def _poll_loop"
```

**Expected Logic:**
```python
# Monday (0) and Thursday (3) — Fetch ICPAU news
if ((_is_target_weekday(0) or _is_target_weekday(3)) and 
    news_fetch_fired_date != today):
    news_fetch_fired_date = today
    t = threading.Thread(target=_run_news_fetch, daemon=True)
    t.start()

# March 1st — bulk invoice reminder emails
if _is_target_date(3, 1) and reminders_fired_year != current_year:
    ...

# March 31st — generate invoices
if _is_target_date(3, 31) and invoices_fired_year != current_year:
    ...
```

**Should NOT See:**
```python
# Daily — renewal reminders
if daily_reminder_fired_date != today:
    daily_reminder_fired_date = today
    t = threading.Thread(target=_run_daily_renewal_reminders, daemon=True)
    t.start()
```

---

## Test 7: Monitor Email Sending (Live Test)

### After Deployment:

1. **Wait 24-48 hours** after deployment
2. **Check email logs** to see what emails are being sent:

```bash
# Check email logs (adjust path to your email log location)
tail -f /var/log/mail.log

# Or check Django logs for email activity
docker logs apf-backend --tail 200 | grep -i "email\|renewal\|reminder"
```

**Expected:**
- ❌ NO daily renewal reminder emails
- ❌ NO overdue account emails
- ✅ Only March 1st and March 31st emails (if those dates)

---

## Test 8: Check Database for Scheduled Tasks

### If using Celery Beat (optional):
```bash
# Check if there are any scheduled tasks for renewal reminders
python manage.py shell
```

```python
from django_celery_beat.models import PeriodicTask
tasks = PeriodicTask.objects.filter(name__icontains='renewal')
for task in tasks:
    print(f"Task: {task.name}, Enabled: {task.enabled}")
```

**Expected:**
- No tasks with "renewal_reminders" or "daily_renewal"
- Only annual tasks (if any)

---

## Test 9: File System Check

### Verify the command file is deleted:
```bash
# Check if the file exists
ls -la admin_management/management/commands/send_renewal_reminders.py
```

**Expected Result:**
```
ls: cannot access 'admin_management/management/commands/send_renewal_reminders.py': No such file or directory
```

✅ **PASS:** File not found (deleted successfully)
❌ **FAIL:** File exists (not deleted)

---

## Test 10: Python Import Test

### On Server:
```bash
python manage.py shell
```

```python
# Try to import the removed command - should fail
try:
    from admin_management.management.commands.send_renewal_reminders import Command
    print("❌ FAIL: Command still exists!")
except ImportError:
    print("✅ PASS: Command has been removed!")
```

**Expected Output:**
```
✅ PASS: Command has been removed!
```

---

## Quick Test Summary Checklist

Run these quick tests after deployment:

```bash
# 1. Command doesn't exist
python manage.py send_renewal_reminders
# Expected: "Unknown command"

# 2. File is deleted
ls admin_management/management/commands/send_renewal_reminders.py
# Expected: "No such file or directory"

# 3. No code references
grep -r "send_renewal_reminders" admin_management/
# Expected: No matches

# 4. Check scheduler logs
docker logs apf-backend --tail 50 | grep -i "renewal"
# Expected: No "daily renewal reminders" messages
```

---

## What to Do If Tests Fail

### If command still exists:
1. Check git status: `git status`
2. Ensure you committed the deletion: `git log --oneline -5`
3. Verify you pushed: `git log origin/main --oneline -5`
4. Pull on server: `git pull origin main`
5. Restart Django: `docker-compose restart apf-backend`

### If references still exist:
1. Search for all references: `grep -r "send_renewal_reminders" .`
2. Remove each reference manually
3. Commit and push changes
4. Redeploy

### If emails still being sent:
1. Check if there's a cron job: `crontab -l`
2. Check if Celery Beat is running old tasks
3. Restart all services: `docker-compose restart`
4. Clear any cached tasks

---

## Monitoring After Deployment

### Week 1: Daily Monitoring
- Check logs daily for any renewal reminder activity
- Monitor email sending logs
- Verify no unexpected emails to users

### Week 2-4: Weekly Monitoring
- Check logs weekly
- Confirm only expected emails (March 1st, March 31st)
- Monitor user complaints about missing emails

### Success Criteria:
✅ No daily renewal reminder emails sent
✅ No errors in logs about missing command
✅ Scheduler runs without issues
✅ News fetch works on Monday & Thursday
✅ Annual emails still work (March 1st & 31st)

---

## Emergency Rollback (If Needed)

If you need to restore the renewal reminders:

```bash
# Restore from git history
git log --all --full-history -- admin_management/management/commands/send_renewal_reminders.py

# Find the commit before deletion
git show <commit-hash>:admin_management/management/commands/send_renewal_reminders.py > admin_management/management/commands/send_renewal_reminders.py

# Restore scheduler changes
git checkout <commit-hash> -- admin_management/scheduler.py

# Commit and push
git add .
git commit -m "Restore renewal reminders"
git push origin main
```

---

## Contact & Support

If you encounter issues:
1. Check the logs first
2. Run all tests above
3. Document what's failing
4. Check git history for changes

**Remember:** The goal is to confirm that daily renewal reminders are completely removed while keeping annual reminders and news fetch working.
