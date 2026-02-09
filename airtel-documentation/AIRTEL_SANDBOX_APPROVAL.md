# Getting Airtel Sandbox/UAT Credentials

**Step-by-step guide to get Airtel Money sandbox credentials for testing**

---

## 🎯 Overview

Unlike MTN (which gives instant sandbox access), Airtel requires you to create an application even for sandbox/UAT access. However, **sandbox approval is usually instant or within 24 hours** - much faster than production!

---

## ⚡ Quick Process (5-10 minutes)

### Step 1: Create Airtel Developer Account

1. **Go to:** https://developers.airtel.africa/
2. Click **"Sign Up"** or **"Get Started"**
3. Fill in the registration form:
   ```
   First Name: [Your first name]
   Last Name: [Your last name]
   Email: [Your email - can be personal for sandbox]
   Password: [Create strong password]
   Phone: [Your phone number]
   Country: Uganda
   ```
4. Click **"Sign Up"** or **"Register"**
5. **Check your email** for verification link
6. Click the verification link to activate your account
7. **Log in** to the developer portal

---

### Step 2: Complete Your Profile (Optional but Recommended)

1. After logging in, you may be asked to complete your profile
2. Fill in basic information:
   ```
   Company/Organization: [Can use your name for testing]
   Role: Developer
   Industry: Technology/Software
   ```
3. Save your profile

---

### Step 3: Create a Sandbox Application

This is the key step to get your credentials!

#### 3.1 Navigate to Applications

1. Look for **"My Apps"**, **"Applications"**, or **"Dashboard"** in the menu
2. Click **"Create New App"** or **"Add Application"** or **"New Application"**

#### 3.2 Fill Application Form

**Basic Information:**
```
Application Name: APF Portal Test
(or any name you prefer - this is just for testing)

Description: 
Testing mobile money integration for membership payment system

Application Type: Web Application
(or Mobile App if you prefer)

Category/Industry: Financial Services
(or Technology/Payments)

Country: Uganda
```

**Environment Selection:**
```
Environment: UAT / Sandbox / Testing
(Choose the non-production option)

⚠️ IMPORTANT: Make sure you select UAT/Sandbox, NOT Production!
```

**Products/APIs to Subscribe:**
```
Select: Collections
(This is for receiving payments)

You might also see:
- Money
- Payments
- Disbursements (optional - for sending money)

✓ Check "Collections" or "Money" for receiving payments
```

**Technical Details (if asked):**
```
Callback URL: https://webhook.site
(You can use webhook.site for testing, or your actual URL if you have one)

Redirect URL: https://your-domain.com
(Can use any URL for sandbox)

Website: https://your-domain.com
(Can use any URL for sandbox, or leave blank if optional)
```

**Additional Information (if asked):**
```
Use Case: 
Testing mobile money payment integration for a membership 
management system. Will be used to collect membership fees 
from users.

Expected Volume: 
Testing only - 10-50 test transactions per month

Target Users:
Development and testing team
```

#### 3.3 Submit Application

1. Review all information
2. Accept terms and conditions (if required)
3. Click **"Submit"** or **"Create Application"**

---

### Step 4: Wait for Approval

**Timeline for Sandbox:**
- **Instant:** Some applications are approved immediately
- **Within 24 hours:** Most sandbox applications
- **Rarely longer:** If there are issues with the form

**What to do while waiting:**
- Check your email (including spam folder)
- Check the developer portal for status updates
- Be patient - usually very quick for sandbox!

---

### Step 5: Get Your Credentials

Once approved (usually instant):

#### 5.1 Access Your Application

1. Go to **"My Apps"** or **"Applications"**
2. Click on your application name (e.g., "APF Portal Test")

#### 5.2 Find Credentials Section

Look for one of these sections:
- **"Credentials"**
- **"API Keys"**
- **"Keys & Secrets"**
- **"Authentication"**

#### 5.3 Copy Your Credentials

You should see:

```
Client ID: a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
(Also called: App ID, API Key, Application ID)

Client Secret: AbCdEfGhIjKlMnOpQrStUvWxYz1234567890
(Also called: App Secret, API Secret, Secret Key)

Environment: UAT / Sandbox
```

**⚠️ Important:** 
- Copy both credentials immediately
- Store them securely
- Don't share them publicly

---

### Step 6: Add to Your Project

#### 6.1 Update Backend/.env

Open `Backend/.env` and add:

```bash
# Airtel Money API (Sandbox/UAT)
AIRTEL_CLIENT_ID=your-client-id-here
AIRTEL_CLIENT_SECRET=your-client-secret-here
PAYMENT_ENVIRONMENT=sandbox
```

#### 6.2 Test Authentication

Run the test script:

```bash
cd Backend
python test_airtel_auth.py
```

Or use the setup script:

```bash
python setup_airtel_credentials.py
```

Expected output:
```
✓ Authentication successful!
Access Token: eyJhbGciOiJSUzI1NiIsInR5cCI...
Token expires in: 7200 seconds (2 hours)
```

---

## 🎯 Minimal Requirements for Sandbox

Good news! For **sandbox/UAT**, requirements are very minimal:

### Required:
- ✓ Email address (can be personal)
- ✓ Phone number
- ✓ Application name
- ✓ Basic description

### NOT Required for Sandbox:
- ❌ Business registration
- ❌ Tax ID (TIN)
- ❌ Bank account
- ❌ Live website with HTTPS
- ❌ Privacy policy
- ❌ Terms & conditions
- ❌ Detailed documentation

**Sandbox is for testing only, so requirements are relaxed!**

---

## 📝 Sample Application Form (Sandbox)

Here's what you can use for a quick sandbox application:

```
Application Name: 
APF Portal Test

Description:
Testing mobile money payment integration for a membership 
management platform. This sandbox application will be used 
to test payment flows, error handling, and webhook integration 
before moving to production.

Application Type:
Web Application

Category:
Financial Services / Technology

Country:
Uganda

Environment:
UAT / Sandbox

Products:
☑ Collections (for receiving payments)

Callback URL:
https://webhook.site
(or https://your-domain.com/api/payments/webhook/airtel/)

Use Case:
Development and testing of mobile money payment integration

Expected Volume:
10-50 test transactions per month (testing only)
```

---

## 🚨 Troubleshooting

### Issue: Application Not Approved Instantly

**Possible Reasons:**
- Form incomplete
- Invalid email/phone
- System delay

**Solution:**
- Wait 24 hours
- Check email (including spam)
- Check portal for status
- Contact support if >24 hours

### Issue: Can't Find "Create Application" Button

**Possible Reasons:**
- Portal layout changed
- Need to complete profile first
- Account not verified

**Solution:**
- Look for: "My Apps", "Dashboard", "Applications"
- Complete profile if prompted
- Verify email if not done
- Try different browser
- Contact support

### Issue: No Credentials Visible

**Possible Reasons:**
- Application still pending
- Need to subscribe to product first
- Looking in wrong section

**Solution:**
- Check application status
- Ensure you subscribed to "Collections"
- Look for "Credentials", "API Keys", "Keys"
- Refresh page
- Log out and log back in

### Issue: Authentication Fails with Credentials

**Possible Reasons:**
- Wrong environment (using production URL with sandbox credentials)
- Copied credentials incorrectly
- Credentials not activated yet

**Solution:**
- Verify you're using UAT URL: `https://openapiuat.airtel.africa`
- Double-check credentials (no extra spaces)
- Wait a few minutes and try again
- Regenerate credentials if available

---

## 🔄 Alternative: Contact Airtel Support

If you're having trouble getting sandbox credentials:

### Email Support

```
To: support@airtel.africa
Subject: Request for Sandbox/UAT API Credentials

Dear Airtel Developer Support,

I am developing a mobile money payment integration for [APF Portal] 
and would like to request sandbox/UAT API credentials for testing.

Application Details:
- Name: APF Portal Test
- Purpose: Testing payment integration
- Country: Uganda
- Product: Collections API
- Environment: UAT/Sandbox

My Account:
- Email: [your-email@example.com]
- Phone: [your-phone-number]
- Developer Portal Account: [Yes/Created]

Please provide:
- Client ID
- Client Secret
- UAT/Sandbox environment access

Thank you for your assistance.

Best regards,
[Your Name]
```

### Through Developer Portal

1. Log in to https://developers.airtel.africa/
2. Look for **"Support"** or **"Help"** or **"Contact"**
3. Submit a support ticket
4. Select category: "API Access" or "Credentials"
5. Describe your need for sandbox credentials

**Response Time:** Usually 1-2 business days

---

## 📱 Sandbox Test Numbers

Once you have credentials, use these test numbers:

```
Success (will approve):
256700000001

Failure (insufficient funds):
256700000002

Timeout:
256700000003
```

**Note:** Test numbers may vary. Check Airtel's documentation or ask support for current test numbers.

---

## ✅ Verification Checklist

After getting credentials:

- [ ] Client ID copied and saved
- [ ] Client Secret copied and saved
- [ ] Added to Backend/.env file
- [ ] PAYMENT_ENVIRONMENT set to "sandbox"
- [ ] Tested authentication (python test_airtel_auth.py)
- [ ] Authentication successful
- [ ] Test transaction attempted
- [ ] Ready to develop!

---

## 🎉 Success!

Once you have your sandbox credentials:

1. **Test authentication** ✓
2. **Test payment request** with test number
3. **Test status checking**
4. **Develop your integration**
5. **Test thoroughly**
6. **When ready, apply for production** (see `APPLICATION_APPROVAL_GUIDE.md`)

---

## 📊 Sandbox vs Production

| Aspect | Sandbox/UAT | Production |
|--------|-------------|------------|
| **Approval Time** | Instant - 24 hours | 5-10 business days |
| **Requirements** | Minimal (email, name) | Full (business docs, bank, etc.) |
| **Cost** | Free | Transaction fees apply |
| **Test Numbers** | Provided by Airtel | Real phone numbers |
| **Real Money** | No | Yes |
| **Purpose** | Testing & development | Live transactions |

---

## 💡 Pro Tips

1. **Use Descriptive Name:** Name your sandbox app clearly (e.g., "APF Portal Test")
2. **Keep Credentials Safe:** Even sandbox credentials should be kept secure
3. **Test Thoroughly:** Use sandbox to test all scenarios before production
4. **Document Issues:** Note any issues you find for production application
5. **Use Test Numbers:** Always use provided test numbers in sandbox
6. **Don't Rush Production:** Only apply for production when fully tested

---

## 🔗 Quick Links

- **Airtel Developer Portal:** https://developers.airtel.africa/
- **Support Email:** support@airtel.africa
- **Setup Script:** `Backend/setup_airtel_credentials.py`
- **Test Script:** `Backend/test_airtel_auth.py`
- **Full Setup Guide:** `Backend/AIRTEL_MONEY_API_SETUP_GUIDE.md`

---

## 📞 Need Help?

If you're stuck:

1. **Check email** (including spam) for approval
2. **Wait 24 hours** for sandbox approval
3. **Contact Airtel support** if >24 hours
4. **Try the portal** from different browser
5. **Check documentation** on Airtel developer portal

---

**Remember:** Sandbox approval is usually **instant or within 24 hours**. It's much simpler than production approval!

Good luck! 🚀
