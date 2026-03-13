# Automated Membership Invoice System

## Overview

The system automatically generates membership renewal invoices on **March 31st** each year and sends them to all active members via email.

## How It Works

### 1. Invoice Generation (March 31st)
- System generates unique invoice numbers for each member
- Creates `MembershipInvoice` records in database
- Sends email with invoice PDF to each member
- Invoice includes:
  - Unique invoice number (e.g., `INV-2026-123-0331120000`)
  - Membership period (April 1, 2026 - March 31, 2027)
  - Amount due: UGX 150,000
  - Due date: 30 days from invoice date

### 2. Payment Processing
- When member pays via MTN/Airtel Money, they reference the invoice number
- Payment system links payment to invoice via `invoice_number` field
- System creates ledger entries:
  - **DEBIT**: Invoice raised (DR: 150,000, CR: 0, Balance: 150,000)
  - **CREDIT**: Payment made (DR: 0, CR: 150,000, Balance: 0)

### 3. Ledger Accounting
- Payment history shows double-entry bookkeeping
- Members can see:
  - When invoice was raised
  - When payment was made
  - Outstanding balance (if any)
  - Full payment history

## Setup Instructions

### Option 1: Linux Cron Job (Recommended for Production)

1. **Edit crontab:**
```bash
crontab -e
```

2. **Add this line** (runs at 6:00 AM on March 31st every year):
```bash
0 6 31 3 * cd /path/to/Backend && /path/to/venv/bin/python manage.py generate_annual_invoices >> /var/log/invoice_generation.log 2>&1
```

3. **Replace paths:**
   - `/path/to/Backend` → Your project directory
   - `/path/to/venv/bin/python` → Your Python virtual environment

4. **Verify cron job:**
```bash
crontab -l
```

### Option 2: Django-Crontab (Alternative)

1. **Install django-crontab:**
```bash
pip install django-crontab
```

2. **Add to `settings.py`:**
```python
INSTALLED_APPS = [
    ...
    'django_crontab',
]

CRONJOBS = [
    # Run at 6:00 AM on March 31st every year
    ('0 6 31 3 *', 'django.core.management.call_command', ['generate_annual_invoices']),
]
```

3. **Add cron jobs:**
```bash
python manage.py crontab add
```

4. **Verify:**
```bash
python manage.py crontab show
```

### Option 3: Celery Beat (For Complex Scheduling)

1. **Install Celery:**
```bash
pip install celery redis
```

2. **Create task in `admin_management/tasks.py`:**
```python
from celery import shared_task
from django.core.management import call_command

@shared_task
def generate_annual_invoices():
    call_command('generate_annual_invoices')
```

3. **Configure in `settings.py`:**
```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'generate-annual-invoices': {
        'task': 'admin_management.tasks.generate_annual_invoices',
        'schedule': crontab(hour=6, minute=0, day_of_month=31, month_of_year=3),
    },
}
```

4. **Run Celery:**
```bash
celery -A api beat --loglevel=info
celery -A api worker --loglevel=info
```

### Option 4: Windows Task Scheduler

1. **Create batch file** (`generate_invoices.bat`):
```batch
@echo off
cd C:\path\to\Backend
C:\path\to\venv\Scripts\python.exe manage.py generate_annual_invoices
```

2. **Open Task Scheduler** → Create Basic Task
3. **Set trigger:** March 31st, 6:00 AM, yearly
4. **Set action:** Run `generate_invoices.bat`

## Manual Execution

### Test Run (Dry Run)
```bash
python manage.py generate_annual_invoices --dry-run
```

### Generate Invoices Without Sending Emails
```bash
python manage.py generate_annual_invoices --no-email
```

### Generate and Send Invoices
```bash
python manage.py generate_annual_invoices
```

## Database Models

### MembershipInvoice
Stores invoice records with:
- `invoice_number`: Unique identifier (e.g., INV-2026-123-0331120000)
- `user`: Member who owes the fee
- `period_start`: April 1st
- `period_end`: March 31st
- `total_amount`: UGX 150,000
- `amount_paid`: Amount paid so far
- `balance_due`: Outstanding balance
- `status`: pending, partial, paid, overdue, cancelled

### Payment Model (Updated)
Added `invoice_number` field to link payments to invoices

### InvoicePaymentLink
Links multiple payments to a single invoice (for partial payments)

## Payment Flow

### 1. Invoice Generated (March 31st)
```
Invoice: INV-2026-123-0331120000
Amount: UGX 150,000
Status: pending
Balance Due: UGX 150,000
```

### 2. Member Pays
```
Payment Reference: INV-2026-123-0331120000
Amount: UGX 150,000
Provider: MTN Mobile Money
```

### 3. System Links Payment to Invoice
```python
# Automatic linking in payment processing
payment.invoice_number = "INV-2026-123-0331120000"
invoice.record_payment(150000)
```

### 4. Ledger Entries Created
```
Date       | Invoice Number          | Description              | DR (UGX) | CR (UGX) | Balance
-----------|-------------------------|--------------------------|----------|----------|----------
31-Mar-26  | INV-2026-123-0331120000 | Membership Renewal Fee   | 150,000  | 0        | 150,000
05-Apr-26  | INV-2026-123-0331120000 | Payment - MTN Money      | 0        | 150,000  | 0
```

## Monitoring

### Check Invoice Generation Status
```bash
python manage.py shell
```

```python
from admin_management.models import MembershipInvoice
from datetime import date

# Check invoices for current year
invoices = MembershipInvoice.objects.filter(
    period_start__year=2026
)

print(f"Total invoices: {invoices.count()}")
print(f"Paid: {invoices.filter(status='paid').count()}")
print(f"Pending: {invoices.filter(status='pending').count()}")
print(f"Overdue: {invoices.filter(status='overdue').count()}")
```

### View Failed Emails
Check logs at `/var/log/invoice_generation.log`

## Troubleshooting

### Invoices Not Generated
1. Check cron job is active: `crontab -l`
2. Check logs: `tail -f /var/log/invoice_generation.log`
3. Verify email settings in `settings.py`
4. Test manually: `python manage.py generate_annual_invoices --dry-run`

### Emails Not Sending
1. Check SMTP settings in `settings.py`
2. Verify email templates exist
3. Check email service credentials
4. Test with single user: `python manage.py send_renewal_invoices --email user@example.com`

### Duplicate Invoices
System prevents duplicates automatically. If invoice exists for the period, it skips creation.

## Migration

Run migrations to create new tables:
```bash
python manage.py makemigrations admin_management
python manage.py migrate
```

## Testing

### Test Invoice Generation
```bash
# Dry run to see what would happen
python manage.py generate_annual_invoices --dry-run

# Generate for test user
python manage.py send_renewal_invoices --email test@example.com
```

### Test Payment Linking
```python
from payments.models import Payment
from admin_management.models import MembershipInvoice

# Create test payment with invoice number
payment = Payment.objects.create(
    user=user,
    amount=150000,
    invoice_number="INV-2026-123-0331120000",
    status='completed'
)

# Verify invoice updated
invoice = MembershipInvoice.objects.get(invoice_number="INV-2026-123-0331120000")
print(f"Amount paid: {invoice.amount_paid}")
print(f"Balance due: {invoice.balance_due}")
print(f"Status: {invoice.status}")
```

## Support

For issues or questions:
1. Check logs: `/var/log/invoice_generation.log`
2. Review Django admin panel for invoice records
3. Test with dry-run mode first
4. Contact system administrator

## Important Dates

- **March 31st**: Invoices generated and sent
- **April 1st**: New membership year begins
- **April 30th**: Payment due date (30 days after invoice)
- **May 1st onwards**: Invoices marked as overdue if unpaid
