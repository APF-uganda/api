# Airtel Sandbox Setup - Visual Step-by-Step Guide

**Detailed walkthrough with descriptions of what you'll see on each screen**

---

## 🎯 Goal

Get Airtel Money sandbox credentials (Client ID and Client Secret) for testing your payment integration.

**Time Required:** 5-10 minutes + approval wait (usually instant to 24 hours)

---

## 📋 Step-by-Step Process

### Step 1: Go to Airtel Developer Portal

**Action:** Open your browser and navigate to:
```
https://developers.airtel.africa/
```

**What You'll See:**
- Airtel Africa branding
- Navigation menu with options like "Products", "Documentation", "Pricing"
- Prominent "Sign Up" or "Get Started" button
- "Sign In" link (if you already have an account)

---

### Step 2: Create Account (If New User)

#### 2.1 Click "Sign Up" or "Get Started"

**What You'll See:**
A registration form with fields like:
```
□ First Name: [Your first name]
□ Last Name: [Your last name]
□ Email Address: [your.email@example.com]
□ Password: [Create password]
□ Confirm Password: [Repeat password]
□ Phone Number: [+256XXXXXXXXX]
□ Country: [Select Uganda]
□ Company/Organization: [Optional - can use your name]
□ Role: [Select Developer]
□ ☑ I agree to Terms & Conditions
```

**Action:** Fill in all required fields and click "Sign Up" or "Register"

#### 2.2 Verify Your Email

**What You'll See:**
- Success message: "Registration successful! Please check your email"
- Or redirect to login page

**Action:**
1. Check your email inbox (and spam folder!)
2. Look for email from Airtel Africa / Airtel Developer
3. Click the verification link in the email
4. You'll be redirected back to the portal

---

### Step 3: Log In

**Action:** Enter your email and password, click "Sign In" or "Log In"

**What You'll See After Login:**
- Dashboard or home page
- Welcome message with your name
- Navigation menu with options like:
  - Dashboard
  - My Apps / Applications
  - Documentation
  - API Reference
  - Support
  - Profile/Account

---

### Step 4: Navigate to Applications

**Action:** Look for and click on one of these menu items:
- **"My Apps"**
- **"Applications"**
- **"Dashboard"** (then look for apps section)

**What You'll See:**
- Page title: "My Applications" or "Applications"
- List of your applications (empty if first time)
- Button: "Create New App" or "Add Application" or "+ New Application"
- Possibly tabs for: "All Apps", "Sandbox", "Production"

---

### Step 5: Create New Application

#### 5.1 Click "Create New App" Button

**What You'll See:**
A form with multiple sections. Here's what to fill in:

#### 5.2 Basic Information Section

```
Application Name: *
[APF Portal Test]
(Use any name - this is just for testing)

Description: *
[Testing mobile money integration for membership payment system]
(Brief description of what you're building)

Application Type:
○ Web Application  ← Select this
○ Mobile Application
○ Desktop Application

Category / Industry: *
[Select: Financial Services]
(Or Technology, Payments, E-commerce)

Country: *
[Select: Uganda]
```

#### 5.3 Environment Selection

**⚠️ CRITICAL STEP:**

```
Environment: *
○ Production  ← DON'T select this!
● UAT / Sandbox / Testing  ← SELECT THIS!

(The exact wording may vary:
- "UAT" (User Acceptance Testing)
- "Sandbox"
- "Testing"
- "Development"
All mean the same - non-production environment)
```

#### 5.4 Products/APIs Section

**What You'll See:**
List of available products/APIs with checkboxes:

```
Available Products:

☑ Collections
  Receive payments from customers
  
☐ Disbursements
  Send money to customers
  
☐ KYC
  Know Your Customer verification
  
☐ Balance
  Check account balance
```

**Action:** Check **"Collections"** (this is for receiving payments)

#### 5.5 Technical Details Section

```
Callback URL / Webhook URL:
[https://webhook.site]
(For testing, you can use webhook.site or your actual URL)

Redirect URL: (Optional)
[https://your-domain.com]
(Can leave blank or use any URL for sandbox)

Website URL: (Optional)
[https://your-domain.com]
(Can leave blank for sandbox)
```

#### 5.6 Additional Information (If Asked)

```
Use Case / Purpose:
[Testing mobile money payment integration for a membership 
management system. Will be used to collect membership fees 
from users during development phase.]

Expected Transaction Volume:
[10-50 test transactions per month]
(Low numbers are fine for sandbox)

Target Users:
[Development and testing team]
```

#### 5.7 Terms & Conditions

```
☑ I agree to the Terms & Conditions
☑ I agree to the Privacy Policy
```

**Action:** Check the boxes and click **"Submit"** or **"Create Application"**

---

### Step 6: Wait for Approval

**What You'll See:**
- Success message: "Application submitted successfully"
- Or: "Application created and pending approval"
- Or: "Application approved" (if instant approval)
- Application status: "Pending" or "Approved"

**Timeline:**
- **Instant:** Many sandbox apps are approved immediately
- **Within 24 hours:** Most sandbox applications
- **Check:** Email and portal for status updates

**What to Do:**
1. Check your email (including spam folder)
2. Check the portal - go to "My Apps" to see status
3. Wait patiently - sandbox approval is usually quick!

---

### Step 7: Access Your Application

**Action:** 
1. Go to **"My Apps"** or **"Applications"**
2. You should see your application listed
3. Click on the application name (e.g., "APF Portal Test")

**What You'll See:**
Application details page with tabs or sections:
- Overview / Details
- **Credentials** ← This is what you need!
- Settings
- Analytics / Usage
- Documentation

---

### Step 8: Get Your Credentials

#### 8.1 Click on "Credentials" Tab

**What You'll See:**

```
═══════════════════════════════════════════════════
                    CREDENTIALS
═══════════════════════════════════════════════════

Environment: UAT / Sandbox

Client ID (App ID):
┌─────────────────────────────────────────────────┐
│ a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6           │
│                                          [Copy] │
└─────────────────────────────────────────────────┘

Client Secret (App Secret):
┌─────────────────────────────────────────────────┐
│ AbCdEfGhIjKlMnOpQrStUvWxYz1234567890           │
│                                          [Copy] │
└─────────────────────────────────────────────────┘

⚠️ Keep your credentials secure. Do not share them publicly.

[Regenerate Credentials]  [Show/Hide Secret]
```

**Alternative Layout:**

Some portals show it as a table:

```
┌──────────────────┬────────────────────────────────┐
│ Credential       │ Value                          │
├──────────────────┼────────────────────────────────┤
│ Client ID        │ a1b2c3d4-e5f6-g7h8-i9j0...    │
│ Client Secret    │ ●●●●●●●●●●●●●●●●●●●●●●●●●●    │
│ Environment      │ UAT                            │
│ Status           │ Active                         │
└──────────────────┴────────────────────────────────┘

[Show Secret]  [Copy Client ID]  [Copy Client Secret]
```

#### 8.2 Copy Your Credentials

**Action:**
1. Click **"Copy"** button next to Client ID (or manually select and copy)
2. Save it somewhere safe (text file, password manager)
3. Click **"Show"** or **"Reveal"** if Client Secret is hidden
4. Click **"Copy"** button next to Client Secret
5. Save it somewhere safe

**Example Credentials:**
```
Client ID: 
a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6

Client Secret: 
AbCdEfGhIjKlMnOpQrStUvWxYz1234567890AbCdEfGhIjKlMnOp
```

---

### Step 9: Add to Your Project

#### 9.1 Open Your .env File

**Action:** Open `Backend/.env` in your code editor

#### 9.2 Add Credentials

**Add these lines:**
```bash
# Airtel Money API (Sandbox/UAT)
AIRTEL_CLIENT_ID=a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
AIRTEL_CLIENT_SECRET=AbCdEfGhIjKlMnOpQrStUvWxYz1234567890AbCdEfGhIjKlMnOp
PAYMENT_ENVIRONMENT=sandbox
```

**Replace** the example values with your actual credentials!

#### 9.3 Save the File

**Action:** Save `Backend/.env`

---

### Step 10: Test Your Credentials

#### 10.1 Run Test Script

**Action:** Open terminal/command prompt and run:

```bash
cd Backend
python test_airtel_auth.py
```

**What You Should See (Success):**
```
✓ Authentication successful!
Access Token: eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Token expires in: 7200 seconds (2 hours)
```

**What You Might See (Error):**
```
✗ Authentication failed: 401 Unauthorized
```

**If Error:**
- Double-check credentials (no extra spaces)
- Ensure PAYMENT_ENVIRONMENT=sandbox
- Wait a few minutes (credentials might not be active yet)
- Verify application is approved in portal

#### 10.2 Alternative: Use Setup Script

**Action:**
```bash
python setup_airtel_credentials.py
```

This interactive script will:
- Ask for your credentials
- Test authentication
- Update your .env file automatically

---

## ✅ Success Checklist

You're done when you have:

- [ ] Airtel developer account created and verified
- [ ] Sandbox application created and approved
- [ ] Client ID copied and saved
- [ ] Client Secret copied and saved
- [ ] Credentials added to Backend/.env
- [ ] PAYMENT_ENVIRONMENT set to "sandbox"
- [ ] Authentication test passed (✓ successful)
- [ ] Ready to start development!

---

## 🚨 Common Issues & Solutions

### Issue 1: Can't Find "Create Application" Button

**Possible Locations:**
- Top right corner
- Center of page
- Under "My Apps" menu
- In a dropdown menu
- Labeled as "+ New", "Add App", "Create"

**Solution:**
- Try different browsers (Chrome, Firefox)
- Clear browser cache
- Log out and log back in
- Complete profile if prompted
- Contact support if still not visible

---

### Issue 2: Application Stuck in "Pending"

**Timeline:**
- Wait at least 24 hours
- Check email (including spam)
- Check portal for status updates

**If >24 Hours:**
- Contact support: support@airtel.africa
- Include application name and reference number
- Ask for sandbox approval status

---

### Issue 3: No Credentials Visible

**Possible Reasons:**
- Application not approved yet
- Looking in wrong section
- Need to subscribe to product first

**Solution:**
- Check application status (should say "Approved" or "Active")
- Look for tabs: "Credentials", "API Keys", "Keys & Secrets"
- Ensure you subscribed to "Collections" product
- Refresh page or log out/in
- Contact support if approved but no credentials

---

### Issue 4: Authentication Fails

**Error:** 401 Unauthorized

**Checklist:**
- [ ] Using correct URL: `https://openapiuat.airtel.africa`
- [ ] Client ID copied correctly (no spaces)
- [ ] Client Secret copied correctly (no spaces)
- [ ] PAYMENT_ENVIRONMENT=sandbox (not production)
- [ ] Application is approved and active
- [ ] Credentials are for UAT/Sandbox (not production)

**Solution:**
- Wait 5-10 minutes (credentials might need activation)
- Regenerate credentials in portal
- Try copying credentials again
- Contact support with error details

---

## 📞 Getting Help

### Airtel Support

**Email:**
```
To: support@airtel.africa
Subject: Sandbox Credentials Request - [Your App Name]

Hello,

I created a sandbox application "[Your App Name]" and need 
assistance with [describe issue].

Account Email: [your-email@example.com]
Application Name: [Your App Name]
Issue: [Describe what's happening]

Please assist.

Thank you,
[Your Name]
```

**Portal Support:**
1. Log in to https://developers.airtel.africa/
2. Look for "Support", "Help", or "Contact"
3. Submit ticket with your issue

**Response Time:** Usually 1-2 business days

---

## 🎉 Next Steps

Once you have working credentials:

1. **Test Payment Request:**
   ```bash
   python manage.py shell
   ```
   ```python
   from decimal import Decimal
   import uuid
   from payments.services.airtel_service import AirtelService
   
   airtel = AirtelService()
   ref = str(uuid.uuid4())
   tx_id = str(uuid.uuid4())
   
   result = airtel.request_to_pay(
       phone_number="256700000001",  # Test number
       amount=Decimal("5000"),
       currency="UGX",
       reference=ref,
       transaction_id=tx_id
   )
   print(result)
   ```

2. **Develop Your Integration**
3. **Test Thoroughly**
4. **When Ready, Apply for Production**

---

## 📚 Related Guides

- **Full Setup Guide:** `Backend/AIRTEL_MONEY_API_SETUP_GUIDE.md`
- **Quick Start:** `Backend/AIRTEL_SETUP_QUICK_START.md`
- **Production Approval:** `Backend/APPLICATION_APPROVAL_GUIDE.md`
- **Sandbox Details:** `Backend/AIRTEL_SANDBOX_APPROVAL.md`

---

**Good luck!** 🚀

Remember: Sandbox approval is usually **instant or within 24 hours** and requires minimal information!
