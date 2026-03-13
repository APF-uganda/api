# Test Data Cleanup Guide

## Overview
This guide explains how to safely remove test/dummy data while preserving all business logic and functionality.

## What Will Be Deleted
- ✗ Test membership invoices
- ✗ Test invoice-payment links
- ✗ Test payment records (membership_fee, event_registration types)

## What Will Be Preserved
- ✓ All models and database schema
- ✓ All business logic and methods
- ✓ All API endpoints and views
- ✓ All serializers and validators
- ✓ All signals and automation
- ✓ All management commands
- ✓ All admin configurations
- ✓ All email templates
- ✓ User accounts (unless specified otherwise)
- ✓ All frontend components and services

## Preserved Functionality

### 1. Invoice Management
- ✓ MembershipInvoice model with all methods
- ✓ Invoice generation logic
- ✓ Invoice status tracking (pending, partial, paid, overdue, cancelled)
- ✓ Balance calculation
- ✓ Payment percentage tracking
- ✓ Email notification system

### 2. Payment Processing
- ✓ Payment model with all payment types
- ✓ MTN MoMo integration
- ✓ Airtel Money integration
- ✓ Payment reconciliation logic
- ✓ Transaction reference generation
- ✓ Payment status tracking

### 3. Invoice-Payment Linking
- ✓ InvoicePaymentLink model
- ✓ Automatic linking via signals
- ✓ Partial payment support
- ✓ Multiple payments per invoice
- ✓ Payment allocation logic

### 4. Automation
- ✓ Annual invoice generation command
- ✓ Renewal email sending command
- ✓ Payment reconciliation signals
- ✓ Status update automation

### 5. Admin Interface
- ✓ Invoice admin with custom displays
- ✓ Payment link admin
- ✓ Bulk actions (mark as paid, cancelled)
- ✓ Email resend functionality
- ✓ Payment progress visualization

### 6. API Endpoints
- ✓ GET /api/admin/membership-invoices/
- ✓ POST /api/admin/membership-invoices/
- ✓ GET /api/admin/membership-invoices/{id}/
- ✓ PATCH /api/admin/membership-invoices/{id}/
- ✓ POST /api/admin/membership-invoices/generate-annual/
- ✓ POST /api/admin/membership-invoices/send-renewal-emails/
- ✓ GET /api/payments/
- ✓ POST /api/payments/initiate/
- ✓ POST /api/payments/mtn/callback/
- ✓ POST /api/payments/airtel/callback/

### 7. Frontend Components
- ✓ MembershipInvoices page
- ✓ GenerateMembershipInvoice page
- ✓ PaymentsPage
- ✓ PaymentHistoryPage
- ✓ Invoice display components
- ✓ Payment forms and modals
- ✓ Receipt generation

## How to Clean Up

### Step 1: Preview (Dry Run)
```bash
cd Backend
python manage.py cleanup_test_data --dry-run
```

This shows what will be deleted without actually deleting anything.

### Step 2: Backup (Recommended)
```bash
# Backup your database
python manage.py dumpdata > backup_before_cleanup.json

# Or backup specific apps
python manage.py dumpdata admin_management payments > backup_invoices_payments.json
```

### Step 3: Execute Cleanup
```bash
python manage.py cleanup_test_data --confirm
```

### Step 4: Verify
```bash
# Check that data is removed
python manage.py shell
>>> from admin_management.models import MembershipInvoice
>>> MembershipInvoice.objects.count()
0

# Verify logic still works
>>> from authentication.models import User
>>> user = User.objects.first()
>>> from admin_management.membership_renewal_service import MembershipRenewalService
>>> invoice = MembershipRenewalService.generate_membership_invoice(user)
>>> print(invoice.invoice_number)
INV-2026-...
```

## Post-Cleanup Testing

### 1. Test Invoice Generation
```bash
python manage.py generate_annual_invoices --year 2026
```

### 2. Test Payment Flow
1. Create a test invoice via admin or API
2. Initiate a payment
3. Verify payment links to invoice
4. Check invoice status updates

### 3. Test Email Sending
```bash
python manage.py send_renewal_invoices --year 2026
```

## Rollback (If Needed)
If something goes wrong, restore from backup:
```bash
python manage.py loaddata backup_before_cleanup.json
```

## Production Deployment Checklist

After cleanup, before deploying to production:

- [ ] All tests pass
- [ ] Invoice generation works
- [ ] Payment processing works
- [ ] Email sending works
- [ ] Admin interface accessible
- [ ] API endpoints respond correctly
- [ ] Frontend displays correctly
- [ ] Signals trigger properly
- [ ] Database migrations applied
- [ ] Environment variables set

## Notes

- This cleanup is safe and reversible (with backup)
- All code remains intact
- All functionality remains operational
- Only test data records are removed
- User accounts are preserved by default
- You can regenerate test data anytime using the management commands

## Support

If you encounter issues:
1. Check the backup was created
2. Review the dry-run output
3. Verify database connections
4. Check Django logs
5. Test individual components

## Next Steps

After cleanup:
1. Generate fresh invoices for current year
2. Test payment flow with real transactions
3. Monitor email delivery
4. Set up automated invoice generation (cron/celery)
5. Configure production payment gateways
