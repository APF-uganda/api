# MTN MoMo Sandbox Testing Guide

This guide provides comprehensive instructions for testing MTN Mobile Money integration in the sandbox environment.

## Prerequisites

Before starting sandbox testing, ensure you have:

1. ✅ MTN Developer account at https://momodeveloper.mtn.com/
2. ✅ Subscription to Collections product (Sandbox)
3. ✅ MTN API credentials configured in `.env` file:
   - `MTN_SUBSCRIPTION_KEY`
   - `MTN_API_USER`
   - `MTN_API_KEY`
4. ✅ `PAYMENT_ENVIRONMENT=sandbox` set in `.env`

## Sandbox Credentials Configuration

### Option 1: Automated Setup (Recommended)

Run the automated setup script:

```bash
cd Backend
python setup_mtn_credentials.py
```

This script will:
- Guide you through credential setup
- Create API User in MTN sandbox
- Generate API Key
- Test authentication
- Update your `.env` file

### Option 2: Manual Setup

If you prefer manual configuration:

1. **Get Subscription Key**:
   - Log in to https://momodeveloper.mtn.com/
   - Go to Products → Collections
   - Subscribe to sandbox
   - Copy your Primary Subscription Key

2. **Generate API User ID**:
   ```python
   import uuid
   print(uuid.uuid4())
   ```

3. **Create API User**:
   ```bash
   curl -X POST https://sandbox.momodeveloper.mtn.com/v1_0/apiuser \
     -H "X-Reference-Id: YOUR_UUID" \
     -H "Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY" \
     -H "Content-Type: application/json" \
     -d '{"providerCallbackHost": "webhook.site"}'
   ```

4. **Generate API Key**:
   ```bash
   curl -X POST https://sandbox.momodeveloper.mtn.com/v1_0/apiuser/YOUR_UUID/apikey \
     -H "Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY"
   ```

5. **Update `.env` file**:
   ```bash
   PAYMENT_ENVIRONMENT=sandbox
   MTN_SUBSCRIPTION_KEY=your-subscription-key
   MTN_API_USER=your-uuid
   MTN_API_KEY=your-api-key
   ```

### Verify Configuration

Run the verification script to ensure everything is configured correctly:

```bash
python verify_mtn_sandbox.py
```

Expected output:
```
✓ Environment variables configured
✓ MTN credentials found
✓ MTN authentication successful
✓ Sandbox environment active
✓ Ready for testing
```

## MTN Sandbox Test Phone Numbers

MTN provides specific test phone numbers for different scenarios:

| Phone Number | Behavior | Use Case |
|--------------|----------|----------|
| 256774000001 | ✅ Approves payment | Test successful payment flow |
| 256774000002 | ❌ Rejects payment | Test payment failure handling |
| 256774000003 | ⏱️ Times out | Test timeout scenario |
| 256774000004 | 💰 Insufficient funds | Test insufficient funds error |
| 256774000005 | 🚫 Invalid account | Test invalid account error |

**Note**: These are sandbox-only numbers. They will not work in production.

## Important: Sandbox Currency Requirement

⚠️ **MTN Sandbox only supports EUR currency, not UGX!**

- **Sandbox**: Must use `EUR` currency
- **Production**: Use `UGX` currency

The payment service automatically handles this based on the `PAYMENT_ENVIRONMENT` setting:
- When `PAYMENT_ENVIRONMENT=sandbox` → Uses EUR for MTN payments
- When `PAYMENT_ENVIRONMENT=production` → Uses UGX for MTN payments

This is a known MTN sandbox limitation. See: [MTN Developer Community](https://momodevelopercommunity.mtn.com/momo-api-sand-box-q-a-6/currency-not-supported-invalid-currency-258)

## Test Scenarios

### 1. Successful Payment Flow

Test the complete successful payment flow:

```bash
python test_mtn_sandbox_success.py
```

This test will:
1. Initiate payment with test number 256774000001
2. Poll payment status every 3 seconds
3. Verify payment completes successfully
4. Check database record is updated correctly

**Expected Result**: Payment status changes from `pending` → `completed`

### 2. Failed Payment Scenarios

Test various failure scenarios:

```bash
python test_mtn_sandbox_failures.py
```

This test covers:
- **Insufficient Funds**: Using 256774000004
- **User Cancellation**: Using 256774000002
- **Invalid Account**: Using 256774000005

**Expected Result**: Payment status changes to `failed` with appropriate error message

### 3. Timeout Scenario

Test payment timeout handling:

```bash
python test_mtn_sandbox_timeout.py
```

This test will:
1. Initiate payment with test number 256774000003
2. Poll for 90 seconds
3. Verify timeout is handled correctly

**Expected Result**: Payment status changes to `timeout` after 90 seconds

### 4. Retry and Cancellation

Test retry and cancellation functionality:

```bash
python test_mtn_sandbox_retry.py
```

This test covers:
- Retrying a failed payment
- Cancelling a pending payment
- Verifying new transaction is created on retry

**Expected Result**: New payment record created with same details

### 5. Webhook Testing

Test webhook callback processing:

```bash
python test_mtn_sandbox_webhook.py
```

This test will:
1. Simulate webhook callback from MTN
2. Verify signature validation
3. Check payment status is updated
4. Test idempotency (duplicate webhooks)

**Expected Result**: Payment status updated correctly, duplicates handled

## Manual Testing via Django Shell

For interactive testing, use Django shell:

```bash
python manage.py shell
```

### Test Authentication

```python
from payments.services.mtn_service import MTNService

mtn = MTNService()
token = mtn._get_access_token()
print(f"Access Token: {token[:30]}...")
```

### Test Payment Initiation

```python
from decimal import Decimal
import uuid

reference = str(uuid.uuid4())
result = mtn.request_to_pay(
    phone_number="256774000001",  # Will approve
    amount=Decimal("50000.00"),
    currency="UGX",
    reference=reference,
    payer_message="Test Payment"
)

print(result)
```

### Test Status Checking

```python
# Use the reference from above
status = mtn.check_payment_status(reference)
print(status)
```

### Test Different Scenarios

```python
# Test rejection
result_reject = mtn.request_to_pay(
    phone_number="256774000002",  # Will reject
    amount=Decimal("50000.00"),
    currency="UGX",
    reference=str(uuid.uuid4())
)

# Test insufficient funds
result_insufficient = mtn.request_to_pay(
    phone_number="256774000004",  # Insufficient funds
    amount=Decimal("50000.00"),
    currency="UGX",
    reference=str(uuid.uuid4())
)
```

## Testing via API Endpoints

Test the complete API flow using curl or Postman:

### 1. Initiate Payment

```bash
curl -X POST http://localhost:8000/api/payments/initiate/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "phone_number": "256774000001",
    "provider": "mtn",
    "amount": "50000.00"
  }'
```

### 2. Check Payment Status

```bash
curl -X GET http://localhost:8000/api/payments/status/PAYMENT_ID/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 3. Retry Payment

```bash
curl -X POST http://localhost:8000/api/payments/PAYMENT_ID/retry/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 4. Cancel Payment

```bash
curl -X POST http://localhost:8000/api/payments/PAYMENT_ID/cancel/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Automated Test Suite

Run the complete automated test suite:

```bash
# Run all MTN sandbox tests
pytest Backend/payments/tests/sandbox/ -v

# Run specific test file
pytest Backend/payments/tests/sandbox/test_mtn_sandbox_success.py -v

# Run with coverage
pytest Backend/payments/tests/sandbox/ --cov=payments --cov-report=html
```

## Troubleshooting

### Common Issues

**1. "401 Unauthorized" Error**
- ❌ Problem: Invalid credentials
- ✅ Solution: Verify subscription key, API user, and API key in `.env`
- Run: `python verify_mtn_sandbox.py`

**2. "404 Not Found" Error**
- ❌ Problem: API User doesn't exist
- ✅ Solution: Run `python setup_mtn_credentials.py` again

**3. "Connection Timeout" Error**
- ❌ Problem: Network connectivity issue
- ✅ Solution: Check internet connection, verify MTN sandbox is accessible

**4. "Invalid Phone Number" Error**
- ❌ Problem: Using production number in sandbox
- ✅ Solution: Use sandbox test numbers (256774000001-256774000005)

**5. Token Caching Issues**
- ❌ Problem: Expired token being reused
- ✅ Solution: Token refresh is automatic, but you can clear cache:
  ```python
  mtn = MTNService()
  mtn.access_token = None
  mtn.token_expiry = None
  ```

### Debug Mode

Enable detailed logging for debugging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will show:
- All API requests and responses
- Token generation and caching
- Payment status transitions
- Error details

## Sandbox Limitations

Be aware of sandbox limitations:

1. **Test Numbers Only**: Only specific test numbers work
2. **No Real Money**: No actual money is transferred
3. **Simulated Responses**: Responses are simulated, not real
4. **No SMS**: No actual SMS notifications sent
5. **Webhook Delays**: Webhooks may not be delivered in sandbox
6. **Rate Limits**: Sandbox has lower rate limits than production

## Next Steps

After successful sandbox testing:

1. ✅ Verify all test scenarios pass
2. ✅ Review logs for any errors
3. ✅ Test webhook integration
4. ✅ Document any issues found
5. ✅ Prepare for production deployment

## Production Transition

When ready to move to production:

1. Apply for production access in MTN Developer Portal
2. Wait for approval (3-7 business days)
3. Get production credentials
4. Update `.env`:
   ```bash
   PAYMENT_ENVIRONMENT=production
   MTN_SUBSCRIPTION_KEY=production-key
   MTN_API_USER=production-uuid
   MTN_API_KEY=production-key
   ```
5. Test with small real transactions first
6. Monitor closely for first 24 hours

## Support

- **MTN Developer Portal**: https://momodeveloper.mtn.com/
- **API Documentation**: https://momodeveloper.mtn.com/api-documentation/
- **Support Email**: momo-api@mtn.com
- **Developer Forum**: https://momodeveloper.mtn.com/community/

## Checklist

Before marking sandbox testing complete:

- [ ] MTN credentials configured and verified
- [ ] Successful payment test passes
- [ ] Failed payment test passes
- [ ] Timeout test passes
- [ ] Retry test passes
- [ ] Cancellation test passes
- [ ] Webhook test passes (if applicable)
- [ ] All automated tests pass
- [ ] No errors in logs
- [ ] Documentation updated

---

**Last Updated**: 2026-02-07
**Environment**: Sandbox
**Status**: Ready for Testing
