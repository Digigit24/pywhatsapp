# Tenant Configuration System - Quick Summary

## 🎯 What's New

A complete multi-tenant configuration system that allows each tenant to store and manage their own WhatsApp Business API credentials in the database, with automatic fallback to `.env` file.

---

## 📁 Files Created

### Models & Schemas
1. **`app/models/tenant_config.py`** - Database model for tenant configurations
2. **`app/schemas/tenant_config.py`** - Pydantic schemas for API requests/responses

### API Endpoints
3. **`app/api/v1/tenant_config.py`** - All tenant config API endpoints
   - OAuth onboarding
   - CRUD operations
   - Activation/deactivation

### Configuration System
4. **`app/core/config_loader.py`** - Dynamic config loader (DB-first, .env fallback)

### Database Migrations
5. **`migrations/create_tenant_configs_table.sql`** - Create table script
6. **`migrations/rollback_tenant_configs_table.sql`** - Rollback script

### Documentation
7. **`docs/TENANT_CONFIG_GUIDE.md`** - Comprehensive implementation guide

### Modified Files
8. **`app/api/v1/router.py`** - Added tenant_config router
9. **`app/core/config.py`** - Added FB_APP_ID and FB_APP_SECRET exports

---

## 🚀 Quick Start

### 1. Database Setup
```bash
psql -h your-host -U your-user -d whatspy_db -f migrations/create_tenant_configs_table.sql
```

### 2. API Endpoints (All under `/api/v1/tenant`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/onboard/whatsapp-client` | OAuth onboarding |
| GET | `/config` | Get config (masked) |
| GET | `/config/full` | Get config (unmasked) |
| POST | `/config` | Create config |
| PUT | `/config` | Update config |
| DELETE | `/config` | Delete config |
| POST | `/config/deactivate` | Deactivate config |
| POST | `/config/activate` | Activate config |

**Admin Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/configs/all` | Get all tenant configs |
| GET | `/admin/configs/stats` | Get config statistics |
| DELETE | `/admin/configs/delete-all` | ⚠️ Delete ALL configs |
| DELETE | `/admin/configs/delete-tenant/{id}` | Delete specific tenant config |

### 3. Use Config Loader in Your Code

```python
from app.core.config_loader import ConfigLoader

# Initialize
loader = ConfigLoader(db, tenant_id)

# Get values (DB first, then .env)
phone_id = loader.get_phone_id()
token = loader.get_access_token()
waba_id = loader.get_waba_id()

# Or get all at once
config = loader.get_all_config()
```

---

## 🔄 Configuration Priority

```
1. Database (tenant_configs table) ✅ Highest Priority
   ↓ (if not found or inactive)
2. .env file ✅ Fallback
```

---

## 📊 Database Schema

### tenant_configs Table

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| tenant_id | VARCHAR(100) | Tenant identifier |
| user_id | VARCHAR(255) | User who created config |
| waba_id | VARCHAR(255) | WhatsApp Business Account ID |
| phone_number_id | VARCHAR(255) | Phone Number ID |
| access_token | TEXT | Long-lived access token |
| fb_app_id | VARCHAR(255) | Facebook App ID |
| fb_app_secret | VARCHAR(255) | Facebook App Secret |
| callback_url | VARCHAR(500) | Webhook callback URL |
| redirect_url | VARCHAR(500) | OAuth redirect URL |
| verify_token | VARCHAR(255) | Webhook verify token |
| token_expires_at | TIMESTAMP | Token expiration |
| refresh_token | TEXT | Refresh token |
| is_active | BOOLEAN | Active status |
| onboarding_completed | BOOLEAN | Onboarding status |
| onboarded_at | TIMESTAMP | Onboarding completion time |
| last_verified_at | TIMESTAMP | Last verification time |
| created_at | TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | Last update time |

---

## 🔐 OAuth Onboarding Flow

1. **Frontend:** Redirect to Meta OAuth URL
   ```
   https://www.facebook.com/v19.0/dialog/oauth
   ```

2. **User:** Authorizes app

3. **Meta:** Redirects back with `code`

4. **Frontend:** Calls onboarding endpoint
   ```bash
   POST /api/v1/tenant/onboard/whatsapp-client
   {
     "code": "AUTH_CODE",
     "waba_id": "123456789",
     "phone_number_id": "987654321",
     "redirect_uri": "https://domain.com/callback"
   }
   ```

5. **Backend:** Exchanges code → stores token → completes onboarding ✅

---

## 💻 Code Examples

### OAuth Onboarding (React)
```jsx
const startOAuth = () => {
  const params = new URLSearchParams({
    client_id: process.env.REACT_APP_FB_APP_ID,
    redirect_uri: `${window.location.origin}/callback`,
    scope: 'whatsapp_business_messaging,whatsapp_business_management',
    response_type: 'code'
  });
  window.location.href = `https://www.facebook.com/v19.0/dialog/oauth?${params}`;
};
```

### Update Config via API
```bash
curl -X PUT http://localhost:8002/api/v1/tenant/config \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number_id": "new-phone-id",
    "callback_url": "https://new-url.com/webhook"
  }'
```

### Use Config in Python
```python
from app.core.config_loader import get_whatsapp_config

config = get_whatsapp_config(db, tenant_id)
wa_client = WhatsAppClient(
    phone_id=config["phone_id"],
    token=config["access_token"]
)
```

---

## 🔒 Security Features

- ✅ Access tokens masked in API responses
- ✅ JWT authentication required for all endpoints
- ✅ Tenant isolation (users can only access their own config)
- ✅ HTTPS required for OAuth
- ✅ Automatic updated_at timestamp
- ✅ Database indexes for performance

---

## 📝 Environment Variables Required

Add to your `.env` file:

```env
# Facebook App Credentials (for OAuth)
FB_APP_ID=your_facebook_app_id
FB_APP_SECRET=your_facebook_app_secret

# Default WhatsApp settings (fallback)
WHATSAPP_PHONE_ID=default_phone_id
WHATSAPP_TOKEN=default_access_token
VERIFY_TOKEN=default_verify_token
CALLBACK_URL=https://yourdomain.com/webhooks
```

---

## 🧪 Testing Checklist

- [ ] Run SQL migration script
- [ ] Verify table created: `SELECT * FROM tenant_configs;`
- [ ] Test OAuth flow with test tenant
- [ ] Test manual config creation via API
- [ ] Test config update endpoint
- [ ] Verify config loader returns DB values
- [ ] Verify .env fallback works when no DB config
- [ ] Test activate/deactivate endpoints
- [ ] Check masked vs full config endpoints
- [ ] Test with multiple tenants

---

## 📚 Full Documentation

For detailed implementation guide, see: **`docs/TENANT_CONFIG_GUIDE.md`**

---

## 🆘 Quick Troubleshooting

### Config not found?
```sql
-- Check if config exists
SELECT * FROM tenant_configs WHERE tenant_id = 'your-tenant-id';
```

### OAuth failing?
- Verify FB_APP_ID and FB_APP_SECRET in .env
- Check redirect_uri matches exactly
- Ensure code hasn't been used already (codes expire quickly)

### Config not being used?
```python
# Check if tenant has active config
loader = ConfigLoader(db, tenant_id)
print(loader.has_tenant_config())  # Should be True
```

---

**Created:** 2025-12-11
**Version:** 1.0.0
