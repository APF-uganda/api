# Swagger API Documentation

## Overview

The APF Portal Backend now includes interactive API documentation using Swagger (drf-yasg). This provides a user-friendly interface to explore and test all API endpoints.

## Accessing the Documentation

### Swagger UI (Interactive)
- **URL**: `http://localhost:8000/api/docs/`
- **Production**: `https://your-domain.com/api/docs/`

The Swagger UI provides:
- Interactive API testing
- Request/response examples
- Authentication support
- Parameter descriptions

### ReDoc (Alternative View)
- **URL**: `http://localhost:8000/api/redoc/`
- **Production**: `https://your-domain.com/api/redoc/`

ReDoc provides a cleaner, read-only documentation view.

### OpenAPI Schema (JSON/YAML)
- **JSON**: `http://localhost:8000/swagger.json`
- **YAML**: `http://localhost:8000/swagger.yaml`

Download the raw OpenAPI schema for use with other tools.

## Using Swagger UI

### 1. Testing Public Endpoints

Public endpoints (like login) don't require authentication:

1. Navigate to `/api/docs/`
2. Find the endpoint (e.g., `POST /api/v1/auth/login`)
3. Click "Try it out"
4. Fill in the request body
5. Click "Execute"
6. View the response

### 2. Testing Protected Endpoints

Protected endpoints require JWT authentication:

1. First, login using `/api/v1/auth/login` and `/api/v1/auth/verify-otp`
2. Copy the `access_token` from the response
3. Click the "Authorize" button at the top of the page
4. Enter: `Bearer <your-access-token>`
5. Click "Authorize"
6. Now you can test protected endpoints

### 3. Example Authentication Flow

```bash
# 1. Login
POST /api/v1/auth/login
{
  "email": "user@example.com",
  "password": "password123"
}

# Response includes session_id and otp_code

# 2. Verify OTP
POST /api/v1/auth/verify-otp
{
  "session_id": "uuid-from-login",
  "otp": "123456",
  "remember_me": false
}

# Response includes access_token and refresh_token

# 3. Use the access_token in Authorize button
Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

# 4. Now test protected endpoints
GET /api/v1/auth/me
```

## Documented Endpoints

### Authentication (`/api/v1/auth/`)
- ✅ `POST /login` - Login with email/password
- ✅ `POST /verify-otp` - Verify OTP and get tokens
- ✅ `POST /refresh` - Refresh access token
- ✅ `POST /logout` - Logout and blacklist token
- ✅ `GET /me` - Get current user info
- ✅ `POST /password-reset-request` - Request password reset
- ✅ `POST /password-reset-confirm` - Confirm password reset
- ✅ `GET /logs` - Get auth logs (admin only)

### Other Endpoints
The following apps also have endpoints that will appear in Swagger:
- Contacts (`/api/v1/contacts/`)
- Applications (`/api/v1/applications/`)
- Dashboard (`/api/v1/`)

## Adding Documentation to New Endpoints

To add Swagger documentation to your views, use the `@swagger_auto_schema` decorator:

```python
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class MyView(APIView):
    @swagger_auto_schema(
        operation_description="Description of what this endpoint does",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['field1'],
            properties={
                'field1': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Field description'
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Success response",
                examples={
                    "application/json": {
                        "success": True,
                        "data": {}
                    }
                }
            ),
            400: "Bad Request",
            401: "Unauthorized"
        },
        tags=['MyApp'],
        security=[{'Bearer': []}]  # For protected endpoints
    )
    def post(self, request):
        # Your view logic
        pass
```

## Configuration

Swagger settings are configured in `Backend/api/settings.py`:

```python
SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Authorization header. Example: 'Bearer <token>'",
        }
    },
    "USE_SESSION_AUTH": False,
}
```

## Benefits

1. **Interactive Testing**: Test APIs directly from the browser
2. **Documentation**: Auto-generated from code
3. **Type Safety**: Request/response schemas are validated
4. **Team Collaboration**: Share API docs with frontend developers
5. **Client Generation**: Generate API clients from OpenAPI schema

## Next Steps

1. Add documentation to remaining endpoints in:
   - `contacts/views.py`
   - `applications/views.py`
   - `dashboard/views.py`
   - `notifications/views.py`

2. Customize the OpenAPI schema with more details:
   - Add more examples
   - Add detailed descriptions
   - Add response schemas

3. Consider adding API versioning documentation

## Resources

- [drf-yasg Documentation](https://drf-yasg.readthedocs.io/)
- [OpenAPI Specification](https://swagger.io/specification/)
- [Swagger UI](https://swagger.io/tools/swagger-ui/)
