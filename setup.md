# Backend Setup Instructions

## Prerequisites
- Python 3.8+
- PostgreSQL installed and running
- pip (Python package manager)

## Setup Steps

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create .env file
Copy `.env.example` to `.env` and update with your credentials:
```bash
cp .env.example .env
```

Edit `.env` and set:
- `SECRET_KEY`: Generate a new Django secret key
- `DB_PASSWORD`: Your PostgreSQL password (currently: Nakaye0@#)

### 3. Create PostgreSQL Database
```sql
CREATE DATABASE apf_portal;
```

Or using psql command:
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

### 5. Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

### 6. Run Development Server
```bash
python manage.py runserver
```

The server will start at `http://localhost:8000`

### 7. Access API Documentation
Once the server is running, access the interactive API documentation:
- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/

See [SWAGGER_DOCUMENTATION.md](./SWAGGER_DOCUMENTATION.md) for detailed usage.
```

The API will be available at: `http://localhost:8000`

## API Endpoints

### Contact Form
- **POST** `/api/contacts/submit/` - Submit a contact message
  ```json
  {
    "name": "John Doe",
    "email": "john@example.com",
    "subject": "Inquiry",
    "message": "Your message here"
  }
  ```

- **GET** `/api/contacts/list/` - List all contact messages (admin)

### Admin Panel
Access at: `http://localhost:8000/admin/`

## Testing the API

Using curl:
```bash
curl -X POST http://localhost:8000/api/contacts/submit/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "subject": "Test Subject",
    "message": "Test message"
  }'
```
