# Login Issues - Fixed

## Issues Identified and Resolved

### ✅ Issue 1: Wrong Password Proceeding to OTP Page
**Status:** FIXED

**Problem:** The LoginView was not properly unpacking the tuple returned by `OTPService.generate_otp()`.

**Solution:** Updated `Backend/authentication/views.py` line 76:
```python
# Before (incorrect):
session_id = OTPService.generate_otp(user)

# After (correct):
otp, session_id = OTPService.generate_otp(user)
```

**Result:** Now correctly returns 401 Unauthorized for wrong passwords.

---

### ✅ Issue 2: OTP Email Not Being Sent
**Status:** FIXED

**Problem:** EmailJS blocks server-side API calls with 403 error. EmailJS is designed for client-side (browser) use only.

**Solution:** Replaced EmailJS with Django's built-in SMTP email system.

**Changes Made:**

1. **Updated `Backend/api/settings.py`:**
   - Added Django email configuration
   - Set default to console backend for development (prints emails to terminal)

2. **Updated `Backend/authentication/services.py`:**
   - Replaced EmailJS API calls with Django's `send_mail()`
   - Emails now use SMTP (or console for development)

**Current Behavior (Development Mode):**
- Emails are printed to the Django server console/terminal
- You can see the OTP code in the terminal output
- No actual emails are sent (perfect for testing)

---

## Testing the Login Flow

### 1. Start Django Server
```bash
cd Backend
python manage.py runserver
```

### 2. Test Login with Wrong Password
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "bashkiko@gmail.com", "password": "wrongpassword"}'
```

**Expected Response:**
```json
{
  "success": false,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password"
  }
}
```
**Status Code:** 401 Unauthorized

### 3. Test Login with Correct Password
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "bashkiko@gmail.com", "password": "Nakaye0@1"}'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "OTP sent to your email",
  "session_id": "a2e69842-0ee1-40c2-95cd-e126d3b3fabb"
}
```
**Status Code:** 200 OK

**Check Terminal:** You'll see the email with OTP code printed in the Django server console.

### 4. Verify OTP
```bash
curl -X POST http://localhost:8000/api/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "<session_id_from_step_3>",
    "otp": "<otp_code_from_terminal>",
    "remember_me": true
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "email": "bashkiko@gmail.com",
    "role": "1"
  }
}
```

---

## Production Setup (Real Email Sending)

For production, configure SMTP to send real emails. See `SMTP_EMAIL_SETUP.md` for detailed instructions.

### Quick Setup for Gmail:

1. **Update `.env`:**
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=APF Portal <your-email@gmail.com>
```

2. **Generate Gmail App Password:**
   - Go to: https://myaccount.google.com/apppasswords
   - Enable 2-Factor Authentication first
   - Generate an app password
   - Use that password in `EMAIL_HOST_PASSWORD`

3. **Restart Django Server**

Now real emails will be sent to users!

---

## Admin User Credentials

**Email:** bashkiko@gmail.com  
**Password:** Nakaye0@1  
**Role:** Admin (role=1)  
**User ID:** 1

---

## Frontend Integration

The frontend should:

1. **POST to `/api/auth/login`** with email and password
2. **Check response status:**
   - `401` = Show error "Invalid email or password"
   - `200` = Navigate to OTP page with `session_id`
3. **On OTP page:** POST to `/api/auth/verify-otp` with `session_id`, `otp`, and `remember_me`
4. **On success:** Store tokens and redirect based on role:
   - `role === "1"` → `/admin/dashboard`
   - `role === "2"` → `/member/dashboard`

---

## Files Modified

1. `Backend/authentication/views.py` - Fixed OTP generation unpacking
2. `Backend/authentication/services.py` - Replaced EmailJS with Django SMTP
3. `Backend/api/settings.py` - Added email configuration
4. `Backend/SMTP_EMAIL_SETUP.md` - Production email setup guide (NEW)
5. `Backend/LOGIN_FIXES_SUMMARY.md` - This file (NEW)

---

## Next Steps

1. ✅ Test login flow with frontend
2. ✅ Verify OTP appears in Django console
3. ✅ Test complete authentication flow
4. 📧 For production: Configure SMTP (see SMTP_EMAIL_SETUP.md)
