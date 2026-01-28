# API Version Update - v1 Migration

## Summary
All API endpoints have been updated to use versioned URLs with `/api/v1/` prefix.

## Changes Made

### Backend (Django)
- Updated `Backend/api/urls.py` to use `/api/v1/` prefix for all endpoints
- Updated health check endpoint to reflect new versioned URLs
- Updated `Backend/openapi.yaml` server URLs
- Updated `Backend/postman_collection.json` base URL

### Frontend (React/TypeScript)
- Updated `portal/src/pages/LoginPage.tsx` - login endpoint
- Updated `portal/src/pages/otpPage.tsx` - OTP verification endpoint
- Updated `portal/src/services/applicationApi.ts` - application submission endpoint
- Updated `portal/src/components/contactPage-components/ContactForm.tsx` - contact form endpoint

## New API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/verify-otp` - OTP verification
- `POST /api/v1/auth/refresh` - Token refresh
- `POST /api/v1/auth/logout` - User logout
- `GET /api/v1/auth/me` - Current user info
- `POST /api/v1/auth/password-reset-request` - Request password reset
- `POST /api/v1/auth/password-reset-confirm` - Confirm password reset
- `GET /api/v1/auth/logs` - Auth logs (admin only)

### Applications
- `GET /api/v1/applications/` - List applications
- `POST /api/v1/applications/` - Submit application
- `GET /api/v1/applications/{id}/` - Get application details
- `PUT /api/v1/applications/{id}/` - Update application
- `DELETE /api/v1/applications/{id}/` - Delete application

### Contacts
- `POST /api/v1/contacts/submit/` - Submit contact form

### Dashboard
- `GET /api/v1/` - Dashboard endpoints

## Testing

### Test with curl
```bash
# Login
curl "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'

# Health check
curl "http://localhost:8000/"
```

### Production URLs
Replace `http://localhost:8000` with `https://apf-api.onrender.com` for production:
```bash
curl "https://apf-api.onrender.com/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

## Benefits of API Versioning

1. **Future-proof**: Easy to introduce breaking changes in v2 while maintaining v1
2. **Clear contracts**: Clients know exactly which API version they're using
3. **Gradual migration**: Can support multiple versions simultaneously if needed
4. **Better documentation**: Version-specific docs are clearer

## Next Steps

1. Restart Django server: `python manage.py runserver`
2. Test all endpoints with the new URLs
3. Update any external integrations or documentation
4. Deploy to production with updated environment variables
