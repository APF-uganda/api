# Email Templates

This folder contains HTML email templates for the APF Portal.

**Location:** `Backend/api/templates/email/`

This is a project-level templates directory, shared across all Django apps.

## Templates

### 1. otp_email.html
Used for login verification OTP emails.

**Variables:**
- `{{ user_name }}` - Recipient's name
- `{{ otp_code }}` - 6-digit verification code

**Used by:**
- `EmailService.send_otp_email()`

**Design:**
- Purple header (#4A2882)
- Lock icon 🔓
- Clear "Login Verification" title

### 2. password_reset_email.html
Used for password reset verification emails.

**Variables:**
- `{{ user_name }}` - Recipient's name
- `{{ otp_code }}` - 6-digit verification code

**Used by:**
- `EmailService.send_password_reset_email()`

**Design:**
- Red header (#DC2626) to indicate security action
- Lock icon 🔐
- Security tips and warnings
- Clear "Password Reset Request" title

### 3. approval_email.html
Sent when a member's application is approved.

**Variables:**
- `{{ user_name }}` - Recipient's name
- `{{ login_url }}` - URL to the login page

**Used by:**
- `EmailService.send_approval_email()`

**Design:**
- Green gradient header
- Celebration icon 🎉
- Welcome message and next steps
- Login button

## Template Configuration

Templates are configured in `api/settings.py`:

```python
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # Project-level templates
        "APP_DIRS": True,  # Also search in app-level templates
        ...
    },
]
```

## Usage in Code

```python
from django.template.loader import render_to_string

# Render a template
html_content = render_to_string('email/otp_email.html', {
    'user_name': 'John',
    'otp_code': '123456'
})
```

## Template Differences

### Login OTP vs Password Reset
We use separate templates to make the purpose clear:

| Feature | Login OTP | Password Reset |
|---------|-----------|----------------|
| Header Color | Purple (#4A2882) | Red (#DC2626) |
| Icon | 🔓 | 🔐 |
| Title | Login Verification | Password Reset Request |
| Security Tips | Basic | Enhanced with password tips |
| Urgency | Standard | Higher (security action) |

## Customization

To customize the email templates:

1. Edit the HTML files in this folder
2. Use Django template syntax: `{{ variable_name }}`
3. Test your changes with `python test_smtp_email.py`
4. Inline CSS is used for email client compatibility

## Design Guidelines

- Keep HTML simple (email clients have limited CSS support)
- Use inline styles (external stylesheets don't work in emails)
- Test in multiple email clients (Gmail, Outlook, etc.)
- Keep images minimal or use emoji for icons
- Ensure mobile responsiveness
- Use color psychology (red for security, green for success, purple for brand)

## Adding New Templates

1. Create a new `.html` file in this folder
2. Add a method in `authentication/email_service_smtp.py`
3. Use `render_to_string('email/your_template.html', context)`
4. Test thoroughly before deploying
