# Airtel Money API - Quick Start Guide

**Get your Airtel Money API credentials in 5 minutes!**

---

## 🎯 What You Need

Two credentials from Airtel:
1. **Client ID** - Your application identifier
2. **Client Secret** - Your application secret key

---

## 📋 Quick Steps

### 1️⃣ Register & Create App (5 minutes)

1. Go to: **https://developers.airtel.africa/**
2. Click **Sign Up** → Verify email → Log in
3. Go to **"My Apps"** or **"Applications"**
4. Click **"Create New App"**
5. Fill in details:
   - **Name:** APF Portal Test (or any name)
   - **Description:** Testing mobile money integration for membership portal
   - **Category:** Financial Services
   - **Country:** Uganda
   - **Product:** Collections (for receiving payments)
   - **Environment:** UAT/Sandbox ⚠️ (NOT Production!)
   - **Callback URL:** https://webhook.site (for testing)
6. Submit and wait for approval
   - **Usually instant** or within 24 hours for sandbox
   - Check email (including spam folder)
7. Once approved, go to your app → **Credentials** section
8. **Copy your Client ID and Client Secret** ✓

**Note:** Sandbox approval is quick and doesn't require business documents!

---

## 2️⃣ Configure Your Project (1 minute)

### Update Backend/.env

Add these lines to your `Backend/.env` file:

```bash
# Airtel Money API
AIRTEL_CLIENT_ID=your-client-id-here
AIRTEL_CLIENT_SECRET=your-client-secret-here
PAYMENT_ENVIRONMENT=sandbox
```

**That's it!** Your credentials are configured.

---

## 🧪 Test Your Setup

### Verify Everything Works

```bash
cd Backend
python verify_payments_setup.py
```

Expected output:
```
✓ Environment variables configured
✓ Airtel credentials found
✓ Airtel authentication successful
✓ Payment models ready
```

### Test a Payment

```bash
python manage.py shell
```

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
    phone_number="256700000001",  # Test number (will approve)
    amount=Decimal("5000"),
    currency="UGX",
    reference=ref,
    transaction_id=tx_id
)

print(result)
# Should show: {'success': True, 'transaction_reference': '...', 'message': '...'}
```

---

## 📱 Sandbox Test Numbers

Use these phone numbers for testing:

| Phone Number | Behavior |
|--------------|----------|
| 256700000001 | ✅ Will approve payment |
| 256700000002 | ❌ Will reject payment (insufficient funds) |
| 256700000003 | ⏱️ Will timeout |

**Note:** Test numbers may vary. Check Airtel's documentation for current test numbers.

---

## 🔧 Manual Setup Script

If you want to test authentication quickly:

```python
# Backend/test_airtel_auth.py
import os
from payments.services.airtel_service import AirtelService
from dotenv import load_dotenv

load_dotenv()

airtel = AirtelService()

try:
    token = airtel._get_access_token()
    print(f"✓ Authentication successful!")
    print(f"Access Token: {token[:30]}...")
except Exception as e:
    print(f"✗ Authentication failed: {e}")
```

Run it:
```bash
python test_airtel_auth.py
```

---

## ✅ Your .env Should Look Like This

```bash
# Payment Configuration
PAYMENT_ENVIRONMENT=sandbox

# MTN MoMo API
MTN_SUBSCRIPTION_KEY=your-mtn-subscription-key
MTN_API_USER=your-mtn-api-user
MTN_API_KEY=your-mtn-api-key

# Airtel Money API
AIRTEL_CLIENT_ID=a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
AIRTEL_CLIENT_SECRET=AbCdEfGhIjKlMnOpQrStUvWxYz1234567890

# Optional: Webhook Secrets
MTN_WEBHOOK_SECRET=your-mtn-webhook-secret
AIRTEL_WEBHOOK_SECRET=your-airtel-webhook-secret
```

---

## 🔑 Key Differences: Airtel vs MTN

| Feature | Airtel | MTN |
|---------|--------|-----|
| **Credentials** | Client ID + Secret | API User + Key + Subscription Key |
| **Auth Method** | OAuth 2.0 | Basic Auth |
| **Token Validity** | 2 hours | 1 hour |
| **Phone Format** | 700000001 (no country code) | 256700000001 (with country code) |
| **Setup Complexity** | ⭐⭐ Simpler | ⭐⭐⭐ More steps |

---

## 🚀 Production Setup (Later)

When ready for production:

1. In Airtel Developer Portal, request production access for your app
2. Wait for approval (5-10 business days)
3. Get production credentials
4. Update environment:
   ```bash
   PAYMENT_ENVIRONMENT=production
   AIRTEL_CLIENT_ID=production-client-id
   AIRTEL_CLIENT_SECRET=production-client-secret
   ```

---

## 🆘 Troubleshooting

### "401 Unauthorized"
- ❌ Wrong Client ID or Secret
- ✅ Double-check credentials from portal

### "403 Forbidden"
- ❌ App not approved or missing permissions
- ✅ Check app status in developer portal

### "Invalid MSISDN"
- ❌ Wrong phone format
- ✅ Use format: 700000001 (service auto-strips country code)

### Authentication Fails
- ❌ Using production credentials in sandbox
- ✅ Ensure PAYMENT_ENVIRONMENT matches your credentials

---

## 📚 More Information

- **Full Guide:** `Backend/AIRTEL_MONEY_API_SETUP_GUIDE.md`
- **Airtel Portal:** https://developers.airtel.africa/
- **API Docs:** https://developers.airtel.africa/documentation

---

## 🎉 You're Ready!

Once setup is complete:
- ✅ Start Django server: `python manage.py runserver`
- ✅ Test payments through your API
- ✅ View payments in Django admin
- ✅ Test provider switching (MTN ↔ Airtel)
- ✅ Integrate with your frontend

---

## 💡 Pro Tips

1. **Test Both Providers:** Set up both MTN and Airtel for complete testing
2. **Provider Switching:** Your app automatically detects provider from phone number
3. **Phone Formats:**
   - MTN: 256774XXXXXX or 256784XXXXXX
   - Airtel: 256700XXXXXX or 256750XXXXXX
4. **Token Caching:** Both services cache tokens automatically
5. **Error Handling:** Check logs for detailed error messages

---

## 🔄 Testing Provider Switching

```python
from payments.services.payment_service import PaymentService

payment_service = PaymentService()

# Test MTN
mtn_result = payment_service.initiate_payment(
    user=user,
    phone_number="256774000001",  # MTN number
    amount=Decimal("5000")
)

# Test Airtel
airtel_result = payment_service.initiate_payment(
    user=user,
    phone_number="256700000001",  # Airtel number
    amount=Decimal("5000")
)
```

**Happy coding!** 🚀
