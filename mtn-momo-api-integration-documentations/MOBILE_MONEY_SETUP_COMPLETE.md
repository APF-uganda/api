# Complete Mobile Money Setup Guide

**Set up both MTN MoMo and Airtel Money APIs for your APF Portal**

---

## 🎯 Overview

Your APF Portal supports two mobile money providers:
- **MTN Mobile Money** (MTN MoMo)
- **Airtel Money**

This guide will help you set up both providers for complete payment coverage in Uganda.

---

## 📊 Provider Coverage in Uganda

| Provider | Market Share | Phone Prefixes |
|----------|--------------|----------------|
| **MTN** | ~60% | 256774, 256784, 256774, 256776, 256777, 256778 |
| **Airtel** | ~30% | 256700, 256750, 256701, 256752 |

**Recommendation:** Set up both providers to cover ~90% of mobile money users in Uganda.

---

## 🚀 Quick Setup (Both Providers)

### Option 1: Automated Scripts (Fastest)

```bash
cd Backend

# Set up MTN MoMo
python setup_mtn_credentials.py

# Set up Airtel Money
python setup_airtel_credentials.py

# Verify both are working
python verify_payments_setup.py
```

### Option 2: Manual Setup

Follow the individual guides:
1. **MTN MoMo:** `Backend/MTN_MOMO_API_SETUP_GUIDE.md`
2. **Airtel Money:** `Backend/AIRTEL_MONEY_API_SETUP_GUIDE.md`

---

## 📋 Credentials Needed

### MTN MoMo (3 credentials)
- ✓ Subscription Key (from MTN Developer Portal)
- ✓ API User ID (UUID you generate)
- ✓ API Key (generated via API)

### Airtel Money (2 credentials)
- ✓ Client ID (from Airtel Developer Portal)
- ✓ Client Secret (from Airtel Developer Portal)

---

## 🔧 Complete .env Configuration

After setting up both providers, your `Backend/.env` should look like:

```bash
# Payment Configuration
PAYMENT_ENVIRONMENT=sandbox  # or 'production'

# MTN MoMo API
MTN_SUBSCRIPTION_KEY=your-mtn-subscription-key
MTN_API_USER=your-mtn-api-user-uuid
MTN_API_KEY=your-mtn-api-key

# Airtel Money API
AIRTEL_CLIENT_ID=your-airtel-client-id
AIRTEL_CLIENT_SECRET=your-airtel-client-secret

# Phone number encryption
PHONE_ENCRYPTION_KEY=your-fernet-encryption-key

# Payment rate limiting
PAYMENT_RATE_LIMIT_REQUESTS=10
PAYMENT_RATE_LIMIT_WINDOW=60

# Webhook secrets (optional)
MTN_WEBHOOK_SECRET=your-mtn-webhook-secret
AIRTEL_WEBHOOK_SECRET=your-airtel-webhook-secret
```

---

## 🧪 Testing Both Providers

### Test MTN MoMo

```python
from decimal import Decimal
import uuid
from payments.services.mtn_service import MTNService

mtn = MTNService()
result = mtn.request_to_pay(
    phone_number="256774000001",  # MTN test number
    amount=Decimal("5000"),
    currency="UGX",
    reference=str(uuid.uuid4()),
    payer_message="Test Payment"
)
print(f"MTN Result: {result}")
```

### Test Airtel Money

```python
from decimal import Decimal
import uuid
from payments.services.airtel_service import AirtelService

airtel = AirtelService()
ref = str(uuid.uuid4())
tx_id = str(uuid.uuid4())

result = airtel.request_to_pay(
    phone_number="256700000001",  # Airtel test number
    amount=Decimal("5000"),
    currency="UGX",
    reference=ref,
    transaction_id=tx_id
)
print(f"Airtel Result: {result}")
```

### Test Automatic Provider Detection

```python
from decimal import Decimal
from payments.services.payment_service import PaymentService
from authentication.models import User

# Get a user
user = User.objects.first()

payment_service = PaymentService()

# Test with MTN number (auto-detects MTN)
mtn_payment = payment_service.initiate_payment(
    user=user,
    phone_number="256774000001",
    amount=Decimal("5000")
)
print(f"Detected provider: {mtn_payment.provider}")  # Should be 'mtn'

# Test with Airtel number (auto-detects Airtel)
airtel_payment = payment_service.initiate_payment(
    user=user,
    phone_number="256700000001",
    amount=Decimal("5000")
)
print(f"Detected provider: {airtel_payment.provider}")  # Should be 'airtel'
```

---

## 📱 Sandbox Test Numbers

### MTN MoMo Test Numbers

| Phone Number | Behavior |
|--------------|----------|
| 256774000001 | ✅ Will approve payment |
| 256774000002 | ❌ Will reject payment |
| 256774000003 | ⏱️ Will timeout |

### Airtel Money Test Numbers

| Phone Number | Behavior |
|--------------|----------|
| 256700000001 | ✅ Will approve payment |
| 256700000002 | ❌ Will reject (insufficient funds) |
| 256700000003 | ⏱️ Will timeout |

**Note:** Test numbers may vary. Check provider documentation for current numbers.

---

## 🔄 How Provider Detection Works

Your payment system automatically detects the provider based on phone number prefix:

```python
# From payments/utils.py
def detect_provider(phone_number: str) -> str:
    """
    Detect mobile money provider from phone number.
    
    Uganda prefixes:
    - MTN: 774, 775, 776, 777, 778, 784
    - Airtel: 700, 701, 750, 752
    """
    # Normalize phone number
    phone = phone_number.replace('+', '').replace(' ', '')
    
    # Extract prefix (assuming 256XXXXXXXXX format)
    if phone.startswith('256'):
        prefix = phone[3:6]  # Get 3 digits after country code
        
        # MTN prefixes
        if prefix in ['774', '775', '776', '777', '778', '784']:
            return 'mtn'
        
        # Airtel prefixes
        elif prefix in ['700', '701', '750', '752']:
            return 'airtel'
    
    # Default to MTN if unknown
    return 'mtn'
```

---

## 🔑 Key Differences Between Providers

| Feature | MTN MoMo | Airtel Money |
|---------|----------|--------------|
| **Setup Complexity** | ⭐⭐⭐ More steps | ⭐⭐ Simpler |
| **Credentials** | 3 (Subscription Key, API User, API Key) | 2 (Client ID, Client Secret) |
| **Auth Method** | Basic Auth + Subscription Key | OAuth 2.0 Client Credentials |
| **Token Validity** | 1 hour (3600s) | 2 hours (7200s) |
| **Phone Format** | Full: 256774000001 | MSISDN: 700000001 (auto-stripped) |
| **Transaction ID** | Uses reference ID | Requires separate transaction ID |
| **Status Codes** | SUCCESSFUL, PENDING, FAILED | TS, TIP, TF, TA |
| **Sandbox URL** | sandbox.momodeveloper.mtn.com | openapiuat.airtel.africa |
| **Production URL** | momodeveloper.mtn.com | openapi.airtel.africa |

---

## ✅ Verification Checklist

Run this checklist to ensure everything is set up correctly:

```bash
cd Backend
python verify_payments_setup.py
```

Expected output:
```
✓ Environment variables configured
✓ MTN credentials found
✓ Airtel credentials found
✓ MTN authentication successful
✓ Airtel authentication successful
✓ Payment models ready
✓ Phone encryption configured
✓ Rate limiting configured
```

---

## 🚀 Production Deployment

### When You're Ready for Production

1. **Apply for Production Access:**
   - MTN: Request production access in MTN Developer Portal
   - Airtel: Request production access in Airtel Developer Portal

2. **Wait for Approval:**
   - MTN: 3-7 business days
   - Airtel: 5-10 business days

3. **Get Production Credentials:**
   - Follow same process as sandbox
   - Get production-specific credentials

4. **Update Environment Variables:**
   ```bash
   PAYMENT_ENVIRONMENT=production
   
   # MTN Production
   MTN_SUBSCRIPTION_KEY=production-subscription-key
   MTN_API_USER=production-api-user-uuid
   MTN_API_KEY=production-api-key
   
   # Airtel Production
   AIRTEL_CLIENT_ID=production-client-id
   AIRTEL_CLIENT_SECRET=production-client-secret
   ```

5. **Test Thoroughly:**
   - Test with small amounts first
   - Verify both providers work
   - Test error scenarios
   - Monitor logs closely

---

## 🆘 Troubleshooting

### Both Providers Fail

**Check:**
- ✓ Environment variables are set correctly
- ✓ PAYMENT_ENVIRONMENT matches your credentials (sandbox vs production)
- ✓ Internet connection is working
- ✓ No firewall blocking API requests

### MTN Works, Airtel Fails (or vice versa)

**Check:**
- ✓ Credentials for failing provider are correct
- ✓ Application is approved in developer portal
- ✓ Using correct environment (sandbox vs production)
- ✓ Phone number format is correct

### Provider Detection Not Working

**Check:**
- ✓ Phone number includes country code (256)
- ✓ Phone number prefix is recognized
- ✓ No extra spaces or special characters

### Payments Stuck in Pending

**Check:**
- ✓ Using correct test numbers in sandbox
- ✓ Status check is being called
- ✓ Webhook is configured (if using webhooks)

---

## 📚 Additional Resources

### Documentation
- **MTN Full Guide:** `Backend/MTN_MOMO_API_SETUP_GUIDE.md`
- **MTN Quick Start:** `Backend/MTN_SETUP_QUICK_START.md`
- **Airtel Full Guide:** `Backend/AIRTEL_MONEY_API_SETUP_GUIDE.md`
- **Airtel Quick Start:** `Backend/AIRTEL_SETUP_QUICK_START.md`

### Developer Portals
- **MTN:** https://momodeveloper.mtn.com/
- **Airtel:** https://developers.airtel.africa/

### API Documentation
- **MTN API Docs:** https://momodeveloper.mtn.com/api-documentation/
- **Airtel API Docs:** https://developers.airtel.africa/documentation

### Support
- **MTN Support:** developer@mtn.com
- **Airtel Support:** support@airtel.africa

---

## 🎉 You're All Set!

With both providers configured, you can now:

✅ Accept payments from ~90% of mobile money users in Uganda
✅ Automatic provider detection based on phone number
✅ Fallback support if one provider is down
✅ Test with sandbox numbers
✅ Monitor payments in Django admin
✅ Integrate with your frontend application

---

## 💡 Best Practices

1. **Always Test Both Providers:** Ensure both MTN and Airtel work before going live
2. **Monitor Provider Status:** Keep track of which provider is more reliable
3. **Handle Errors Gracefully:** Show user-friendly error messages
4. **Log Everything:** Keep detailed logs for debugging
5. **Rate Limiting:** Respect API rate limits (configured in your app)
6. **Security:** Never commit credentials to version control
7. **Webhooks:** Set up webhooks for real-time payment updates
8. **Retry Logic:** Implement retry logic for failed payments
9. **User Communication:** Keep users informed about payment status
10. **Testing:** Test edge cases (timeouts, cancellations, insufficient funds)

---

## 🔐 Security Reminders

- ✓ Phone numbers are encrypted in database
- ✓ API credentials stored in environment variables
- ✓ Webhook signatures verified
- ✓ Rate limiting enabled
- ✓ HTTPS enforced in production
- ✓ Audit logs for all transactions
- ✓ IP address and user agent captured

---

**Happy coding!** 🚀

For questions or issues, refer to the individual provider guides or contact their support teams.
