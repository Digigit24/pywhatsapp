# WhatsApp Template Setup Guide

## Issue: Templates Not Creating in Meta API

If you're seeing this error in your logs:
```
ValueError: When initializing WhatsApp without `business_account_id`, `waba_id` must be provided.
```

This means your WhatsApp client needs the **WhatsApp Business Account ID (WABA ID)** to create templates.

## Solution: Add Your WhatsApp Business Account ID

### Step 1: Get Your WhatsApp Business Account ID

#### Option A: From Meta Business Manager
1. Go to [Meta Business Manager](https://business.facebook.com/)
2. Navigate to **Business Settings** → **Accounts** → **WhatsApp Accounts**
3. Click on your WhatsApp Business Account
4. Copy the **WhatsApp Business Account ID** (looks like: `123456789012345`)

#### Option B: From Meta Developers Console
1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Open your app
3. Go to **WhatsApp** → **Getting Started** or **API Setup**
4. Find the **WhatsApp Business Account ID** field
5. Copy the ID (numeric ID, e.g., `123456789012345`)

#### Option C: Via API Call
Make a GET request to:
```bash
curl -X GET "https://graph.facebook.com/v18.0/me/business_managers" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Or check the phone number details:
```bash
curl -X GET "https://graph.facebook.com/v18.0/YOUR_PHONE_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

The response will include your `whatsapp_business_account_id`.

### Step 2: Add to Your `.env` File

Add one of these lines to your `.env` file:

```env
# Option 1 (recommended):
WHATSAPP_BUSINESS_ACCOUNT_ID=123456789012345

# Option 2 (alternative):
WABA_ID=123456789012345
```

### Step 3: Restart Your Application

After adding the environment variable, restart your application:
```bash
# If using Docker
docker-compose restart

# If using uvicorn directly
# Stop the server (Ctrl+C) and restart
python -m uvicorn app.main:app --reload
```

### Step 4: Verify Configuration

When your app starts, check the logs for:
```
✅ WhatsApp Business Account ID configured: 123456789012345
✅ WhatsApp client initialized
```

If you see this warning instead:
```
⚠️  BUSINESS_ACCOUNT_ID not set - template creation will fail!
```

Then the environment variable wasn't loaded correctly. Double-check your `.env` file.

## Testing Template Creation

Once configured, try creating a template again:

```bash
curl -X POST "http://localhost:8100/api/templates/" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: your-tenant-id" \
  -d '{
    "name": "test_template",
    "language": "en_US",
    "category": "UTILITY",
    "components": [
      {
        "type": "BODY",
        "text": "Hello, this is a test template."
      }
    ]
  }'
```

Check `logs/template_api.log` for detailed execution logs.

## What Changed

1. **`app/core/config.py`**: Added `BUSINESS_ACCOUNT_ID` configuration
2. **`app/main.py`**: Updated WhatsApp client initialization to include `business_account_id`
3. The client now properly initializes with the WABA ID needed for template operations

## Troubleshooting

### Error: "Invalid WhatsApp Business Account ID"
- Verify the ID is correct in Meta Business Manager
- Ensure you're using the correct access token with proper permissions

### Error: "Access token does not have permission"
- Your access token needs `whatsapp_business_management` permission
- Regenerate the token with proper scopes in Meta for Developers

### Templates Still Not Creating
1. Check `logs/template_api.log` for detailed error messages
2. Verify your access token has not expired
3. Ensure your WhatsApp Business Account is verified and approved
4. Check that you have template creation permissions in your Meta Business account

## Additional Resources

- [PyWa Documentation](https://pywa.readthedocs.io/)
- [Meta WhatsApp Business Platform](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Template Message Format](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-message-templates)

## Support

If you're still having issues:
1. Check the full log output in `logs/template_api.log`
2. Verify all environment variables are set correctly
3. Ensure your Meta app has the necessary permissions
