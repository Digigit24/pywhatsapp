# Tenant Configuration System - Complete Guide

## Overview

The Tenant Configuration System allows each tenant to have their own WhatsApp Business API credentials stored in the database, which override the global `.env` settings. This enables true multi-tenancy where each tenant can:

- Use their own WhatsApp Business Account
- Complete OAuth onboarding independently
- Manage their own credentials via API
- Update settings through frontend forms

## Table of Contents

1. [Database Setup](#database-setup)
2. [Configuration Priority](#configuration-priority)
3. [OAuth Onboarding Flow](#oauth-onboarding-flow)
4. [API Endpoints](#api-endpoints)
5. [Using the Config Loader](#using-the-config-loader)
6. [Frontend Integration](#frontend-integration)
7. [Security Considerations](#security-considerations)

---

## Database Setup

### Step 1: Run the Migration SQL

Connect to your PostgreSQL database and run the migration script:

```bash
psql -h your-host -U your-user -d whatspy_db -f migrations/create_tenant_configs_table.sql
```

Or using pgAdmin/any SQL client, execute the contents of:
```
migrations/create_tenant_configs_table.sql
```

### Step 2: Verify Table Creation

```sql
-- Check if table exists
SELECT * FROM tenant_configs LIMIT 1;

-- View table structure
\d tenant_configs
```

### Rollback (if needed)

To remove the tenant_configs table:

```bash
psql -h your-host -U your-user -d whatspy_db -f migrations/rollback_tenant_configs_table.sql
```

---

## Configuration Priority

The system follows this priority order:

1. **Database Configuration (Highest Priority)**
   - Tenant-specific settings from `tenant_configs` table
   - Only if `is_active = TRUE`

2. **Environment Variables (Fallback)**
   - Global settings from `.env` file
   - Used when no tenant config exists

### Example

If tenant has `phone_number_id` in database:
```
Database: 123456789     ✅ Used
.env: 987654321         ❌ Ignored
```

If tenant has NO database config:
```
Database: (none)
.env: 987654321         ✅ Used (fallback)
```

---

## OAuth Onboarding Flow

### Overview

The OAuth flow allows tenants to connect their WhatsApp Business Account by authorizing your app through Meta's OAuth system.

### Step-by-Step Process

#### 1. Frontend: Initiate OAuth

Redirect user to Meta's OAuth URL:

```javascript
const FACEBOOK_OAUTH_URL = `https://www.facebook.com/v19.0/dialog/oauth`;
const params = new URLSearchParams({
  client_id: 'YOUR_FB_APP_ID',
  redirect_uri: 'https://yourdomain.com/oauth/callback',
  scope: 'whatsapp_business_messaging,whatsapp_business_management',
  response_type: 'code',
  state: 'random_state_token'  // CSRF protection
});

window.location.href = `${FACEBOOK_OAUTH_URL}?${params.toString()}`;
```

#### 2. User Authorizes

User logs into Facebook and authorizes your app to access their WhatsApp Business Account.

#### 3. Meta Redirects Back

Meta redirects to your `redirect_uri` with:
```
https://yourdomain.com/oauth/callback?code=AUTH_CODE&state=random_state_token
```

#### 4. Frontend: Extract Data

On the callback page, extract the authorization code and collect additional data:

```javascript
// Parse URL parameters
const urlParams = new URLSearchParams(window.location.search);
const code = urlParams.get('code');

// User needs to provide these (from Meta Business Manager)
const waba_id = document.getElementById('waba_id').value;
const phone_number_id = document.getElementById('phone_id').value;
const redirect_uri = 'https://yourdomain.com/oauth/callback';
```

#### 5. Frontend: Call Onboarding API

```javascript
const response = await fetch('/api/v1/tenant/onboard/whatsapp-client', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${jwtToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    code: code,
    waba_id: waba_id,
    phone_number_id: phone_number_id,
    redirect_uri: redirect_uri
  })
});

const result = await response.json();
console.log('Onboarding complete:', result);
```

#### 6. Backend: Exchange Code & Store

The API automatically:
- Exchanges code for access_token
- Stores credentials in database
- Marks onboarding as complete

---

## API Endpoints

### Base URL
```
/api/v1/tenant
```

All endpoints require JWT authentication via `Authorization: Bearer <token>` header.

---

### 1. OAuth Onboarding

**Endpoint:** `POST /onboard/whatsapp-client`

**Description:** Complete WhatsApp Business API onboarding via OAuth code exchange.

**Request:**
```json
{
  "code": "AUTH_CODE_FROM_META",
  "waba_id": "123456789",
  "phone_number_id": "987654321",
  "redirect_uri": "https://yourdomain.com/oauth/callback"
}
```

**Response:**
```json
{
  "success": true,
  "message": "WhatsApp Business API onboarding completed successfully",
  "tenant_id": "tenant-uuid",
  "config_id": 1,
  "waba_id": "123456789",
  "phone_number_id": "987654321"
}
```

**Errors:**
- `400`: Invalid code or missing parameters
- `502`: Failed to communicate with Meta
- `500`: Database error

---

### 2. Get Configuration (Masked)

**Endpoint:** `GET /config`

**Description:** Get tenant configuration with sensitive fields masked.

**Response:**
```json
{
  "id": 1,
  "tenant_id": "tenant-uuid",
  "user_id": "user-123",
  "waba_id": "123456789",
  "phone_number_id": "987654321",
  "access_token": "***abc123",  // Last 4 chars only
  "fb_app_id": "123456789",
  "fb_app_secret": "***xyz789",  // Masked
  "callback_url": "https://domain.com/webhook",
  "redirect_url": "https://domain.com/oauth",
  "verify_token": "verify123",
  "is_active": true,
  "onboarding_completed": true,
  "onboarded_at": "2025-12-11T10:30:00Z",
  "created_at": "2025-12-11T10:30:00Z",
  "updated_at": "2025-12-11T10:30:00Z"
}
```

---

### 3. Get Full Configuration (Admin)

**Endpoint:** `GET /config/full`

**Description:** Get full configuration including unmasked sensitive data.

⚠️ **Admin only** - Returns real tokens and secrets.

**Response:**
```json
{
  "id": 1,
  "tenant_id": "tenant-uuid",
  "access_token": "EAABsbCS...full_token",  // Unmasked
  "fb_app_secret": "abc123def456...full_secret",  // Unmasked
  "refresh_token": "refresh_token_value",
  // ... other fields
}
```

---

### 4. Create Configuration

**Endpoint:** `POST /config`

**Description:** Manually create tenant configuration (without OAuth).

**Request:**
```json
{
  "user_id": "user-123",
  "waba_id": "123456789",
  "phone_number_id": "987654321",
  "fb_app_id": "app-id",
  "callback_url": "https://domain.com/webhook",
  "redirect_url": "https://domain.com/oauth",
  "verify_token": "verify123"
}
```

**Response:** Same as GET /config (masked data)

---

### 5. Update Configuration

**Endpoint:** `PUT /config`

**Description:** Update tenant configuration. Only updates provided fields.

**Request:**
```json
{
  "phone_number_id": "new-phone-id",
  "callback_url": "https://new-domain.com/webhook",
  "is_active": true
}
```

**Response:** Updated configuration (masked)

---

### 6. Delete Configuration

**Endpoint:** `DELETE /config`

**Description:** Permanently delete tenant configuration.

⚠️ **Warning:** This removes all stored credentials.

**Response:** `204 No Content`

---

### 7. Deactivate Configuration

**Endpoint:** `POST /config/deactivate`

**Description:** Deactivate configuration without deleting (preserves data).

**Response:** Updated configuration with `is_active: false`

---

### 8. Activate Configuration

**Endpoint:** `POST /config/activate`

**Description:** Reactivate a deactivated configuration.

**Response:** Updated configuration with `is_active: true`

---

## Using the Config Loader

### In Your Code

The `ConfigLoader` class provides database-first configuration loading:

```python
from app.core.config_loader import ConfigLoader
from app.db.session import get_db

# Initialize loader
db = next(get_db())
loader = ConfigLoader(db, tenant_id="your-tenant-id")

# Get individual values
phone_id = loader.get_phone_id()          # DB first, then .env
access_token = loader.get_access_token()  # DB first, then .env
waba_id = loader.get_waba_id()            # DB only

# Get all config at once
config = loader.get_all_config()
print(config)
# {
#   "phone_id": "...",
#   "access_token": "...",
#   "has_tenant_config": True,
#   "onboarding_completed": True,
#   ...
# }

# Check status
if loader.has_tenant_config():
    print("Using database config")
else:
    print("Falling back to .env")
```

### Convenience Functions

```python
from app.core.config_loader import (
    get_whatsapp_config,
    get_phone_id_for_tenant,
    get_access_token_for_tenant,
    is_tenant_onboarded
)

# Quick config fetch
config = get_whatsapp_config(db, tenant_id)

# Single value fetches
phone_id = get_phone_id_for_tenant(db, tenant_id)
token = get_access_token_for_tenant(db, tenant_id)

# Check onboarding status
if is_tenant_onboarded(db, tenant_id):
    print("Tenant is ready to use WhatsApp API")
```

### In API Endpoints

```python
from fastapi import Depends
from app.api.deps import get_current_tenant_id
from app.core.config_loader import ConfigLoader

@router.post("/send-message")
async def send_message(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    # Load tenant-specific config
    loader = ConfigLoader(db, tenant_id)

    # Initialize WhatsApp client with tenant config
    wa_client = WhatsAppClient(
        phone_id=loader.get_phone_id(),
        token=loader.get_access_token()
    )

    # Send message...
```

---

## Frontend Integration

### React Example: OAuth Flow

```jsx
import React, { useState } from 'react';

function WhatsAppOnboarding() {
  const [loading, setLoading] = useState(false);

  // Step 1: Redirect to Meta OAuth
  const startOAuth = () => {
    const params = new URLSearchParams({
      client_id: process.env.REACT_APP_FB_APP_ID,
      redirect_uri: `${window.location.origin}/oauth/callback`,
      scope: 'whatsapp_business_messaging,whatsapp_business_management',
      response_type: 'code',
      state: Math.random().toString(36)
    });

    window.location.href = `https://www.facebook.com/v19.0/dialog/oauth?${params}`;
  };

  return (
    <button onClick={startOAuth}>
      Connect WhatsApp Business
    </button>
  );
}

// OAuth Callback Page
function OAuthCallback() {
  const [wabaId, setWabaId] = useState('');
  const [phoneId, setPhoneId] = useState('');

  const completeOnboarding = async () => {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');

    const response = await fetch('/api/v1/tenant/onboard/whatsapp-client', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('jwt')}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        code: code,
        waba_id: wabaId,
        phone_number_id: phoneId,
        redirect_uri: `${window.location.origin}/oauth/callback`
      })
    });

    const result = await response.json();

    if (result.success) {
      alert('Onboarding complete!');
      window.location.href = '/dashboard';
    }
  };

  return (
    <div>
      <h2>Complete Setup</h2>
      <input
        placeholder="WhatsApp Business Account ID"
        value={wabaId}
        onChange={(e) => setWabaId(e.target.value)}
      />
      <input
        placeholder="Phone Number ID"
        value={phoneId}
        onChange={(e) => setPhoneId(e.target.value)}
      />
      <button onClick={completeOnboarding}>
        Complete Onboarding
      </button>
    </div>
  );
}
```

### React Example: Config Management

```jsx
function ConfigSettings() {
  const [config, setConfig] = useState(null);
  const [formData, setFormData] = useState({});

  // Load current config
  useEffect(() => {
    fetch('/api/v1/tenant/config', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('jwt')}`
      }
    })
      .then(res => res.json())
      .then(data => {
        setConfig(data);
        setFormData(data);
      });
  }, []);

  // Update config
  const handleSave = async () => {
    const response = await fetch('/api/v1/tenant/config', {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('jwt')}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(formData)
    });

    const result = await response.json();
    setConfig(result);
    alert('Configuration updated!');
  };

  return (
    <form>
      <h2>WhatsApp Configuration</h2>

      <label>Phone Number ID</label>
      <input
        value={formData.phone_number_id || ''}
        onChange={(e) => setFormData({...formData, phone_number_id: e.target.value})}
      />

      <label>Callback URL</label>
      <input
        value={formData.callback_url || ''}
        onChange={(e) => setFormData({...formData, callback_url: e.target.value})}
      />

      <label>Verify Token</label>
      <input
        value={formData.verify_token || ''}
        onChange={(e) => setFormData({...formData, verify_token: e.target.value})}
      />

      <button type="button" onClick={handleSave}>
        Save Configuration
      </button>
    </form>
  );
}
```

---

## Security Considerations

### 1. Access Token Storage

✅ **Do:**
- Store access tokens encrypted in database
- Use HTTPS for all API calls
- Rotate tokens periodically

❌ **Don't:**
- Log access tokens
- Expose full tokens in API responses (use masking)
- Store tokens in frontend localStorage

### 2. OAuth Security

- Always validate `state` parameter (CSRF protection)
- Use HTTPS redirect URIs only
- Whitelist redirect URIs in Meta App Settings

### 3. API Access Control

```python
# Always require authentication
@router.get("/config")
async def get_config(
    current_user: dict = Depends(get_current_user),  # ✅ Required
    tenant_id: str = Depends(get_current_tenant_id)  # ✅ Required
):
    # User can only access their own tenant's config
    pass
```

### 4. Database Security

- Use strong passwords for database access
- Enable SSL for PostgreSQL connections
- Regular backups of tenant_configs table
- Consider encrypting sensitive columns

### 5. Frontend Security

```javascript
// ✅ Do: Store JWT securely
const token = localStorage.getItem('jwt');

// ❌ Don't: Expose sensitive config values
console.log('Access Token:', config.access_token);  // Never do this!

// ✅ Do: Validate user input
if (!isValidPhoneId(phoneId)) {
  alert('Invalid Phone ID format');
  return;
}
```

---

## Troubleshooting

### Issue: "Tenant configuration not found"

**Solution:**
1. Check if tenant has completed onboarding
2. Verify tenant_id matches JWT token
3. Check database:
   ```sql
   SELECT * FROM tenant_configs WHERE tenant_id = 'your-tenant-id';
   ```

### Issue: "Failed to exchange code with Meta"

**Possible causes:**
- Invalid authorization code (expired or already used)
- Wrong `client_id` or `client_secret` in .env
- Mismatched `redirect_uri`
- Network/firewall issues

**Solution:**
- Restart OAuth flow from beginning
- Verify FB_APP_ID and FB_APP_SECRET in .env
- Check redirect_uri matches exactly

### Issue: Config not being used

**Solution:**
1. Check `is_active` flag:
   ```sql
   SELECT is_active FROM tenant_configs WHERE tenant_id = 'your-tenant-id';
   ```

2. Verify ConfigLoader usage:
   ```python
   loader = ConfigLoader(db, tenant_id)
   print(loader.has_tenant_config())  # Should be True
   ```

3. Clear any caching if implemented

---

## Next Steps

1. **Run the migration** to create the table
2. **Test OAuth flow** with a test tenant
3. **Integrate ConfigLoader** in your WhatsApp message sending code
4. **Build frontend forms** for config management
5. **Set up monitoring** for token expiration

For questions or issues, refer to the main CLAUDE.md documentation.

---

**Last Updated:** 2025-12-11
