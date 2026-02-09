# Airtel Money Sandbox Testing Guide

Complete guide for testing Airtel Money integration in sandbox environment.

**Requirements: 11.2, 11.4, 2.1-2.10, 6.1-6.10**

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Sandbox Credentials Setup](#sandbox-credentials-setup)
3. [Test Phone Numbers](#test-phone-numbers)
4. [Running Tests](#running-tests)
5. [Test Scenarios](#test-scenarios)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before testing, ensure you have:

- ✅ Airtel Developer account (https://developers.airtel.africa/)
- ✅ Sandbox application created and approved
- ✅ Client ID and Client Secret from developer portal
- ✅ Django environment set up
- ✅ Database migrations run

---

## Sandbox Credentials Setup

### Option 1: Interactive Setup Script (Recommended)

```bash
cd Backend
python setup_airtel_credentials.py
```

This script will:
1. Guide you through credential entry
2. Test authentication
3. Update your `.env` file
4. Verify the setup

### Option 2: Manual Setup

1. **Get Credentials from Airtel Developer Portal:**
   - Go to https://developers.airtel.africa/
   - Log in to your account
   - Navigate to your application
   - Copy Client ID and Client Secret

2. **Update Backend/.env:**
   ```bash
   # Airtel Money API (sandbox)
   AIRTEL_CLIENT_ID=your-client-id-here
   AIRTEL_CLIENT_SECRET=your-client-secret-here
   PAYMENT_ENVIRONMENT=sandbox
   ```

3. **Verify Setup:**
   ```bash
   python test_airtel_sandbox_setup.py
   ```

---

## Test Phone Numbers

Airtel provides specific test phone numbers for sandbox testing:

| Phone Number | Expected Behavior | Use Case |
|--------------|-------------------|----------|
| 256700000001 | ✅ Approves payment | Test successful payment flow |
| 256700000002 | ❌ Rejects (insufficient funds) | Test insufficient funds error |
| 256700000003 | ⏱️ Times out | Test timeout handling |

**Important Notes:**
- Test numbers may not trigger actual USSD prompts on your phone
- Sandbox responses are simulated by Airtel
- Test numbers may change - check Airtel documentation for updates
- Use format: 256XXXXXXXXX (with country code)

---

## Running Tests

### 1. Quick Verification Test

Test your sandbox setup:

```bash
cd Backend
python test_airtel_sandbox_setup.py
```

Expected output:
```
[Step 1] Checking Environment Variables
✓ AIRTEL_CLIENT_ID: a1b2c3d4...
✓ AIRTEL_CLIENT_SECRET: AbCdEfGh...
✓ PAYMENT_ENVIRONMENT: sandbox

[Step 2] Testing Authentication
✓ Authentication successful!

[Step 3] Testing Payment Initiation
✓ Payment initiation successful!

[Step 4] Testing Payment Status Check
✓ Status check successful!

[Step 5] Testing Error Scenarios
✓ Error handling tests completed

✅ Your Airtel sandbox integration is working!
```

### 2. End-to-End Integration Tests

Run comprehensive E2E tests:

```bash
# Test successful payment flow
pytest Backend/payments/test_e2e_airtel_successful_payment.py -v

# Test failed payment scenarios
pytest Backend/payments/test_e2e_airtel_failed_payment.py -v

# Test provider switching
pytest Backend/payments/test_e2e_provider_switching.py -v

# Run all Airtel tests
pytest Backend/payments/test_e2e_airtel_*.py -v
```

### 3. Unit Tests

Test Airtel service in isolation:

```bash
pytest Backend/payments/test_airtel_service.py -v
```

### 4. Manual API Testing

Test through Django shell:

```bash
python manage.py shell
```

```python
from decimal import Decimal
import uuid
from payments.services.airtel_service import AirtelService

# Initialize service
airtel = AirtelService()

# Test authentication
token = airtel._get_access_token()
print(f"Token: {token[:30]}...")

# Test payment initiation
ref = str(uuid.uuid4())
tx_id = str(uuid.uuid4())

result = airtel.request_to_pay(
    phone_number="256700000001",  # Test number
    amount=Decimal("5000"),
    currency="UGX",
    reference=ref,
    transaction_id=tx_id
)

print(f"Initiation: {result}")

# Test status check
status = airtel.check_payment_status(tx_id)
print(f"Status: {status}")
```

---

## Test Scenarios

### Scenario 1: Successful Payment (Requirements 2.1-2.10)

**Test:** Complete payment flow from initiation to completion

```bash
pytest Backend/payments/test_e2e_airtel_successful_payment.py::TestAirtelSuccessfulPaymentE2E::test_airtel_successful_payment_flow -v
```

**Expected Flow:**
1. ✅ Payment initiated with status='pending'
2. ✅ Status check returns 'TIP' (Transaction In Progress)
3. ✅ Status check returns 'TS' (Transaction Successful)
4. ✅ Payment record updated with status='completed'
5. ✅ Provider transaction ID stored
6. ✅ Completion timestamp recorded

### Scenario 2: Insufficient Funds (Requirements 2.8, 6.5)

**Test:** Payment fails due to insufficient balance

```bash
pytest Backend/payments/test_e2e_airtel_failed_payment.py::TestAirtelFailedPaymentE2E::test_airtel_failed_payment_insufficient_funds -v
```

**Expected Flow:**
1. ✅ Payment initiated successfully
2. ✅ Status check returns 'TF' (Transaction Failed)
3. ✅ Error message: "Insufficient funds in your Airtel Money account"
4. ✅ Payment status updated to 'failed'
5. ✅ Payment can be retried

### Scenario 3: User Cancellation (Requirements 2.8, 6.4)

**Test:** User cancels payment on their phone

```bash
pytest Backend/payments/test_e2e_airtel_failed_payment.py::TestAirtelFailedPaymentE2E::test_airtel_failed_payment_user_cancelled -v
```

**Expected Flow:**
1. ✅ Payment initiated successfully
2. ✅ Status check returns 'TF' with 'USER_CANCELLED'
3. ✅ Error message: "Payment cancelled by user"
4. ✅ Payment status updated to 'failed'
5. ✅ Payment can be retried

### Scenario 4: Payment Timeout (Requirements 1.9, 4.6)

**Test:** Payment times out after 90 seconds

```bash
pytest Backend/payments/test_e2e_timeout.py -v
```

**Expected Flow:**
1. ✅ Payment initiated successfully
2. ✅ Status remains 'TIP' for 30 polls (90 seconds)
3. ✅ Payment marked as 'timeout'
4. ✅ User can retry payment

### Scenario 5: Payment Retry (Requirements 12.1-12.7)

**Test:** Failed payment is retried successfully

```bash
pytest Backend/payments/test_e2e_airtel_failed_payment.py::TestAirtelFailedPaymentE2E::test_airtel_failed_payment_with_retry -v
```

**Expected Flow:**
1. ✅ First payment fails
2. ✅ Retry creates new payment record
3. ✅ New payment has different transaction reference
4. ✅ New payment completes successfully
5. ✅ Original payment remains failed

### Scenario 6: Provider Switching (Requirements 5.3, 5.6)

**Test:** Switch from MTN to Airtel mid-flow

```bash
pytest Backend/payments/test_e2e_provider_switching.py -v
```

**Expected Flow:**
1. ✅ Start with MTN payment
2. ✅ Cancel MTN payment
3. ✅ Switch to Airtel
4. ✅ Complete Airtel payment
5. ✅ Both payments tracked independently

---

## Troubleshooting

### Issue: "401 Unauthorized"

**Cause:** Invalid credentials

**Solution:**
1. Verify credentials in Airtel Developer Portal
2. Check `.env` file has correct values
3. Ensure no extra spaces in credentials
4. Run: `python setup_airtel_credentials.py`

### Issue: "403 Forbidden"

**Cause:** Application not approved or missing permissions

**Solution:**
1. Check application status in developer portal
2. Ensure 'Collections' product is enabled
3. Verify sandbox environment is selected
4. Wait for approval (usually instant for sandbox)

### Issue: "Invalid MSISDN"

**Cause:** Wrong phone number format

**Solution:**
1. Use format: 256XXXXXXXXX (with country code)
2. Airtel service auto-strips country code internally
3. Verify phone number is valid Ugandan number

### Issue: "Token Expired"

**Cause:** Access token expired (valid for 2 hours)

**Solution:**
- Token is automatically refreshed by service
- If issue persists, restart Django server
- Check system clock is correct

### Issue: "Network Error"

**Cause:** Cannot reach Airtel API

**Solution:**
1. Check internet connection
2. Verify firewall allows HTTPS to openapiuat.airtel.africa
3. Check Airtel API status
4. Try again after a few minutes

### Issue: "Service Unavailable"

**Cause:** Airtel sandbox temporarily down

**Solution:**
1. Check Airtel developer portal for status updates
2. Try again after 15-30 minutes
3. Contact Airtel support if persists

### Issue: Tests Pass but Real Payments Fail

**Cause:** Sandbox vs Production environment mismatch

**Solution:**
1. Verify `PAYMENT_ENVIRONMENT=sandbox` in `.env`
2. Check using sandbox credentials, not production
3. Ensure base URL is correct (openapiuat.airtel.africa)

---

## Sandbox Limitations

Be aware of these sandbox limitations:

1. **No Real Money:** Sandbox doesn't process real transactions
2. **Simulated Responses:** API responses are simulated
3. **No USSD Prompts:** Test numbers don't trigger actual phone prompts
4. **Limited Test Numbers:** Only specific test numbers work
5. **Rate Limits:** Sandbox may have stricter rate limits
6. **Data Persistence:** Sandbox data may be cleared periodically

---

## Next Steps After Sandbox Testing

Once sandbox testing is complete:

1. ✅ **Document Test Results:**
   - Record all test scenarios executed
   - Note any issues encountered
   - Document workarounds used

2. ✅ **Request Production Access:**
   - Apply for production credentials in developer portal
   - Provide business documentation
   - Wait for approval (5-10 business days)

3. ✅ **Update Configuration:**
   ```bash
   PAYMENT_ENVIRONMENT=production
   AIRTEL_CLIENT_ID=production-client-id
   AIRTEL_CLIENT_SECRET=production-client-secret
   ```

4. ✅ **Production Testing:**
   - Test with small real amounts (UGX 1000)
   - Verify webhook delivery
   - Test with real phone numbers
   - Monitor logs carefully

5. ✅ **Go Live:**
   - Update frontend to use production API
   - Enable monitoring and alerts
   - Set up error tracking
   - Document support procedures

---

## Useful Commands

```bash
# Verify environment setup
python test_airtel_sandbox_setup.py

# Run all Airtel tests
pytest Backend/payments/test_*airtel*.py -v

# Run specific test
pytest Backend/payments/test_e2e_airtel_successful_payment.py::TestAirtelSuccessfulPaymentE2E::test_airtel_successful_payment_flow -v

# Check test coverage
pytest Backend/payments/test_*airtel*.py --cov=payments.services.airtel_service --cov-report=html

# View logs
tail -f Backend/logs/payments.log

# Django shell for manual testing
python manage.py shell
```

---

## Additional Resources

- **Airtel Developer Portal:** https://developers.airtel.africa/
- **API Documentation:** https://developers.airtel.africa/documentation
- **Quick Start Guide:** `Backend/AIRTEL_SETUP_QUICK_START.md`
- **Full Setup Guide:** `Backend/AIRTEL_MONEY_API_SETUP_GUIDE.md`
- **Support:** support@airtel.africa

---

## Checklist

Before moving to production, ensure:

- [ ] All sandbox tests pass
- [ ] Successful payment flow tested
- [ ] Failed payment scenarios tested
- [ ] Timeout handling tested
- [ ] Retry mechanism tested
- [ ] Error messages are user-friendly
- [ ] Logging is comprehensive
- [ ] Phone numbers are encrypted
- [ ] Webhooks are verified (if configured)
- [ ] Rate limiting works
- [ ] Admin dashboard displays payments correctly
- [ ] Documentation is complete

---

**Happy Testing!** 🚀

For questions or issues, refer to the troubleshooting section or contact Airtel support.
