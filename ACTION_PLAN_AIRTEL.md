# Airtel Money - Action Plan

## 🎯 Goal
Get Airtel Money payments working in your APF Portal

## ⏱️ Time Required
**Total: 10-15 minutes** (mostly waiting for Airtel approval)

---

## 📋 Step-by-Step Action Plan

### Step 1: Get Airtel Credentials (5-10 minutes)

**Time:** 5-10 minutes (includes waiting for approval)

**Actions:**
1. Open browser and go to: https://developers.airtel.africa/
2. Click "Sign Up" or "Register"
3. Fill in registration form:
   - Email: Your email
   - Password: Create strong password
   - Name: Your name
   - Country: Uganda
4. Verify email (check inbox/spam)
5. Log in to developer portal
6. Click "Create Application" or "New App"
7. Fill in application form:
   - Name: "APF Portal Test"
   - Description: "Testing mobile money integration"
   - Environment: **Sandbox/UAT** (important!)
   - Products: Select "Collections"
8. Submit application
9. Wait for approval (usually instant for sandbox)
10. Go to application → Credentials
11. Copy Client ID
12. Copy Client Secret

**Expected Result:**
- ✅ You have Client ID
- ✅ You have Client Secret

**If stuck:** See `airtel-documentation/AIRTEL_SANDBOX_APPROVAL.md`

---

### Step 2: Add Credentials to .env (1 minute)

**Time:** 1 minute

**Actions:**
1. Open file: `Backend/api/.env`
2. Find the Airtel section (at the bottom)
3. Replace empty values:
   ```bash
   AIRTEL_CLIENT_ID=paste-your-client-id-here
   AIRTEL_CLIENT_SECRET=paste-your-client-secret-here
   ```
4. Save file

**Optional but recommended:**
Generate webhook secret:
```powershell
# PowerShell
$bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
[Convert]::ToBase64String($bytes)
```

Add to .env:
```bash
AIRTEL_WEBHOOK_SECRET=paste-generated-secret-here
```

**Expected Result:**
- ✅ .env file updated
- ✅ No syntax errors
- ✅ File saved

---

### Step 3: Test Authentication (30 seconds)

**Time:** 30 seconds

**Actions:**
1. Open terminal/PowerShell
2. Navigate to Backend/api:
   ```bash
   cd Backend/api
   ```
3. Activate virtual environment:
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```
4. Run authentication test:
   ```bash
   python test_airtel_auth.py
   ```

**Expected Output:**
```
✓ AIRTEL_CLIENT_ID: a1b2c3d4...
✓ AIRTEL_CLIENT_SECRET: AbCdEfGh...
✓ Authentication successful!
✅ AIRTEL AUTHENTICATION TEST PASSED
```

**If failed:**
- Check credentials are correct
- Verify no extra spaces in .env
- Check internet connection
- Try regenerating credentials

---

### Step 4: Full Verification (1 minute)

**Time:** 1 minute

**Actions:**
1. Run full verification script:
   ```bash
   python verify_airtel_setup.py
   ```

**Expected Output:**
```
✓ PASS: Environment Variables
✓ PASS: API Authentication
✓ PASS: Database Models
✓ PASS: Payment Service
✓ PASS: Webhook Endpoint
✓ PASS: Test Payment
✅ ALL CHECKS PASSED - AIRTEL INTEGRATION READY!
```

**If any check fails:**
- Read the error message
- Follow suggested actions
- Check `AIRTEL_SETUP_CHECKLIST.md`

---

### Step 5: Test Payment Flow (2 minutes)

**Time:** 2 minutes

**Option A: Django Shell Test**

1. Start Django shell:
   ```bash
   python manage.py shell
   ```

2. Run test payment:
   ```python
   from decimal import Decimal
   import uuid
   from payments.services.airtel_service import AirtelService
   
   # Initialize service
   airtel = AirtelService()
   
   # Generate IDs
   ref = str(uuid.uuid4())
   tx_id = str(uuid.uuid4())
   
   # Test payment with sandbox number
   result = airtel.request_to_pay(
       phone_number="256700000001",  # Test number
       amount=Decimal("5000"),
       currency="UGX",
       reference=ref,
       transaction_id=tx_id
   )
   
   print(result)
   
   # Check status
   import time
   time.sleep(3)
   status = airtel.check_payment_status(tx_id)
   print(status)
   ```

**Expected Result:**
```python
{
    'success': True,
    'transaction_reference': '...',
    'message': 'Payment request sent...'
}
```

**Option B: Frontend Test**

1. Start Django server:
   ```bash
   python manage.py runserver
   ```

2. Open frontend application

3. Go to registration or payment page

4. Select "Airtel Money"

5. Enter test phone: `256700000001`

6. Submit payment

7. Check status updates

**Expected Result:**
- ✅ Payment initiated
- ✅ Status shows "pending"
- ✅ Eventually shows "completed"

---

### Step 6: Verify Database (1 minute)

**Time:** 1 minute

**Actions:**
1. Open Django shell:
   ```bash
   python manage.py shell
   ```

2. Check payments:
   ```python
   from payments.models import Payment
   
   # Check Airtel payments
   airtel_payments = Payment.objects.filter(provider='airtel')
   print(f"Total Airtel payments: {airtel_payments.count()}")
   
   # Check latest
   latest = airtel_payments.order_by('-created_at').first()
   if latest:
       print(f"Status: {latest.status}")
       print(f"Amount: {latest.amount}")
       print(f"Phone: {latest.get_masked_phone()}")
   ```

**Expected Result:**
- ✅ Payments are being created
- ✅ Status updates correctly
- ✅ Phone numbers are masked

---

## ✅ Success Checklist

After completing all steps, verify:

- [ ] Airtel credentials obtained
- [ ] Credentials added to .env
- [ ] test_airtel_auth.py passes
- [ ] verify_airtel_setup.py passes
- [ ] Test payment successful
- [ ] Database records created
- [ ] Status updates working
- [ ] No errors in logs

---

## 🎯 Test Scenarios

### Scenario 1: Successful Payment
```
Phone: 256700000001
Expected: Payment succeeds
```

### Scenario 2: Insufficient Funds
```
Phone: 256700000002
Expected: Payment fails with "Insufficient funds"
```

### Scenario 3: Timeout
```
Phone: 256700000003
Expected: Payment times out
```

---

## 🔧 Troubleshooting

### Issue: "Module not found: dotenv"
**Solution:**
```bash
pip install python-dotenv
```

### Issue: "401 Unauthorized"
**Causes:**
- Wrong credentials
- Extra spaces in .env
- Wrong environment (sandbox vs production)

**Solution:**
1. Verify credentials in Airtel portal
2. Check .env file for spaces
3. Ensure PAYMENT_ENVIRONMENT=sandbox

### Issue: "Authentication failed"
**Causes:**
- Network issues
- Airtel API down
- Invalid credentials

**Solution:**
1. Check internet connection
2. Try again in a few minutes
3. Regenerate credentials
4. Contact Airtel support

### Issue: "Payment not found"
**Causes:**
- Transaction reference mismatch
- Payment not created
- Database issue

**Solution:**
1. Check transaction reference
2. Verify payment in database
3. Check logs for errors

---

## 📊 Progress Tracking

Mark your progress:

- [ ] Step 1: Get credentials
- [ ] Step 2: Add to .env
- [ ] Step 3: Test authentication
- [ ] Step 4: Full verification
- [ ] Step 5: Test payment
- [ ] Step 6: Verify database
- [ ] ✅ All done!

---

## 🎉 What Happens After Success

Once all steps pass:

### Immediate
- ✅ Airtel payments work
- ✅ Can test all scenarios
- ✅ Can develop features
- ✅ Can integrate with frontend

### Short Term
- Test error scenarios
- Test retry mechanism
- Test webhook delivery
- Review logs
- Document findings

### Medium Term
- Complete sandbox testing
- Apply for production credentials
- Plan production deployment
- Set up monitoring
- Train support team

---

## 📚 Reference Documents

### Quick Reference
- `AIRTEL_QUICK_START.md` - Fast setup
- `MISSING_FOR_AIRTEL.md` - What's missing
- `AIRTEL_STATUS_SUMMARY.md` - Current status

### Detailed Guides
- `AIRTEL_SETUP_CHECKLIST.md` - Complete checklist
- `airtel-documentation/AIRTEL_SANDBOX_APPROVAL.md` - Get credentials
- `airtel-documentation/AIRTEL_MONEY_API_SETUP_GUIDE.md` - Full guide
- `airtel-documentation/AIRTEL_SANDBOX_TESTING_GUIDE.md` - Testing

### Scripts
- `test_airtel_auth.py` - Test authentication
- `verify_airtel_setup.py` - Full verification

---

## 🆘 Need Help?

### During Setup
1. Check error messages carefully
2. Review relevant documentation
3. Run verification script
4. Check logs

### Getting Credentials
- Portal: https://developers.airtel.africa/
- Guide: `airtel-documentation/AIRTEL_SANDBOX_APPROVAL.md`
- Support: support@airtel.africa

### Technical Issues
- Run: `python verify_airtel_setup.py`
- Check: Console logs
- Review: Error messages
- Consult: Documentation

---

## 🚀 Ready to Start?

**Current Status:** Ready to begin

**First Step:** Get Airtel credentials

**Time Required:** 10-15 minutes

**Difficulty:** Easy

**Result:** Working Airtel payments!

---

**Let's do this!** 💪

Start with Step 1: Visit https://developers.airtel.africa/
