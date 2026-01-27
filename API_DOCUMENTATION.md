# APF Portal Authentication API Documentation

## Overview

The APF Portal Authentication API provides secure authentication and authorization endpoints for the Accountants and Procurement Professionals portal. The API implements two-factor authentication via email OTP, JWT-based session management, role-based access control, and comprehensive security features including rate limiting and audit logging.

**Base URL**: `http://localhost:8000/api/auth`

**Authentication**: Most endpoints require JWT Bearer token authentication

**Content Type**: `application/json`

---

## Table of Contents

1. [Authentication Flow](#authentication-flow)
2. [Endpoints](#endpoints)
   - [POST /login](#post-login)
   - [POST /verify-otp](#post-verify-otp)
   - [POST /refresh](#post-refresh)
   - [POST /logout](#post-logout)
   - [GET /me](#get-me)
   - [POST /password-reset-request](#post-password-reset-request)
   - [POST /password-reset-confirm](#post-password-reset-confirm)
   - [GET /logs](#get-logs)
3. [Error Codes](#error-codes)
4. [Rate Limiting](#rate-limiting)
5. [Security Considerations](#security-considerations)

---

## Authentication Flow

The authentication process follows a two-factor authentication pattern:

```
1. User submits email + password → POST /api/auth/login
   ↓
2. System verifies credentials and sends OTP via email
   ↓
3. User submits OTP + session_id → POST /api/auth/verify-otp
   ↓
4. System returns JWT access_token and refresh_token
   ↓
5. User includes access_token in Authorization header for protected endpoints
   ↓
6. When access_token expires, use refresh_token → POST /api/auth/refresh
```

---

## Endpoints

### POST /login

Verify user credentials and generate OTP for two-factor authentication.

**URL**: `/api/auth/login`

**Method**: `POST`

**Authentication**: None (public endpoint)

**Rate Limiting**: 5 attempts per 15 minutes per IP/email

#### Request Body

```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| email | string | Yes | User's email address |
| password | string | Yes | User's password |

#### Success Response (200 OK)

```json
{
  "success": true,
  "message": "OTP sent to your email",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Always true for successful requests |
| message | string | Human-readable success message |
| session_id | string (UUID) | Session identifier for OTP verification |

#### Error Responses

**400 Bad Request** - Missing required fields
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email and password are required"
  }
}
```

**401 Unauthorized** - Invalid credentials
```json
{
  "success": false,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password"
  }
}
```

**429 Too Many Requests** - Rate limit exceeded
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many login attempts. Please try again in 15 minutes."
  }
}
```

#### Example

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securePassword123"
  }'
```

---

### POST /verify-otp

Verify OTP code and issue JWT tokens.

**URL**: `/api/auth/verify-otp`

**Method**: `POST`

**Authentication**: None (requires valid session_id from login)

#### Request Body

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "otp": "123456",
  "remember_me": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| session_id | string (UUID) | Yes | Session ID from login response |
| otp | string | Yes | 6-digit OTP code sent via email |
| remember_me | boolean | No | If true, refresh token expires in 30 days; otherwise 24 hours |

#### Success Response (200 OK)

```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "role": "2"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Always true for successful requests |
| access_token | string (JWT) | Access token valid for 1 hour |
| refresh_token | string (JWT) | Refresh token (24 hours or 30 days based on remember_me) |
| user.id | integer | User's unique identifier |
| user.email | string | User's email address |
| user.role | string | User role: "1" (admin) or "2" (member) |

**Note**: Frontend should redirect based on role:
- Role "1" (admin) → `/admin/dashboard`
- Role "2" (member) → `/member/dashboard`

#### Error Responses

**400 Bad Request** - Missing required fields
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Session ID and OTP are required"
  }
}
```

**401 Unauthorized** - Invalid or expired OTP
```json
{
  "success": false,
  "error": {
    "code": "INVALID_OTP",
    "message": "Invalid or expired OTP"
  }
}
```

#### Example

```bash
curl -X POST http://localhost:8000/api/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "otp": "123456",
    "remember_me": true
  }'
```

---

### POST /refresh

Refresh access token using refresh token.

**URL**: `/api/auth/refresh`

**Method**: `POST`

**Authentication**: None (requires valid refresh token)

#### Request Body

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| refresh_token | string (JWT) | Yes | Valid refresh token from login |

#### Success Response (200 OK)

```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Always true for successful requests |
| access_token | string (JWT) | New access token valid for 1 hour |
| refresh_token | string (JWT) | New refresh token (optional, may be same as input) |

#### Error Responses

**400 Bad Request** - Missing refresh token
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Refresh token is required"
  }
}
```

**401 Unauthorized** - Invalid or expired refresh token
```json
{
  "success": false,
  "error": {
    "code": "INVALID_TOKEN",
    "message": "Invalid or expired refresh token"
  }
}
```

#### Example

```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

---

### POST /logout

Invalidate refresh token and log out user.

**URL**: `/api/auth/logout`

**Method**: `POST`

**Authentication**: Required (JWT Bearer token)

#### Request Headers

```
Authorization: Bearer <access_token>
```

#### Request Body

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| refresh_token | string (JWT) | Yes | Refresh token to invalidate |

#### Success Response (200 OK)

```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

#### Error Responses

**400 Bad Request** - Missing refresh token
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Refresh token is required"
  }
}
```

**401 Unauthorized** - Missing or invalid access token
```json
{
  "detail": "Authentication credentials were not provided."
}
```

#### Example

```bash
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

---

### GET /me

Get current authenticated user information.

**URL**: `/api/auth/me`

**Method**: `GET`

**Authentication**: Required (JWT Bearer token)

#### Request Headers

```
Authorization: Bearer <access_token>
```

#### Success Response (200 OK)

```json
{
  "id": 1,
  "email": "user@example.com",
  "role": "2",
  "created_at": "2024-01-15T10:30:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| id | integer | User's unique identifier |
| email | string | User's email address |
| role | string | User role: "1" (admin) or "2" (member) |
| created_at | string (ISO 8601) | Account creation timestamp |

#### Error Responses

**401 Unauthorized** - Missing or invalid access token
```json
{
  "detail": "Authentication credentials were not provided."
}
```

#### Example

```bash
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### POST /password-reset-request

Request password reset token via email.

**URL**: `/api/auth/password-reset-request`

**Method**: `POST`

**Authentication**: None (public endpoint)

#### Request Body

```json
{
  "email": "user@example.com"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| email | string | Yes | User's email address |

#### Success Response (200 OK)

```json
{
  "success": true,
  "message": "Password reset instructions sent to your email"
}
```

**Note**: This endpoint always returns success, even if the email doesn't exist in the system. This is a security best practice to prevent email enumeration attacks.

#### Error Responses

**400 Bad Request** - Missing email
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email is required"
  }
}
```

#### Example

```bash
curl -X POST http://localhost:8000/api/auth/password-reset-request \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

---

### POST /password-reset-confirm

Confirm password reset with token and new password.

**URL**: `/api/auth/password-reset-confirm`

**Method**: `POST`

**Authentication**: None (requires valid reset token)

#### Request Body

```json
{
  "token": "abc123def456ghi789jkl012mno345pqr678stu901vwx234yz",
  "new_password": "newSecurePassword123"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| token | string | Yes | Password reset token from email |
| new_password | string | Yes | New password (minimum 8 characters) |

#### Success Response (200 OK)

```json
{
  "success": true,
  "message": "Password reset successfully"
}
```

**Note**: After successful password reset, all existing refresh tokens for the user are invalidated.

#### Error Responses

**400 Bad Request** - Password validation failed
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Password must be at least 8 characters long"
  }
}
```

**401 Unauthorized** - Invalid or expired token
```json
{
  "success": false,
  "error": {
    "code": "INVALID_RESET_TOKEN",
    "message": "Invalid or expired password reset token"
  }
}
```

#### Example

```bash
curl -X POST http://localhost:8000/api/auth/password-reset-confirm \
  -H "Content-Type: application/json" \
  -d '{
    "token": "abc123def456ghi789jkl012mno345pqr678stu901vwx234yz",
    "new_password": "newSecurePassword123"
  }'
```

---

### GET /logs

Retrieve authentication logs (admin only).

**URL**: `/api/auth/logs`

**Method**: `GET`

**Authentication**: Required (JWT Bearer token with admin role)

#### Request Headers

```
Authorization: Bearer <access_token>
```

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| email | string | No | Filter by email address |
| event_type | string | No | Filter by event type (see Event Types below) |
| start_date | string (ISO 8601) | No | Filter by start date |
| end_date | string (ISO 8601) | No | Filter by end date |
| page | integer | No | Page number (default: 1) |
| page_size | integer | No | Results per page (default: 20) |

#### Event Types

- `login_attempt` - Login attempt (success or failure)
- `login_success` - Successful login
- `login_failure` - Failed login
- `otp_generated` - OTP generated and sent
- `otp_verified` - OTP successfully verified
- `otp_failed` - OTP verification failed
- `password_reset_requested` - Password reset requested
- `password_reset_completed` - Password reset completed
- `rate_limit_triggered` - Rate limit triggered
- `token_refreshed` - Token refreshed
- `logout` - User logged out

#### Success Response (200 OK)

```json
{
  "count": 150,
  "next": "http://localhost:8000/api/auth/logs?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "email": "user@example.com",
      "event_type": "login_success",
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0...",
      "timestamp": "2024-01-15T10:30:00Z",
      "success": true,
      "details": {}
    },
    {
      "id": 2,
      "email": "user@example.com",
      "event_type": "otp_generated",
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0...",
      "timestamp": "2024-01-15T10:30:05Z",
      "success": true,
      "details": {}
    }
  ]
}
```

#### Error Responses

**401 Unauthorized** - Missing or invalid access token
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**403 Forbidden** - User is not an admin
```json
{
  "success": false,
  "error": {
    "code": "FORBIDDEN",
    "message": "You do not have permission to access this resource"
  }
}
```

#### Example

```bash
# Get all logs
curl -X GET http://localhost:8000/api/auth/logs \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Filter by email
curl -X GET "http://localhost:8000/api/auth/logs?email=user@example.com" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Filter by event type and date range
curl -X GET "http://localhost:8000/api/auth/logs?event_type=login_failure&start_date=2024-01-01&end_date=2024-01-31" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## Error Codes

All error responses follow a consistent format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

### Error Code Reference

| Code | HTTP Status | Description |
|------|-------------|-------------|
| VALIDATION_ERROR | 400 | Request validation failed (missing or invalid fields) |
| INVALID_CREDENTIALS | 401 | Email or password is incorrect |
| INVALID_OTP | 401 | OTP is incorrect or expired |
| INVALID_TOKEN | 401 | JWT token is invalid or expired |
| INVALID_RESET_TOKEN | 401 | Password reset token is invalid or expired |
| UNAUTHORIZED | 401 | Authentication required |
| FORBIDDEN | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Resource not found |
| RATE_LIMIT_EXCEEDED | 429 | Too many requests, try again later |
| SERVER_ERROR | 500 | Internal server error |

---

## Rate Limiting

The API implements rate limiting to prevent brute force attacks:

### Login Endpoint Rate Limits

- **5 failed attempts per 15 minutes** per IP address
- **5 failed attempts per 15 minutes** per email address
- Successful login resets the counter for both IP and email
- Rate limit applies to both IP and email independently

### Rate Limit Response

When rate limited, the API returns:

**HTTP 429 Too Many Requests**
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many login attempts. Please try again in 15 minutes."
  }
}
```

**Response Headers**:
```
Retry-After: 900
```

The `Retry-After` header indicates the number of seconds until the rate limit expires.

---

## Security Considerations

### Password Security

- Passwords are hashed using Django's PBKDF2 with SHA256
- Plaintext passwords are never stored or logged
- Password minimum length: 8 characters

### Token Security

- **Access tokens** expire after 1 hour
- **Refresh tokens** expire after:
  - 24 hours (default)
  - 30 days (with remember_me=true)
- Tokens include user ID, email, and role in payload
- All refresh tokens are invalidated after password reset

### OTP Security

- OTPs are 6-digit numeric codes
- OTPs expire after 10 minutes
- OTPs are single-use (invalidated after successful verification)
- New OTP request invalidates previous unexpired OTPs

### Error Message Security

- Authentication failures return generic error messages
- System never reveals whether an email exists in the database
- Password reset always returns success (even for non-existent emails)
- Error responses never include sensitive information (passwords, tokens, internal paths)

### Audit Logging

All authentication events are logged with:
- Timestamp
- User email
- IP address
- User agent
- Event type
- Success/failure status
- Additional details (as applicable)

### CORS Configuration

The API supports CORS for the React frontend:
- Allowed origin: `http://localhost:5173`
- Allowed methods: GET, POST, PUT, DELETE, OPTIONS
- Allowed headers: Content-Type, Authorization

---

## Postman Collection

A Postman collection is available for testing the API. Import the collection from:

`Backend/postman_collection.json`

The collection includes:
- Pre-configured requests for all endpoints
- Environment variables for base URL and tokens
- Example requests and responses
- Test scripts for automated testing

---

## Support

For issues or questions about the API, please contact:
- Email: support@apfportal.com
- Documentation: https://docs.apfportal.com

---

**Last Updated**: January 2026
**API Version**: 1.0.0
