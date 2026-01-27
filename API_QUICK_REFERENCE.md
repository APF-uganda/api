# APF Portal Authentication API - Quick Reference

## Base URL
```
http://localhost:8000/api/auth
```

## Quick Start

### 1. Login Flow
```bash
# Step 1: Login with credentials
POST /api/auth/login
{
  "email": "user@example.com",
  "password": "password123"
}
# Returns: { "session_id": "..." }

# Step 2: Verify OTP (check email for code)
POST /api/auth/verify-otp
{
  "session_id": "...",
  "otp": "123456",
  "remember_me": false
}
# Returns: { "access_token": "...", "refresh_token": "...", "user": {...} }

# Step 3: Use access token for protected endpoints
GET /api/auth/me
Authorization: Bearer <access_token>
```

## Endpoints Summary

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/login` | POST | No | Login with email/password, get session_id |
| `/verify-otp` | POST | No | Verify OTP, get JWT tokens |
| `/refresh` | POST | No | Refresh access token |
| `/logout` | POST | Yes | Logout and invalidate refresh token |
| `/me` | GET | Yes | Get current user info |
| `/password-reset-request` | POST | No | Request password reset |
| `/password-reset-confirm` | POST | No | Confirm password reset |
| `/logs` | GET | Yes (Admin) | Get authentication logs |

## Common Request Examples

### Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass123"}'
```

### Verify OTP
```bash
curl -X POST http://localhost:8000/api/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"session_id":"...","otp":"123456","remember_me":false}'
```

### Get Current User
```bash
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### Refresh Token
```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"..."}'
```

### Logout
```bash
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{"refresh_token":"..."}'
```

## Response Formats

### Success Response
```json
{
  "success": true,
  "data": { ... }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error description"
  }
}
```

## Common Error Codes

| Code | Status | Meaning |
|------|--------|---------|
| `VALIDATION_ERROR` | 400 | Missing or invalid fields |
| `INVALID_CREDENTIALS` | 401 | Wrong email/password |
| `INVALID_OTP` | 401 | Wrong or expired OTP |
| `INVALID_TOKEN` | 401 | Invalid/expired JWT |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many attempts |

## Token Expiration

| Token Type | Default | With remember_me |
|------------|---------|------------------|
| Access Token | 1 hour | 1 hour |
| Refresh Token | 24 hours | 30 days |
| OTP | 10 minutes | N/A |
| Password Reset Token | 1 hour | N/A |

## Rate Limiting

- **5 failed login attempts** per 15 minutes
- Applies per IP address AND per email
- Successful login resets counters
- Returns `429` with `Retry-After` header

## User Roles

| Role | Value | Dashboard Route |
|------|-------|-----------------|
| Admin | "1" | `/admin/dashboard` |
| Member | "2" | `/member/dashboard` |

## Security Notes

- ✅ Passwords hashed with PBKDF2-SHA256
- ✅ OTPs are single-use and expire in 10 minutes
- ✅ Generic error messages prevent user enumeration
- ✅ All auth events logged with IP and timestamp
- ✅ Password reset invalidates all refresh tokens
- ✅ CORS enabled for localhost:5173

## Testing

### Postman Collection
Import `Backend/postman_collection.json` for pre-configured requests

### Test Users
Create test users with Django management command:
```bash
python manage.py create_admin admin@example.com adminpass123
```

## Need More Details?

See full documentation: `Backend/API_DOCUMENTATION.md`
