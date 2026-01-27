# EmailJS Setup Guide

This document provides instructions for setting up EmailJS for the APF Portal authentication system.

## 📚 Documentation Index

- **🚀 Quick Start**: See `EMAILJS_QUICK_SETUP.md` for 5-minute setup
- **📋 Variable Reference**: See `EMAILJS_VARIABLE_MAPPING.md` for exact variable names
- **🎨 Template Guide**: See `EMAILJS_TEMPLATE_GUIDE.md` for professional HTML templates
- **📖 This Guide**: Complete setup and configuration instructions

## Overview

The authentication system uses EmailJS to send:
1. **OTP (One-Time Password)** emails for two-factor authentication
2. **Password Reset** emails with reset links

### Required Template Variables

**OTP Email MUST include:**
- `{{to_email}}` - Recipient email
- `{{otp_code}}` - 6-digit verification code
- `{{user_name}}` - User's display name

**Password Reset Email MUST include:**
- `{{to_email}}` - Recipient email
- `{{reset_link}}` - Complete password reset URL
- `{{user_name}}` - User's display name
- `{{reset_token}}` - Reset token (optional)

## EmailJS Configuration Steps

### 1. Create EmailJS Account

1. Go to [EmailJS](https://www.emailjs.com/)
2. Sign up for a free account
3. Verify your email address

### 2. Add Email Service

1. In the EmailJS dashboard, go to **Email Services**
2. Click **Add New Service**
3. Choose your email provider (Gmail, Outlook, etc.)
4. Follow the setup instructions for your provider
5. Note down your **Service ID** (e.g., `service_abc123`)

### 3. Create Email Templates

#### OTP Email Template

1. Go to **Email Templates** in the dashboard
2. Click **Create New Template**
3. Name it "OTP Verification"
4. Use the following template variables:
   - `{{to_email}}` - Recipient email address
   - `{{otp_code}}` - 6-digit OTP code
   - `{{user_name}}` - User's name

**Sample Template:**
```
Subject: Your APF Portal Verification Code

Hello {{user_name}},

Your verification code is: {{otp_code}}

This code will expire in 10 minutes.

If you didn't request this code, please ignore this email.

Best regards,
APF Portal Team
```

5. Note down the **Template ID** (e.g., `template_otp123`)

#### Password Reset Email Template

1. Create another new template
2. Name it "Password Reset"
3. Use the following template variables:
   - `{{to_email}}` - Recipient email address
   - `{{reset_link}}` - Full password reset URL
   - `{{reset_token}}` - Reset token (optional, for display)
   - `{{user_name}}` - User's name

**Sample Template:**
```
Subject: Reset Your APF Portal Password

Hello {{user_name}},

You requested to reset your password for your APF Portal account.

Click the link below to reset your password:
{{reset_link}}

This link will expire in 1 hour.

If you didn't request this password reset, please ignore this email.

Best regards,
APF Portal Team
```

4. Note down the **Template ID** (e.g., `template_reset456`)

### 4. Get Public Key

1. Go to **Account** in the EmailJS dashboard
2. Find your **Public Key** (also called User ID)
3. Note it down (e.g., `user_xyz789`)

### 5. Configure Environment Variables

Add the following to your `.env` file:

```bash
# EmailJS Configuration
EMAILJS_SERVICE_ID=service_abc123
EMAILJS_TEMPLATE_ID_OTP=template_otp123
EMAILJS_TEMPLATE_ID_PASSWORD_RESET=template_reset456
EMAILJS_PUBLIC_KEY=user_xyz789
```

Replace the example values with your actual EmailJS credentials.

## Testing Email Functionality

### Test OTP Email

```python
from authentication.services import EmailService

# Send test OTP email
result = EmailService.send_otp_email(
    email='your-email@example.com',
    otp_code='123456',
    user_name='Test User'
)

print(f"Email sent: {result}")
```

### Test Password Reset Email

```python
from authentication.services import EmailService

# Send test password reset email
result = EmailService.send_password_reset_email(
    email='your-email@example.com',
    reset_token='test-token-123',
    user_name='Test User'
)

print(f"Email sent: {result}")
```

## Troubleshooting

### Email Not Sending

1. **Check credentials**: Verify all EmailJS credentials in `.env` are correct
2. **Check service status**: Ensure your EmailJS service is active
3. **Check email provider**: Some providers require app-specific passwords
4. **Check logs**: Look for error messages in Django logs

### Email Goes to Spam

1. Configure SPF and DKIM records for your domain
2. Use a verified sender email address
3. Avoid spam trigger words in templates
4. Test with different email providers

### Rate Limits

EmailJS free tier has limits:
- 200 emails per month
- Consider upgrading for production use

## Security Best Practices

1. **Never commit credentials**: Keep `.env` file out of version control
2. **Use environment variables**: Always use environment variables for sensitive data
3. **Rotate keys**: Periodically rotate your EmailJS public key
4. **Monitor usage**: Check EmailJS dashboard for unusual activity

## Production Considerations

1. **Upgrade plan**: Free tier may not be sufficient for production
2. **Custom domain**: Use a custom domain for professional emails
3. **Email templates**: Design professional HTML email templates
4. **Error handling**: The system gracefully handles email failures
5. **Monitoring**: Set up alerts for email delivery failures

## API Reference

### EmailService.send_otp_email()

Sends an OTP verification email.

**Parameters:**
- `email` (str): Recipient email address
- `otp_code` (str): 6-digit OTP code
- `user_name` (str, optional): User's name for personalization

**Returns:**
- `bool`: True if email sent successfully, False otherwise

### EmailService.send_password_reset_email()

Sends a password reset email with reset link.

**Parameters:**
- `email` (str): Recipient email address
- `reset_token` (str): Password reset token
- `user_name` (str, optional): User's name for personalization

**Returns:**
- `bool`: True if email sent successfully, False otherwise

## Support

For EmailJS-specific issues, refer to:
- [EmailJS Documentation](https://www.emailjs.com/docs/)
- [EmailJS Support](https://www.emailjs.com/support/)
