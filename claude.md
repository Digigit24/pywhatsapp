# PyWhatsApp - Multi-Tenant WhatsApp Business API

## Overview

PyWhatsApp is a FastAPI-based WhatsApp Business API application with multi-tenant support, real-time messaging via WebSockets, and both session-based (HTML UI) and JWT (API) authentication.

**Tech Stack:**
- **Framework:** FastAPI 0.109.2
- **Database:** PostgreSQL with SQLAlchemy 2.0.25
- **Migrations:** Alembic 1.13.1
- **WhatsApp SDK:** PyWA
- **Authentication:** Session-based + JWT
- **Real-time:** WebSockets

---

## Quick Start

### 1. Prerequisites

- Python 3.8+
- PostgreSQL 12+
- WhatsApp Business API credentials (Phone ID, Token)

### 2. Installation

```bash
# Clone the repository
git clone <repository-url>
cd pywhatsapp

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the project root:

```env
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/whatspy_db
# Or configure individually:
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=whatspy_db

# WhatsApp Configuration
WHATSAPP_PHONE_ID=your_phone_id
WHATSAPP_TOKEN=your_access_token
VERIFY_TOKEN=your_verify_token
CALLBACK_URL=https://your-domain.com/webhooks

# Optional WhatsApp Settings
FB_APP_ID=your_app_id
FB_APP_SECRET=your_app_secret
VALIDATE_UPDATES=true
MESSAGE_BUFFER=200

# Authentication
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin@123
SESSION_SECRET_KEY=change-this-secret-key-in-production
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60

# Multi-tenant
DEFAULT_TENANT_ID=bc531d42-ac91-41df-817e-26c339af6b3a

# Logging
LOG_LEVEL=INFO
```

### 4. Database Setup

#### Create PostgreSQL Database

```bash
# Login to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE whatspy_db;

# Exit
\q
```

#### Initialize Database (Fresh Installation)

Run the auto-setup script to create tables and admin user:

```bash
python auto_setup.py
```

This script will:
- Test database connection
- Drop and recreate all tables (FRESH START)
- Create admin user
- Verify all tables are working

**Expected Output:**
```
✅ SETUP COMPLETED SUCCESSFULLY!
📌 Admin Login Credentials:
   Username: admin
   Password: admin@123
   Tenant ID: default
```

### 5. Run the Application

#### Development Mode

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

#### Production Mode

```bash
# Using uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8002 --workers 4

# Or using gunicorn with uvicorn workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8002
```

### 6. Access the Application

- **Login:** http://localhost:8002/login
- **Chat UI:** http://localhost:8002/chat
- **Dashboard:** http://localhost:8002/dashboard
- **API Docs:** http://localhost:8002/docs
- **Health Check:** http://localhost:8002/healthz

---

## Database Migrations

### Overview

This project uses Alembic for database migrations. Migrations track changes to your database schema over time.

### When to Use Migrations

- **New Database:** Use `auto_setup.py` for fresh installations
- **Schema Changes:** Use Alembic migrations when modifying existing databases

### Changing Database URL

If you need to change your database URL:

1. **Update `.env` file:**
   ```env
   DATABASE_URL=postgresql://new_user:new_password@new_host:5432/new_database
   ```

2. **Create the new database:**
   ```bash
   psql -U postgres
   CREATE DATABASE new_database;
   \q
   ```

3. **Run auto-setup for fresh start:**
   ```bash
   python auto_setup.py
   ```

   OR use migrations to preserve data:

4. **Initialize Alembic (if needed):**
   ```bash
   alembic init alembic  # Only if alembic folder doesn't exist
   ```

5. **Run existing migrations:**
   ```bash
   alembic upgrade head
   ```

### Creating New Migrations

When you modify models (add/remove tables or columns):

```bash
# Generate migration automatically
alembic revision --autogenerate -m "description of changes"

# Example:
alembic revision --autogenerate -m "add user profile table"
```

### Running Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade <revision_id>

# Downgrade one revision
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade <revision_id>

# Show current revision
alembic current

# Show migration history
alembic history
```

### Migration Best Practices

1. **Always review generated migrations** before applying
2. **Test migrations** on development database first
3. **Backup production database** before running migrations
4. **Use descriptive messages** for migration revisions
5. **Never edit applied migrations** - create new ones instead

---

## Application Architecture

### Project Structure

```
pywhatsapp/
├── app/
│   ├── api/
│   │   ├── deps.py              # Authentication dependencies
│   │   └── v1/
│   │       ├── router.py         # API router aggregator
│   │       ├── auth.py           # JWT authentication endpoints
│   │       ├── messages.py       # Message endpoints
│   │       ├── contacts.py       # Contact management
│   │       ├── campaigns.py      # Campaign management
│   │       ├── groups.py         # Group management
│   │       ├── templates.py      # Template management
│   │       └── webhooks.py       # Webhook endpoints
│   ├── core/
│   │   ├── config.py             # Configuration management
│   │   ├── security.py           # Password hashing, auth
│   │   └── jwt_auth.py           # JWT utilities
│   ├── db/
│   │   ├── base.py               # SQLAlchemy Base
│   │   └── session.py            # Database session management
│   ├── models/
│   │   ├── base.py               # Base model with common fields
│   │   ├── user.py               # Admin user model
│   │   ├── message.py            # Message & MessageTemplate
│   │   ├── contact.py            # Contact model
│   │   ├── group.py              # Group model
│   │   ├── campaign.py           # Campaign model
│   │   ├── webhook.py            # Webhook logs & reactions
│   │   └── template.py           # Message templates
│   ├── schemas/
│   │   ├── message.py            # Pydantic schemas for messages
│   │   ├── contact.py            # Contact schemas
│   │   ├── campaign.py           # Campaign schemas
│   │   ├── group.py              # Group schemas
│   │   └── template.py           # Template schemas
│   ├── services/
│   │   ├── message_service.py    # Message business logic
│   │   ├── template_service.py   # Template management
│   │   └── whatsapp_handlers.py  # WhatsApp webhook handlers
│   ├── ws/
│   │   └── manager.py            # WebSocket connection manager
│   └── main.py                   # FastAPI application entry point
├── alembic/
│   ├── versions/                 # Migration files
│   └── env.py                    # Alembic configuration
├── scripts/
│   ├── setup_database_.py        # Database setup utilities
│   ├── create_admin.py           # Create admin user script
│   └── migrate_templates.py      # Template migration script
├── templates/                    # Jinja2 HTML templates
│   ├── login.html
│   ├── chat.html
│   ├── dashboard.html
│   └── logs.html
├── docs/                         # Documentation
├── auto_setup.py                 # Auto-setup script
├── auto_setup_prod.py            # Production setup script
├── requirements.txt              # Python dependencies
├── requirements_prod.txt         # Production dependencies
└── alembic.ini                   # Alembic configuration

```

### Core Components

#### 1. Authentication System

**Dual Authentication:**
- **Session-based:** For HTML UI (login, chat, dashboard)
- **JWT-based:** For API access (mobile apps, external integrations)

**Files:**
- `app/core/security.py` - Password hashing, user authentication
- `app/core/jwt_auth.py` - JWT token creation and validation
- `app/api/deps.py` - Authentication dependencies for routes

#### 2. Multi-Tenant Support

- Each request is scoped to a tenant via `X-Tenant-Id` header
- Default tenant ID from environment variable
- Session stores tenant ID for UI users
- JWT tokens contain tenant information

**Implementation:**
- `app/api/deps.py:get_tenant_id_flexible()` - Tenant ID extraction
- All models include `tenant_id` field
- Queries automatically filtered by tenant

#### 3. Database Layer

**SQLAlchemy Models:**
- All models extend `BaseModel` (UUID primary key, timestamps, tenant_id)
- Relationship management with foreign keys
- Indexes for query optimization

**Key Models:**
- `AdminUser` - Application users
- `Message` - WhatsApp messages (incoming/outgoing)
- `Contact` - Contact information
- `Group` - WhatsApp groups
- `Campaign` - Bulk messaging campaigns
- `MessageTemplate` - Reusable message templates
- `WebhookLog` - Webhook event logs

#### 4. WhatsApp Integration

**PyWA Library:**
- Official WhatsApp Business API wrapper
- Handles webhooks automatically
- Message sending and receiving

**Handlers:**
- `app/services/whatsapp_handlers.py` - Webhook event processors
- Incoming messages saved to database
- Real-time WebSocket broadcasting

#### 5. Real-Time Communication

**WebSocket Manager:**
- `app/ws/manager.py` - Connection pool management
- Tenant-isolated broadcasting
- Automatic connection cleanup

**Events:**
- `message_incoming` - New message received
- `message_outgoing` - Message sent
- Connection tracking per tenant

#### 6. API Structure

**RESTful Endpoints:**
- `/api/v1/messages` - Message operations
- `/api/v1/contacts` - Contact management
- `/api/v1/campaigns` - Campaign management
- `/api/v1/groups` - Group operations
- `/api/v1/templates` - Template CRUD
- `/api/v1/webhooks` - Webhook logs

**Response Format:**
```json
{
  "data": {},
  "message": "Success",
  "status": "ok"
}
```

---

## Development Rules & Best Practices

### Code Style

1. **Type Hints:** Always use type hints for function parameters and returns
2. **Docstrings:** Document all public functions and classes
3. **Logging:** Use structured logging with appropriate levels
4. **Error Handling:** Always catch specific exceptions

### Database Operations

1. **Use Dependencies:** Always use `Depends(get_db)` for database access
2. **Transactions:** Service layer handles commits/rollbacks
3. **Queries:** Filter by tenant_id for all multi-tenant queries
4. **Indexes:** Add indexes for frequently queried columns

### API Development

1. **Versioning:** All API routes under `/api/v1/`
2. **Validation:** Use Pydantic schemas for request/response
3. **Authentication:** Use appropriate auth dependency
4. **CORS:** Configured in `main.py` - update allowed origins as needed

### Security

1. **Never commit secrets** - Use environment variables
2. **Password hashing** - Use bcrypt via `passlib`
3. **JWT validation** - Always validate tokens
4. **SQL injection** - Use SQLAlchemy ORM, never raw SQL with user input

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/test_messages.py
```

### Multi-Tenant Guidelines

1. **Always filter by tenant_id** in queries
2. **Extract tenant from request** using `get_tenant_id_flexible()`
3. **Include tenant_id** in all model creates
4. **WebSocket rooms** scoped by tenant_id

---

## Common Tasks

### Create Admin User

```bash
python scripts/create_admin.py
```

### Reset Database

```bash
python auto_setup.py  # Drops and recreates all tables
```

### View Logs

```bash
# Development logs
tail -f logs/whatspy.log

# Production logs
journalctl -u whatspy -f
```

### Backup Database

```bash
pg_dump -U postgres whatspy_db > backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
psql -U postgres whatspy_db < backup_20240101.sql
```

---

## API Examples

### Authentication

**Get JWT Token:**
```bash
curl -X POST http://localhost:8002/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin@123"
  }'
```

**Use JWT Token:**
```bash
curl http://localhost:8002/api/v1/messages \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Send Message

```bash
curl -X POST http://localhost:8002/api/send/text \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: YOUR_TENANT_ID" \
  -d '{
    "to": "1234567890",
    "text": "Hello from PyWhatsApp!"
  }'
```

### Get Conversations

```bash
curl http://localhost:8002/api/conversations \
  -H "X-Tenant-Id: YOUR_TENANT_ID"
```

---

## Troubleshooting

### Database Connection Issues

1. Check PostgreSQL is running:
   ```bash
   # Windows
   sc query postgresql

   # Linux
   sudo systemctl status postgresql
   ```

2. Verify credentials in `.env`
3. Check database exists:
   ```bash
   psql -U postgres -l
   ```

### WhatsApp Not Connecting

1. Verify credentials in `.env`
2. Check webhook URL is accessible
3. Verify webhook in Meta Developer Console
4. Check logs for errors

### Migration Errors

1. Check current migration state:
   ```bash
   alembic current
   ```

2. If stuck, check migration table:
   ```sql
   SELECT * FROM alembic_version;
   ```

3. Force to specific version:
   ```bash
   alembic stamp head
   ```

---

## Production Deployment

### Using Docker (Recommended)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements_prod.txt .
RUN pip install --no-cache-dir -r requirements_prod.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
```

### Using Systemd

```ini
[Unit]
Description=PyWhatsApp Service
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/pywhatsapp
Environment="PATH=/opt/pywhatsapp/venv/bin"
ExecStart=/opt/pywhatsapp/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8002
Restart=always

[Install]
WantedBy=multi-user.target
```

### Environment Variables for Production

```env
# Use strong secrets
SESSION_SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)

# Use production database
DATABASE_URL=postgresql://user:pass@prod-db:5432/whatspy_prod

# Disable debug mode
LOG_LEVEL=WARNING
```

---

## License & Contact

For questions or issues, please create an issue in the repository.

**Last Updated:** 2025-11-21
