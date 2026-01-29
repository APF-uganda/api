# APF Portal Backend

Django REST API backend for the APF Portal contact form and future features.

## Quick Start (Windows)

Run the PowerShell setup script:
```powershell
.\quick_setup.ps1
```

Then start the server:
```bash
python manage.py runserver
```

## Manual Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Create a `.env` file from the example:
```bash
copy .env.example .env
```

Generate a Django secret key:
```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Update `.env` with your secret key and database credentials.

### 3. Create Database
```bash
psql -U postgres
CREATE DATABASE apf_portal;
\q
```

### 4. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create Admin User (Optional)
```bash
python manage.py createsuperuser
```

### 6. Start Server
```bash
python manage.py runserver
```

## API Endpoints

### 📚 Interactive API Documentation

The backend includes comprehensive Swagger/OpenAPI documentation:

- **Swagger UI**: `http://localhost:8000/api/docs/` - Interactive API testing
- **ReDoc**: `http://localhost:8000/api/redoc/` - Clean documentation view
- **OpenAPI Schema**: `http://localhost:8000/swagger.json` - Raw schema

See [SWAGGER_DOCUMENTATION.md](./SWAGGER_DOCUMENTATION.md) for detailed usage instructions.

### Contact Messages

#### Submit Contact Form
```
POST /api/contacts/submit/
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "subject": "Inquiry about membership",
  "message": "I would like to know more about..."
}

Response (201 Created):
{
  "message": "Your message has been sent successfully!",
  "data": {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com",
    "subject": "Inquiry about membership",
    "message": "I would like to know more about...",
    "created_at": "2024-01-20T10:30:00Z",
    "is_read": false
  }
}
```

#### List All Messages (Admin)
```
GET /api/contacts/list/

Response (200 OK):
[
  {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com",
    "subject": "Inquiry about membership",
    "message": "I would like to know more about...",
    "created_at": "2024-01-20T10:30:00Z",
    "is_read": false
  }
]
```

## Admin Panel

Access the Django admin panel at `http://localhost:8000/admin/`

Features:
- View all contact messages
- Mark messages as read/unread
- Search and filter messages
- Export data

## Database Schema

### ContactMessage Model
- `id`: Primary key (auto-generated)
- `name`: CharField (max 200 characters)
- `email`: EmailField
- `subject`: CharField (max 300 characters)
- `message`: TextField
- `created_at`: DateTimeField (auto-generated)
- `is_read`: BooleanField (default: False)

## Frontend Integration

The frontend React app connects to this backend. Make sure:
1. Backend is running on `http://localhost:8000`
2. CORS is configured for frontend origin (default: `http://localhost:5173`)
3. Frontend makes POST requests to `/api/contacts/submit/`

## Testing

Test the API with curl:
```bash
curl -X POST http://localhost:8000/api/contacts/submit/ \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Test User\",\"email\":\"test@example.com\",\"subject\":\"Test\",\"message\":\"Testing the API\"}"
```

## Troubleshooting

### Database Connection Error
- Ensure PostgreSQL is running
- Check database credentials in `.env`
- Verify database `apf_portal` exists

### CORS Error
- Check `CORS_ALLOWED_ORIGINS` in `settings.py`
- Ensure frontend URL is included

### Module Not Found
- Activate virtual environment: `.\venv\Scripts\Activate.ps1`
- Install dependencies: `pip install -r requirements.txt`

## Production Deployment

For production:
1. Set `DEBUG=False` in `.env`
2. Update `ALLOWED_HOSTS` in `settings.py`
3. Use environment variables for sensitive data
4. Set up proper database backups
5. Use a production WSGI server (gunicorn, uwsgi)
6. Configure HTTPS
7. Set up proper logging

## Dependencies

- Django 5.2.7
- Django REST Framework 3.15.2
- django-cors-headers 4.6.0
- psycopg2-binary 2.9.10
- django-environ 0.11.2
