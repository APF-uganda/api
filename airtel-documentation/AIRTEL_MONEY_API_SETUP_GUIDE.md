# Airtel Money API Setup Guide

Complete step-by-step guide to obtain and configure Airtel Money API credentials for your APF Portal project.

---

## Overview

Your project requires two main credentials from Airtel Money:
1. **Client ID** - Your application identifier
2. **Client Secret** - Your application secret key

You'll start with the **UAT (Sandbox) environment** for testing, then move to **Production** when ready.

---

## Step 1: Create Airtel Developer Account

### 1.1 Register on Airtel Developer Portal

1. Go to: **https://developers.airtel.africa/**
2. Click **"Sign Up"** or **"Get Started"**
3. Fill in your details:
   - Email address
   - Password
   - First name & Last name
   - Company name
   - Country (Uganda)
   - Phone number
4. Verify your email address
5. Log in to the developer portal

### 1.2 Complete Your Profile

1. After logging in, complete your profile information
2. Add company/business details if required
3. Accept terms and conditions

---

## Step 2: Create an Application

Airtel requires you to create an "Application" to get API credentials.

### 2.1 Navigate to Applications

1. In the developer portal, go to **"My Apps"** or **"Applications"**
2. Click **"Create New App"** or **"Add Application"**

### 2.2 Fill Application Details

Provide the following information:

**Basic Information:**
- **Application Name**: `APF Portal` (or your preferred name)
- **Description**: `Payment integration for APF membership portal`
- **Category**: `Financial Services` or `Payments`
- **Country**: `Uganda`

**Technical Details:**
- **Callback URL**: Your webhook URL (can use `https://webhook.site` for testing)
- **Environment**: Select **UAT/Sandbox** for testing

**Products/APIs:**
- Select **"Collections"** or **"Disbursements"** (choose Collections for receiving payments)
- You may also see it as **"Money"** or **"Payment"** product

### 2.3 Submit Application

1. Review your application details
2. Click **"Submit"** or **"Create Application"**
3. Wait for approval (usually instant for sandbox, may take time for production)

---

## Step 3: Get Your API Credentials

Once your application is approved, you'll receive your credentials.

### 3.1 View Application Credentials

1. Go to **"My Apps"** or **"Applications"**
2. Click on your application name
3. Navigate to **"Credentials"** or **"API Keys"** section

### 3.2 Copy Your Credentials

You should see:
- **Client ID** (also called App ID or API Key)
- **Client Secret** (also called App Secret or API Secret)

**Example format:**
```
Client ID: a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
Client Secret: AbCdEfGhIjKlMnOpQrStUvWxYz1234567890
```

**⚠️ Important:** Keep your Client Secret secure! Never commit it to version control or share it publicly.

---

## Step 4: Configure Your Project

Now add the credentials to your project's environment file.

### 4.1 Update Backend/.env

Open `Backend/.env` and add:

```bash
# Payment Configuration
PAYMENT_ENVIRONMENT=sandbox

# Airtel Money API Credentials
AIRTEL_CLIENT_ID=your-client-id-here
AIRTEL_CLIENT_SECRET=your-client-secret-here

# Optional: Webhook Secret (generate a random string)
AIRTEL_WEBHOOK_SECRET=your-random-webhook-secret-here
```

### 4.2 Generate Webhook Secret (Optional)

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

## Step 5: Test Your Configuration

### 5.1 Run the Verification Script

Your project has a verification script. Run it:

```bash
cd Backend
python verify_payments_setup.py
```

This will check:
- ✓ Environment variables are set
- ✓ Airtel credentials are configured
- ✓ Can authenticate with Airtel API
- ✓ Database models are set up

### 5.2 Test Authentication Manually

You can also test authentication manually:

```python
# Backend/test_airtel_auth.py
import os
from payments.services.airtel_service import AirtelService

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Test Airtel authentication
airtel_service = AirtelService()

try:
    token = airtel_service._get_access_token()
    print(f"✓ Authentication successful!")
    print(f"Access Token: {token[:20]}...")
except Exception as e:
    print(f"✗ Authentication failed: {e}")
```

Run it:
```bash
python test_airtel_auth.py
```

---

## Step 6: Test Payment Flow (Sandbox)

### 6.1 Sandbox Test Phone Numbers

Airtel provides test phone numbers for UAT/sandbox environment:

**Uganda (256):**
- `256700000001` - Will approve payment
- `256700000002` - Will reject payment (insufficient funds)
- `256700000003` - Will timeout

**Note:** Test numbers may vary. Check Airtel's documentation or developer portal for current test numbers.

### 6.2 Test a Payment Request

```python
# Backend/test_airtel_payment.py
from decimal import Decimal
import uuid
from payments.services.airtel_service import AirtelService

airtel_service = AirtelService()

# Generate unique IDs
transaction_ref = str(uuid.uuid4())
transaction_id = str(uuid.uuid4())

# Test payment request
result = airtel_service.request_to_pay(
    phone_number="256700000001",  # Test number
    amount=Decimal("5000"),
    currency="UGX",
    reference=transaction_ref,
    transaction_id=transaction_id
)

print(f"Payment Result: {result}")

if result['success']:
    # Check status after a few seconds
    import time
    time.sleep(5)
    
    status = airtel_service.check_payment_status(transaction_id)
    print(f"Payment Status: {status}")
```

---

## Step 7: Understanding Airtel API Differences

Airtel Money API has some differences from MTN MoMo:

### 7.1 Authentication

**Airtel:**
- Uses OAuth 2.0 with Client Credentials grant
- Token valid for 2 hours (7200 seconds)
- Endpoint: `POST /auth/oauth2/token`

**Request:**
```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "grant_type": "client_credentials"
}
```

### 7.2 Payment Request

**Airtel:**
- Requires separate transaction ID
- Phone number format: MSISDN without country code (e.g., `700000001`)
- Headers include `X-Country` and `X-Currency`

**Request:**
```json
{
  "reference": "bill-payment",
  "subscriber": {
    "country": "UG",
    "currency": "UGX",
    "msisdn": "700000001"
  },
  "transaction": {
    "amount": 5000,
    "country": "UG",
    "currency": "UGX",
    "id": "unique-transaction-id"
  }
}
```

### 7.3 Status Codes

**Airtel Status Codes:**
- `TS` - Transaction Successful
- `TIP` - Transaction In Progress
- `TF` - Transaction Failed
- `TA` - Transaction Ambiguous

---

## Step 8: Production Setup (When Ready)

### 8.1 Apply for Production Access

1. Log in to Airtel Developer Portal
2. Go to your application
3. Click **"Request Production Access"** or **"Go Live"**
4. Fill in the application form:
   - Business details
   - Use case description
   - Expected transaction volume
   - Business registration documents
   - Tax identification number
   - Bank account details

### 8.2 Wait for Approval

Airtel will review your application (typically 5-10 business days).

### 8.3 Get Production Credentials

Once approved:
1. Go to your application in the portal
2. Switch to **"Production"** environment
3. Get your **Production Client ID** and **Client Secret**

### 8.4 Update Environment Variables

For production deployment (Render, etc.):

```bash
PAYMENT_ENVIRONMENT=production
AIRTEL_CLIENT_ID=your-production-client-id
AIRTEL_CLIENT_SECRET=your-production-client-secret
AIRTEL_WEBHOOK_SECRET=your-production-webhook-secret
```

---

## Step 9: Webhook Configuration (Optional)

### 9.1 Set Up Webhook Endpoint

Airtel can send payment status updates to your webhook URL.

**Your webhook endpoint:** `https://your-domain.com/api/payments/webhook/airtel/`

### 9.2 Configure in Airtel Portal

1. Go to your application settings
2. Find **"Webhook URL"** or **"Callback URL"**
3. Enter your webhook endpoint
4. Save changes

### 9.3 Webhook Payload Example

```json
{
  "transaction": {
    "id": "transaction-id",
    "status": "TS",
    "message": "Transaction successful",
    "amount": 5000,
    "currency": "UGX"
  }
}
```

---

## Troubleshooting

### Issue: "401 Unauthorized" Error

**Cause:** Invalid credentials

**Solution:**
1. Verify your Client ID and Client Secret are correct
2. Ensure you're using the right environment (UAT vs Production)
3. Check that credentials haven't expired
4. Regenerate credentials if needed

### Issue: "403 Forbidden" Error

**Cause:** Application not approved or insufficient permissions

**Solution:**
1. Check application status in developer portal
2. Ensure you've subscribed to the Collections product
3. Verify your application has the necessary permissions

### Issue: "Invalid MSISDN" Error

**Cause:** Phone number format incorrect

**Solution:**
1. Use format without country code: `700000001` (not `256700000001`)
2. The service automatically strips the country code
3. Ensure phone number is valid for Uganda

### Issue: "Access Token Expired"

**Cause:** Token expired (valid for 2 hours)

**Solution:**
- The AirtelService automatically refreshes tokens
- If manual testing, request a new token

### Issue: "Payment Request Fails"

**Cause:** Various reasons

**Solution:**
1. Check phone number format
2. Verify amount is valid (minimum 100 UGX)
3. Use sandbox test numbers for testing
4. Check Airtel API status page
5. Review API response for specific error codes

---

## Quick Reference

### Environment Variables Needed

```bash
# Required
AIRTEL_CLIENT_ID=<from-step-3>
AIRTEL_CLIENT_SECRET=<from-step-3>
PAYMENT_ENVIRONMENT=sandbox

# Optional
AIRTEL_WEBHOOK_SECRET=<random-string>
```

### API Endpoints

**UAT/Sandbox:**
- Base URL: `https://openapiuat.airtel.africa`
- Authentication: `POST /auth/oauth2/token`
- Payment Request: `POST /merchant/v1/payments/`
- Check Status: `GET /standard/v1/payments/{transactionId}`

**Production:**
- Base URL: `https://openapi.airtel.africa`
- (Same endpoints as UAT)

### Test Phone Numbers (UAT)

- **Success:** 256700000001
- **Failure:** 256700000002
- **Timeout:** 256700000003

**Note:** Verify current test numbers in Airtel documentation.

---

## Additional Resources

- **Airtel Developer Portal:** https://developers.airtel.africa/
- **API Documentation:** https://developers.airtel.africa/documentation
- **Support:** support@airtel.africa or through developer portal
- **Status Page:** Check Airtel developer portal for service status

---

## Summary Checklist

- [ ] Created Airtel Developer account
- [ ] Created application in developer portal
- [ ] Got Client ID and Client Secret
- [ ] Added credentials to Backend/.env
- [ ] Generated webhook secret (optional)
- [ ] Ran verification script
- [ ] Tested authentication
- [ ] Tested payment with sandbox number
- [ ] Ready for development!

---

## Comparison: Airtel vs MTN

| Feature | Airtel Money | MTN MoMo |
|---------|--------------|----------|
| **Authentication** | OAuth 2.0 Client Credentials | Basic Auth + Subscription Key |
| **Token Validity** | 2 hours (7200s) | 1 hour (3600s) |
| **Phone Format** | MSISDN only (700000001) | Full number (256700000001) |
| **Transaction ID** | Required separate ID | Uses reference ID |
| **Status Codes** | TS, TIP, TF, TA | SUCCESSFUL, PENDING, FAILED |
| **Sandbox URL** | openapiuat.airtel.africa | sandbox.momodeveloper.mtn.com |

---

**Need Help?**

If you encounter issues:
1. Check the troubleshooting section above
2. Review Airtel API documentation
3. Contact Airtel developer support
4. Check your project's payment service logs

**Next Steps:**

Once configured, you can:
1. Start the Django development server
2. Test payment flows through the API
3. Use the admin interface to view payments
4. Integrate with your frontend application
5. Test provider switching between MTN and Airtel
