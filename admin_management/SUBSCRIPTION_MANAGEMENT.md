# Subscription Management System

## Overview

The subscription management system automatically handles annual membership renewals and account suspensions for members who haven't paid their subscription fees.

## Features

### 1. Automatic Subscription Date Setting

The system automatically sets the `subscription_due_date` for members in two scenarios:

#### When a New Member is Approved
- When an admin approves a membership application, the system automatically sets the subscription due date to **1 year from the approval date**
- This happens automatically via Django signals in `applications/signals.py`

#### When a Member Pays Their Subscription
- When a payment is marked as completed, the system automatically:
  - Updates the subscription due date to **1 year from the payment date**
  - Reactivates the account if it was suspended
  - Clears any suspension records
- This happens automatically via Django signals in `payments/signals.py`

### 2. Member Suspension

Admins can manually suspend members through the admin panel or API:

**API Endpoint:**
```
PATCH /api/v1/admin-management/members/{member_id}/suspend/
```

**Request Body:**
```json
{
  "reason": "Annual subscription not paid"
}
```

**What Happens When a Member is Suspended:**
- User's `is_active` flag is set to `False`
- A `SuspendedMember` record is created with the suspension reason
- User receives a notification about the suspension
- User cannot log in or access member features until reactivated

### 3. Member Reactivation

Admins can manually reactivate suspended members:

**API Endpoint:**
```
PATCH /api/v1/admin-management/members/{member_id}/reactivate/
```

**What Happens When a Member is Reactivated:**
- User's `is_active` flag is set to `True`
- Suspension record is updated with reactivation timestamp
- User receives a notification about the reactivation
- User can log in and access member features again

**Note:** Members are also automatically reactivated when they complete a payment.

### 4. Automatic Expiration Checking

A management command is available to automatically check for expired subscriptions and suspend members:

**Command:**
```bash
python manage.py check_expired_subscriptions
```

**Options:**
- `--dry-run`: Preview which members would be suspended without making changes

**What It Does:**
- Checks all active members whose `subscription_due_date` has passed
- Automatically suspends them with a standard reason
- Sends notifications to suspended members
- Logs all actions for audit purposes

**Recommended Setup:**
Set up a daily cron job or scheduled task to run this command automatically:

**Linux/Mac (crontab):**
```bash
# Run daily at 2 AM
0 2 * * * cd /path/to/Backend/api && python manage.py check_expired_subscriptions
```

**Windows (Task Scheduler):**
Create a scheduled task that runs daily and executes:
```cmd
cd C:\path\to\Backend\api && python manage.py check_expired_subscriptions
```

## Database Schema

### User Model Fields
- `subscription_due_date` (DateField, nullable): The date when the annual subscription expires

### SuspendedMember Model
- `user` (OneToOne): Link to the suspended user
- `suspension_reason` (TextField): Reason for suspension
- `suspended_at` (DateTime): When the suspension occurred
- `reactivated_at` (DateTime, nullable): When the user was reactivated

## Frontend Integration

The frontend displays:
- Member status (Active/Suspended)
- Subscription renewal date
- Suspend/Reactivate buttons based on current status

**API Response Format:**
```json
{
  "count": 10,
  "results": [
    {
      "id": 1,
      "full_name": "John Doe",
      "email": "john@example.com",
      "phone_number": "+256700000000",
      "membership_status": "ACTIVE",
      "subscription_due_date": "2026-02-17",
      "created_at": "2025-02-17T10:00:00Z"
    }
  ]
}
```

## Testing

### Test Suspension
```bash
# Suspend a member
curl -X PATCH http://localhost:8000/api/v1/admin-management/members/1/suspend/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Test suspension"}'
```

### Test Reactivation
```bash
# Reactivate a member
curl -X PATCH http://localhost:8000/api/v1/admin-management/members/1/reactivate/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test Expiration Check (Dry Run)
```bash
python manage.py check_expired_subscriptions --dry-run
```

## Migration

To apply the database changes:

```bash
cd Backend/api
python manage.py migrate authentication
python manage.py migrate admin_management
```

## Troubleshooting

### Subscription Date Not Set
- Check that signals are properly registered in `apps.py`
- Verify that the application status is 'approved' or payment status is 'completed'
- Check Django logs for any signal errors

### Suspension Not Working
- Verify admin has proper permissions (`IsAdminUser`)
- Check that the member ID is correct
- Review error messages in the API response

### Automatic Expiration Not Running
- Verify the cron job or scheduled task is configured correctly
- Check Django logs for command execution
- Test the command manually first with `--dry-run`
