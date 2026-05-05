# Testing Scheduler Changes

## How to Verify Renewal Emails Have Been Removed

### Method 1: Check Management Commands (Quick Test)

SSH into your server and try to run the deleted command:

```bash
# This should FAIL with "Unknown command: send_renewal_reminders"
python manage.py send_renewal_reminders
```

**Expected Result:** ❌ Error message saying the command doesn't exist

If you get an error, it means the command is successfully removed! ✅

### Method 2: Check Available Commands

List all available management commands:

```bash
python manage.py help
```

**Look for:** The `send_renewal_reminders` command should NOT be in the list.

### Method 3: Check Scheduler Logs

After deployment, check the Django logs:

```bash
# Check logs for scheduler activity
docker logs apf-backend | grep Scheduler

# OR if using journalctl
journalctl -u your-django-service | grep Scheduler
```

**What you should see:**
```
[Scheduler] Starting membership renewal scheduler (polling every 24 hours)
```

**What you should NOT see:**
```
[Scheduler] Running daily renewal reminders  ❌ (This should be gone)
```

### Method 4: Code Inspection (Most Reliable)

Check the scheduler file directly on the server:

```bash
# View the scheduler file
cat admin_management/scheduler.py | grep -i "renewal_reminders"
```

**Expected Result:** No matches found ✅

### Method 5: Monitor for 24 Hours

After deployment, monitor logs for 24 hours to ensure:
- ✅ News fetch runs on Monday/Thursday
- ✅ No daily renewal reminder emails are sent
- ✅ No errors about missing send_renewal_reminders command

### Method 6: Check Email Logs

If you have email logging enabled, check that no renewal reminder emails are being sent:

```bash
# Check Django logs for email activity
docker logs apf-backend | grep -i "renewal reminder"
```

**Expected Result:** No renewal reminder emails after deployment ✅

---

## Summary: What to Look For

### ✅ GOOD Signs (Removal Successful):
- Command `send_renewal_reminders` doesn't exist
- No "daily renewal reminders" in scheduler logs
- No renewal reminder emails being sent
- Scheduler only mentions: news fetch, March 1st, March 31st

### ❌ BAD Signs (Removal Failed):
- Command still exists
- Logs show "Running daily renewal reminders"
- Users still receiving daily renewal emails
- Errors about send_renewal_reminders

---

## Quick Test Script

Create this test script on your server:

```bash
#!/bin/bash
echo "=== Testing Scheduler Changes ==="
echo ""
echo "1. Checking if send_renewal_reminders command exists..."
python manage.py send_renewal_reminders 2>&1 | grep -q "Unknown command" && echo "✅ Command removed successfully" || echo "❌ Command still exists"
echo ""
echo "2. Checking scheduler file..."
grep -q "send_renewal_reminders" admin_management/scheduler.py && echo "❌ Still referenced in scheduler" || echo "✅ Not in scheduler"
echo ""
echo "3. Listing all management commands..."
python manage.py help | grep -i renewal
echo ""
echo "=== Test Complete ==="
```

Save as `test_scheduler.sh`, make executable with `chmod +x test_scheduler.sh`, and run it.
