# EmailJS Template Configuration Guide

This guide provides the exact template configurations needed for the APF Portal authentication system.

## Template Parameters Reference

The system sends these exact parameters to EmailJS. Your templates MUST use these variable names.

### OTP Email Template Parameters

| Variable Name | Description | Example Value |
|--------------|-------------|---------------|
| `{{to_email}}` | Recipient's email address | `user@example.com` |
| `{{otp_code}}` | 6-digit verification code | `123456` |
| `{{user_name}}` | User's display name | `john` or `user` |

### Password Reset Email Template Parameters

| Variable Name | Description | Example Value |
|--------------|-------------|---------------|
| `{{to_email}}` | Recipient's email address | `user@example.com` |
| `{{reset_link}}` | Complete password reset URL | `http://localhost:5173/reset-password?token=abc123...` |
| `{{reset_token}}` | Reset token (optional display) | `abc123def456...` |
| `{{user_name}}` | User's display name | `john` or `user` |

---

## Template 1: OTP Verification Email

### EmailJS Dashboard Setup

1. Go to **Email Templates** → **Create New Template**
2. **Template Name**: `APF Portal - OTP Verification`
3. Configure the following fields:

#### To Email
```
{{to_email}}
```

#### From Name
```
APF Portal
```

#### From Email
```
noreply@apfportal.com
```
*(or your verified sender email)*

#### Subject
```
Your APF Portal Verification Code
```

#### Content (HTML)
```html
<!DOCTYPE html>
<html>
<head>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background-color: #4F46E5;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }
        .content {
            background-color: #f9f9f9;
            padding: 30px;
            border: 1px solid #ddd;
            border-top: none;
        }
        .otp-code {
            background-color: #4F46E5;
            color: white;
            font-size: 32px;
            font-weight: bold;
            padding: 15px 30px;
            text-align: center;
            letter-spacing: 8px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .warning {
            background-color: #FEF3C7;
            border-left: 4px solid #F59E0B;
            padding: 12px;
            margin: 20px 0;
        }
        .footer {
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>APF Portal</h1>
    </div>
    <div class="content">
        <h2>Hello {{user_name}},</h2>
        
        <p>You requested a verification code to access your APF Portal account.</p>
        
        <p>Your verification code is:</p>
        
        <div class="otp-code">
            {{otp_code}}
        </div>
        
        <div class="warning">
            <strong>Important:</strong> This code will expire in <strong>10 minutes</strong>.
        </div>
        
        <p>Enter this code on the verification page to complete your login.</p>
        
        <p>If you didn't request this code, please ignore this email or contact support if you have concerns about your account security.</p>
        
        <p>Best regards,<br>
        <strong>APF Portal Team</strong></p>
    </div>
    <div class="footer">
        <p>This is an automated message from APF Portal. Please do not reply to this email.</p>
        <p>&copy; 2024 Accountants and Procurement Professionals Portal. All rights reserved.</p>
    </div>
</body>
</html>
```

#### Content (Plain Text - Fallback)
```
Hello {{user_name}},

You requested a verification code to access your APF Portal account.

Your verification code is: {{otp_code}}

⏰ IMPORTANT: This code will expire in 10 minutes.

Enter this code on the verification page to complete your login.

If you didn't request this code, please ignore this email or contact support if you have concerns about your account security.

Best regards,
APF Portal Team

---
This is an automated message from APF Portal. Please do not reply to this email.
© 2024 Accountants and Procurement Professionals Portal. All rights reserved.
```

---

## Template 2: Password Reset Email

### EmailJS Dashboard Setup

1. Go to **Email Templates** → **Create New Template**
2. **Template Name**: `APF Portal - Password Reset`
3. Configure the following fields:

#### To Email
```
{{to_email}}
```

#### From Name
```
APF Portal
```

#### From Email
```
noreply@apfportal.com
```
*(or your verified sender email)*

#### Subject
```
Reset Your APF Portal Password
```

#### Content (HTML)
```html
<!DOCTYPE html>
<html>
<head>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background-color: #4F46E5;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }
        .content {
            background-color: #f9f9f9;
            padding: 30px;
            border: 1px solid #ddd;
            border-top: none;
        }
        .button {
            display: inline-block;
            background-color: #4F46E5;
            color: white;
            padding: 15px 40px;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            margin: 20px 0;
            text-align: center;
        }
        .button:hover {
            background-color: #4338CA;
        }
        .warning {
            background-color: #FEF3C7;
            border-left: 4px solid #F59E0B;
            padding: 12px;
            margin: 20px 0;
        }
        .security-notice {
            background-color: #FEE2E2;
            border-left: 4px solid #EF4444;
            padding: 12px;
            margin: 20px 0;
        }
        .footer {
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }
        .link-box {
            background-color: #E5E7EB;
            padding: 10px;
            border-radius: 5px;
            word-break: break-all;
            font-size: 12px;
            color: #666;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>APF Portal</h1>
    </div>
    <div class="content">
        <h2>Hello {{user_name}},</h2>
        
        <p>You requested to reset your password for your APF Portal account.</p>
        
        <p>Click the button below to reset your password:</p>
        
        <div style="text-align: center;">
            <a href="{{reset_link}}" class="button">Reset Password</a>
        </div>
        
        <p>Or copy and paste this link into your browser:</p>
        <div class="link-box">
            {{reset_link}}
        </div>
        
        <div class="warning">
            <strong>⏰ Important:</strong> This link will expire in <strong>1 hour</strong>.
        </div>
        
        <div class="security-notice">
            <strong>🔒 Security Notice:</strong> If you didn't request this password reset, please ignore this email. Your password will remain unchanged.
        </div>
        
        <p>For security reasons, we recommend:</p>
        <ul>
            <li>Using a strong, unique password</li>
            <li>Not sharing your password with anyone</li>
            <li>Enabling two-factor authentication</li>
        </ul>
        
        <p>If you have any concerns about your account security, please contact our support team immediately.</p>
        
        <p>Best regards,<br>
        <strong>APF Portal Team</strong></p>
    </div>
    <div class="footer">
        <p>This is an automated message from APF Portal. Please do not reply to this email.</p>
        <p>&copy; 2024 Accountants and Procurement Professionals Portal. All rights reserved.</p>
    </div>
</body>
</html>
```

#### Content (Plain Text - Fallback)
```
Hello {{user_name}},

You requested to reset your password for your APF Portal account.

Click the link below to reset your password:
{{reset_link}}

⏰ IMPORTANT: This link will expire in 1 hour.

🔒 SECURITY NOTICE: If you didn't request this password reset, please ignore this email. Your password will remain unchanged.

For security reasons, we recommend:
- Using a strong, unique password
- Not sharing your password with anyone
- Enabling two-factor authentication

If you have any concerns about your account security, please contact our support team immediately.

Best regards,
APF Portal Team

---
This is an automated message from APF Portal. Please do not reply to this email.
© 2024 Accountants and Procurement Professionals Portal. All rights reserved.
```

---

## Testing Your Templates

### Test in EmailJS Dashboard

1. Go to your template in EmailJS
2. Click **Test It** button
3. Fill in test values:
   - **to_email**: Your email address
   - **otp_code**: `123456` (for OTP template)
   - **reset_link**: `http://localhost:5173/reset-password?token=test123` (for reset template)
   - **reset_token**: `test123` (for reset template)
   - **user_name**: `Test User`
4. Click **Send Test Email**
5. Check your inbox

### Test from Django

```python
# In Django shell (python manage.py shell)
from authentication.services import EmailService

# Test OTP email
EmailService.send_otp_email(
    email='your-email@example.com',
    otp_code='123456',
    user_name='Test User'
)



# Test password reset email
EmailService.send_password_reset_email(
    email='your-email@example.com',
    reset_token='test-token-abc123',
    user_name='Test User'
)
```

---

## Customization Tips

### Branding
- Replace `#4F46E5` (indigo) with your brand color
- Add your logo image URL in the header
- Update footer text with your organization details

### Styling
- Adjust font sizes for better readability
- Modify padding/margins for mobile responsiveness
- Add more visual elements (icons, borders)

### Content
- Adjust tone to match your organization's voice
- Add contact information or support links
- Include social media links in footer

### Localization
- Create separate templates for different languages
- Use conditional logic if EmailJS supports it
- Store language preference in user profile

---

## Common Issues

### Variables Not Showing
- **Problem**: `{{otp_code}}` appears as text instead of the actual code
- **Solution**: Ensure you're using double curly braces `{{variable}}` not single `{variable}`

### Email Goes to Spam
- **Problem**: Emails land in spam folder
- **Solution**: 
  - Use a verified sender email
  - Avoid spam trigger words (FREE, URGENT, etc.)
  - Set up SPF/DKIM records for your domain

### Styling Not Working
- **Problem**: HTML styles don't render in email
- **Solution**: 
  - Use inline styles instead of CSS classes
  - Test with different email clients
  - Provide plain text fallback

### Link Not Clickable
- **Problem**: Reset link appears as plain text
- **Solution**: 
  - Ensure you're using `<a href="{{reset_link}}">` in HTML
  - Check that the link is properly formatted
  - Test in different email clients

---

## Security Checklist

- ✅ Never include sensitive information (passwords, full tokens) in email body
- ✅ Use HTTPS for all links
- ✅ Set appropriate expiration times (10 min for OTP, 1 hour for reset)
- ✅ Include security warnings in emails
- ✅ Use verified sender email addresses
- ✅ Monitor for suspicious email activity
- ✅ Rate limit email sending to prevent abuse

---

## Support

If you encounter issues with EmailJS templates:
1. Check EmailJS dashboard for error logs
2. Verify all variable names match exactly
3. Test with EmailJS's built-in test feature
4. Review EmailJS documentation: https://www.emailjs.com/docs/
5. Contact EmailJS support if needed
