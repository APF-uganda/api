# Swagger Documentation - Quick Start 🚀

## ✅ Setup Complete!

Swagger/OpenAPI documentation has been successfully integrated into the APF Portal Backend.

## Access the Documentation

### Start the Server
```bash
cd Backend
python manage.py runserver
```

### Open Swagger UI
Navigate to: **http://localhost:8000/api/docs/**

You'll see an interactive API documentation interface with all your endpoints.

## Quick Test

1. **Open Swagger UI**: http://localhost:8000/api/docs/
2. **Find the login endpoint**: `POST /api/v1/auth/login`
3. **Click "Try it out"**
4. **Enter test data**:
   ```json
   {
     "email": "test@example.com",
     "password": "password123"
   }
   ```
5. **Click "Execute"**
6. **View the response**

## Testing Protected Endpoints

For endpoints that require authentication:

1. Login and get your access token
2. Click the **"Authorize"** button (🔒 icon at top)
3. Enter: `Bearer <your-access-token>`
4. Click "Authorize"
5. Now you can test protected endpoints like `/api/v1/auth/me`

## Available Documentation Views

- **Swagger UI** (Interactive): http://localhost:8000/api/docs/
- **ReDoc** (Clean view): http://localhost:8000/api/redoc/
- **JSON Schema**: http://localhost:8000/swagger.json
- **YAML Schema**: http://localhost:8000/swagger.yaml

## What's Documented

All authentication endpoints are fully documented:
- ✅ Login
- ✅ Verify OTP
- ✅ Refresh Token
- ✅ Logout
- ✅ Get Current User
- ✅ Password Reset Request
- ✅ Password Reset Confirm
- ✅ Auth Logs (Admin)

## Configuration Fixed

The following issues were also resolved:
- ✅ Fixed `.env` file format (quoted special characters)
- ✅ Added `DB_SSL_MODE` for local PostgreSQL (no SSL required)
- ✅ Updated `.env.example` with proper format

## Database Connection Note

For **local PostgreSQL**, use:
```env
DB_SSL_MODE=disable
```

For **Neon/Production**, use:
```env
DB_SSL_MODE=require
```

## Next Steps

See [SWAGGER_DOCUMENTATION.md](./SWAGGER_DOCUMENTATION.md) for:
- Detailed usage instructions
- How to add documentation to other endpoints
- Advanced configuration options
- Troubleshooting guide

## Resources

- Swagger UI: http://localhost:8000/api/docs/
- Full Documentation: [SWAGGER_DOCUMENTATION.md](./SWAGGER_DOCUMENTATION.md)
- Setup Details: [SWAGGER_SETUP_COMPLETE.md](./SWAGGER_SETUP_COMPLETE.md)
