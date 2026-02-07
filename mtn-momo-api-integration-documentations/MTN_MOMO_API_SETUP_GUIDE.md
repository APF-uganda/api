# MTN MoMo API Setup Guide

Complete step-by-step guide to obtain and configure MTN Mobile Money API credentials for your APF Portal project.

---

## Overview

Your project requires three main credentials from MTN MoMo:
1. **Subscription Key** (Primary/Secondary)
2. **API User ID** (UUID)
3. **API Key** (Secret key)

You'll start with the **Sandbox environment** for testing, then move to **Production** when ready.

---

## Step 1: Create MTN MoMo Developer Account

### 1.1 Register on MTN Developer Portal

1. Go to: **https://momodeveloper.mtn.com/**
2. Click **"Sign Up"** or **"Register"**
3. Fill in your details:
   - Email address
   - Password
   - First name & Last name
   - Country (Uganda)
   - Phone number
4. Verify your email address
5. Log in to the developer portal

### 1.2 Navigate to Your Profile

1. After logging in, click on your **profile/account** icon
2. You should see your dashboard

---

## Step 2: Subscribe to Collections Product

The Collections product allows you to receive payments from customers.

### 2.1 Subscribe to Collections

1. In the developer portal, go to **"Products"** section
2. Find **"Collections"** product
3. Click **"Subscribe"**
4. Choose your subscription tier:
   - **Sandbox**: Free for testing
   - **Production**: Requires approval and may have fees

### 2.2 Get Your Subscription Key

After subscribing, you'll receive:
- **Primary Key** (Subscription Key)
- **Secondary Key** (Backup)

**Save these keys immediately!** You'll need the Primary Key.

```
Example format:
Primary Key: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

---

## Step 3: Create API User (Sandbox)

For the sandbox environment, you need to create an API User.

### 3.1 Using the Developer Portal UI

**Option A: Through Portal (if available)**
1. Go to **"Sandbox"** section
2. Look for **"API User"** or **"Create User"**
3. Click **"Create API User"**
4. Save the generated **User ID** (UUID format)

### 3.2 Using API Calls (Recommended Method)

If the portal doesn't have a UI for this, use API calls:

#### Step 3.2.1: Generate a UUID

First, generate a UUID for your API User. You can use:

**Online UUID Generator:**
- Go to: https://www.uuidgenerator.net/
- Copy the generated UUID (e.g., `a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6`)

**Or use Python:**
```python
import uuid
print(str(uuid.uuid4()))
```

**Or use PowerShell:**
```powershell
[guid]::NewGuid().ToString()
```

#### Step 3.2.2: Create API User via API

Use this curl command (replace placeholders):

```bash
curl -X POST https://sandbox.momodeveloper.mtn.com/v1_0/apiuser \
  -H "X-Reference-Id: YOUR_GENERATED_UUID" \
  -H "Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "providerCallbackHost": "your-domain.com"
  }'
```

**Windows PowerShell version:**
```powershell
$uuid = "YOUR_GENERATED_UUID"
$subscriptionKey = "YOUR_SUBSCRIPTION_KEY"

$headers = @{
    "X-Reference-Id" = $uuid
    "Ocp-Apim-Subscription-Key" = $subscriptionKey
    "Content-Type" = "application/json"
}

$body = @{
    providerCallbackHost = "webhook.site"
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://sandbox.momodeveloper.mtn.com/v1_0/apiuser" `
    -Method Post `
    -Headers $headers `
    -Body $body
```

**Response:**
- **201 Created**: Success! Your API User is created
- The UUID you used is now your **API User ID**

**Save this UUID as your MTN_API_USER!**

---

## Step 4: Generate API Key

Now generate the API Key for your API User.

### 4.1 Using API Call

```bash
curl -X POST https://sandbox.momodeveloper.mtn.com/v1_0/apiuser/YOUR_API_USER_ID/apikey \
  -H "Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY"
```

**Windows PowerShell version:**
```powershell
$apiUserId = "YOUR_API_USER_ID"
$subscriptionKey = "YOUR_SUBSCRIPTION_KEY"

$headers = @{
    "Ocp-Apim-Subscription-Key" = $subscriptionKey
}

$response = Invoke-RestMethod -Uri "https://sandbox.momodeveloper.mtn.com/v1_0/apiuser/$apiUserId/apikey" `
    -Method Post `
    -Headers $headers

$response.apiKey
```

**Response:**
```json
{
  "apiKey": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
}
```

**Save this as your MTN_API_KEY!**

---

## Step 5: Configure Your Project

Now add the credentials to your project's environment file.

### 5.1 Update Backend/.env

Open `Backend/.env` and add:

```bash
# Payment Configuration
PAYMENT_ENVIRONMENT=sandbox

# MTN MoMo API Credentials
MTN_SUBSCRIPTION_KEY=your-primary-subscription-key-here
MTN_API_USER=your-api-user-uuid-here
MTN_API_KEY=your-api-key-here

# Optional: Webhook Secret (generate a random string)
MTN_WEBHOOK_SECRET=your-random-webhook-secret-here
```

### 5.2 Generate Webhook Secret (Optional)

For webhook verification, generate a random secret:

**Python:**
```python
import secrets
print(secrets.token_urlsafe(32))
```

**PowerShell:**
```powershell
$bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
[Convert]::ToBase64String($bytes)
```

---

## Step 6: Test Your Configuration

### 6.1 Run the Verification Script

Your project has a verification script. Run it:

```bash
cd Backend
python verify_payments_setup.py
```

This will check:
- ✓ Environment variables are set
- ✓ MTN credentials are configured
- ✓ Can authenticate with MTN API
- ✓ Database models are set up

### 6.2 Test Authentication Manually

You can also test authentication manually:

```python
# Backend/test_mtn_auth.py
import os
from payments.services.mtn_service import MTNService

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Test MTN authentication
mtn_service = MTNService()

try:
    token = mtn_service._get_access_token()
    print(f"✓ Authentication successful!")
    print(f"Access Token: {token[:20]}...")
except Exception as e:
    print(f"✗ Authentication failed: {e}")
```

Run it:
```bash
python test_mtn_auth.py
```

---

## Step 7: Test Payment Flow (Sandbox)

### 7.1 Sandbox Test Phone Numbers

MTN provides test phone numbers for sandbox:

**Uganda (256):**
- `256774000001` - Will approve payment
- `256774000002` - Will reject payment
- `256774000003` - Will timeout

### 7.2 Test a Payment Request

```python
# Backend/test_mtn_payment.py
from decimal import Decimal
import uuid
from payments.services.mtn_service import MTNService

mtn_service = MTNService()

# Test payment request
result = mtn_service.request_to_pay(
    phone_number="256774000001",  # Test number
    amount=Decimal("5000"),
    currency="UGX",
    reference=str(uuid.uuid4()),
    payer_message="Test Payment"
)

print(f"Payment Result: {result}")

if result['success']:
    # Check status after a few seconds
    import time
    time.sleep(5)
    
    status = mtn_service.check_payment_status(result['transaction_reference'])
    print(f"Payment Status: {status}")
```

---

## Step 8: Production Setup (When Ready)

### 8.1 Apply for Production Access

1. Log in to MTN Developer Portal
2. Go to **"Products"** → **"Collections"**
3. Click **"Request Production Access"**
4. Fill in the application form:
   - Business details
   - Use case description
   - Expected transaction volume
   - Business registration documents

### 8.2 Wait for Approval

MTN will review your application (typically 3-7 business days).

### 8.3 Get Production Credentials

Once approved:
1. Subscribe to **Collections (Production)**
2. Get your **Production Subscription Key**
3. Create Production API User (same process as sandbox)
4. Generate Production API Key

### 8.4 Update Environment Variables

For production deployment (Render, etc.):

```bash
PAYMENT_ENVIRONMENT=production
MTN_SUBSCRIPTION_KEY=your-production-subscription-key
MTN_API_USER=your-production-api-user-uuid
MTN_API_KEY=your-production-api-key
MTN_WEBHOOK_SECRET=your-production-webhook-secret
```

---

## Troubleshooting

### Issue: "401 Unauthorized" Error

**Cause:** Invalid credentials or subscription key

**Solution:**
1. Verify your subscription key is correct
2. Ensure you're using the right environment (sandbox vs production)
3. Check that API User and API Key match

### Issue: "404 Not Found" Error

**Cause:** API User doesn't exist

**Solution:**
1. Verify your API User ID is correct
2. Recreate the API User if needed
3. Ensure you're using the correct base URL

### Issue: "Access Token Expired"

**Cause:** Token expired (valid for ~1 hour)

**Solution:**
- The MTNService automatically refreshes tokens
- If manual testing, request a new token

### Issue: "Payment Request Fails"

**Cause:** Various reasons

**Solution:**
1. Check phone number format (256XXXXXXXXX)
2. Verify amount is valid (minimum 100 UGX)
3. Use sandbox test numbers for testing
4. Check MTN API status page

---

## Quick Reference

### Environment Variables Needed

```bash
# Required
MTN_SUBSCRIPTION_KEY=<from-step-2>
MTN_API_USER=<from-step-3>
MTN_API_KEY=<from-step-4>
PAYMENT_ENVIRONMENT=sandbox

# Optional
MTN_WEBHOOK_SECRET=<random-string>
```

### API Endpoints

**Sandbox:**
- Base URL: `https://sandbox.momodeveloper.mtn.com`
- Create API User: `POST /v1_0/apiuser`
- Generate API Key: `POST /v1_0/apiuser/{userId}/apikey`
- Get Token: `POST /collection/token/`
- Request Payment: `POST /collection/v1_0/requesttopay`
- Check Status: `GET /collection/v1_0/requesttopay/{referenceId}`

**Production:**
- Base URL: `https://momodeveloper.mtn.com`
- (Same endpoints as sandbox)

### Test Phone Numbers (Sandbox)

- **Success:** 256774000001
- **Failure:** 256774000002
- **Timeout:** 256774000003

---

## Additional Resources

- **MTN Developer Portal:** https://momodeveloper.mtn.com/
- **API Documentation:** https://momodeveloper.mtn.com/api-documentation/
- **Support:** developer@mtn.com
- **Status Page:** Check MTN developer portal for service status

---

## Summary Checklist

- [ ] Created MTN Developer account
- [ ] Subscribed to Collections (Sandbox)
- [ ] Got Subscription Key (Primary Key)
- [ ] Generated API User UUID
- [ ] Created API User via API
- [ ] Generated API Key
- [ ] Added credentials to Backend/.env
- [ ] Generated webhook secret
- [ ] Ran verification script
- [ ] Tested authentication
- [ ] Tested payment with sandbox number
- [ ] Ready for development!

---

**Need Help?**

If you encounter issues:
1. Check the troubleshooting section above
2. Review MTN API documentation
3. Contact MTN developer support
4. Check your project's payment service logs

**Next Steps:**

Once configured, you can:
1. Start the Django development server
2. Test payment flows through the API
3. Use the admin interface to view payments
4. Integrate with your frontend application
