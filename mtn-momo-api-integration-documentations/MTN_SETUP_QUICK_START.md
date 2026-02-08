# MTN MoMo API - Quick Start Guide

**Get your MTN MoMo API credentials in 5 minutes!**

---

## 🎯 What You Need

Three credentials from MTN:
1. **Subscription Key** - From MTN Developer Portal
2. **API User ID** - UUID you generate
3. **API Key** - Generated via API

---

## 📋 Quick Steps

### 1️⃣ Register & Subscribe (5 minutes)

1. Go to: **https://momodeveloper.mtn.com/**
2. Click **Sign Up** → Verify email → Log in
3. Go to **Products** → Find **Collections**
4. Click **Subscribe** (choose Sandbox - it's free)
5. **Copy your Primary Subscription Key** ✓

---

### 2️⃣ Run Setup Script (2 minutes)

We've created an automated script to handle the rest!

```bash
cd Backend
python setup_mtn_credentials.py
```

The script will:
- ✓ Ask for your Subscription Key
- ✓ Generate an API User ID
- ✓ Create the API User with MTN
- ✓ Generate your API Key
- ✓ Test authentication
- ✓ Update your .env file

**That's it!** Your credentials are configured.

---

## 🧪 Test Your Setup

### Verify Everything Works

```bash
python verify_payments_setup.py
```

Expected output:
```
✓ Environment variables configured
✓ MTN credentials found
✓ MTN authentication successful
✓ Payment models ready
```

### Test a Payment

```bash
python manage.py shell
```

```python
from decimal import Decimal
import uuid
from payments.services.mtn_service import MTNService

# Initialize service
mtn = MTNService()

# Test payment with sandbox number
result = mtn.request_to_pay(
    phone_number="256774000001",  # Test number (will approve)
    amount=Decimal("5000"),
    currency="UGX",
    reference=str(uuid.uuid4()),
    payer_message="Test Payment"
)

print(result)
# Should show: {'success': True, 'transaction_reference': '...', 'message': '...'}
```

---

## 📱 Sandbox Test Numbers

Use these phone numbers for testing:

| Phone Number | Behavior |
|--------------|----------|
| 256774000001 | ✅ Will approve payment |
| 256774000002 | ❌ Will reject payment |
| 256774000003 | ⏱️ Will timeout |

---

## 🔧 Manual Setup (Alternative)

If you prefer to do it manually:

### Step 1: Generate UUID
```python
import uuid
print(uuid.uuid4())
# Example: a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
```

### Step 2: Create API User
```bash
curl -X POST https://sandbox.momodeveloper.mtn.com/v1_0/apiuser \
  -H "X-Reference-Id: YOUR_UUID" \
  -H "Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY" \
  -H "Content-Type: application/json" \
  -d '{"providerCallbackHost": "webhook.site"}'
```

### Step 3: Generate API Key
```bash
curl -X POST https://sandbox.momodeveloper.mtn.com/v1_0/apiuser/YOUR_UUID/apikey \
  -H "Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY"
```

### Step 4: Add to .env
```bash
MTN_SUBSCRIPTION_KEY=your-subscription-key
MTN_API_USER=your-uuid
MTN_API_KEY=your-api-key
PAYMENT_ENVIRONMENT=sandbox
```

---

## ✅ Your .env Should Look Like This

```bash
# Payment Configuration
PAYMENT_ENVIRONMENT=sandbox

# MTN MoMo API
MTN_SUBSCRIPTION_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
MTN_API_USER=12345678-1234-1234-1234-123456789abc
MTN_API_KEY=x1y2z3a4b5c6d7e8f9g0h1i2j3k4l5m6

# Optional: Webhook Secret
MTN_WEBHOOK_SECRET=your-random-secret-string
```

---

## 🚀 Production Setup (Later)

When ready for production:

1. Apply for production access in MTN Developer Portal
2. Wait for approval (3-7 days)
3. Get production credentials (same process)
4. Update environment:
   ```bash
   PAYMENT_ENVIRONMENT=production
   MTN_SUBSCRIPTION_KEY=production-key
   MTN_API_USER=production-uuid
   MTN_API_KEY=production-key
   ```

---

## 🆘 Troubleshooting

### "401 Unauthorized"
- ❌ Wrong subscription key
- ✅ Double-check your key from the portal

### "404 Not Found"
- ❌ API User doesn't exist
- ✅ Run the setup script again

### "Connection Error"
- ❌ Network issue
- ✅ Check your internet connection

### Script Fails
- ❌ Missing dependencies
- ✅ Run: `pip install requests`

---

## 📚 More Information

- **Full Guide:** `Backend/MTN_MOMO_API_SETUP_GUIDE.md`
- **MTN Portal:** https://momodeveloper.mtn.com/
- **API Docs:** https://momodeveloper.mtn.com/api-documentation/

---

## 🎉 You're Ready!

Once setup is complete:
- ✅ Start Django server: `python manage.py runserver`
- ✅ Test payments through your API
- ✅ View payments in Django admin
- ✅ Integrate with your frontend

**Happy coding!** 🚀
