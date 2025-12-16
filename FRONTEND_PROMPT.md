# 🚀 Frontend Implementation Prompt - WhatsApp Embedded Signup

Copy this entire prompt and share it with your frontend team.

---

## Task: Implement WhatsApp Embedded Signup Flow

### Objective
Create a React component that handles WhatsApp Business API embedded signup using Facebook OAuth and postMessage events.

---

## Requirements

### 1. Facebook SDK Integration

Initialize Facebook SDK with your app credentials:

```javascript
window.fbAsyncInit = function() {
  window.FB.init({
    appId: 'YOUR_FB_APP_ID',
    cookie: true,
    xfbml: true,
    version: 'v19.0'
  });
};
```

### 2. postMessage Event Listener

Implement a `useEffect` hook that listens for WhatsApp signup completion:

```javascript
useEffect(() => {
  const handleMessage = (event) => {
    // IMPORTANT: Security check - only accept messages from Facebook
    if (event.origin !== "https://www.facebook.com") {
      return;
    }

    try {
      const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;

      // Check for WhatsApp signup completion
      if (data.type === 'WA_EMBEDDED_SIGNUP' && data.event === 'FINISH') {
        const { waba_id, phone_number_id } = data.data;

        // Store these values in state
        setWabaId(waba_id);
        setPhoneNumberId(phone_number_id);
      }
    } catch (err) {
      console.error('Error parsing postMessage:', err);
    }
  };

  window.addEventListener('message', handleMessage);
  return () => window.removeEventListener('message', handleMessage);
}, []);
```

### 3. Facebook Login Callback

Trigger Facebook login and capture the OAuth code:

```javascript
const handleFacebookLogin = () => {
  window.FB.login(
    (response) => {
      if (response.authResponse && response.authResponse.code) {
        // Store OAuth code
        setOauthCode(response.authResponse.code);
      }
    },
    {
      config_id: 'YOUR_CONFIG_ID', // From Meta App settings
      response_type: 'code',
      override_default_response_type: true,
      extras: {
        setup: {},
        featureType: '',
        sessionInfoVersion: 2
      }
    }
  );
};
```

### 4. Backend API Integration

When you have all three values (`code`, `waba_id`, `phone_number_id`), call the backend:

**API Endpoint:** `POST /api/v1/tenant/onboard/whatsapp-client`

**Request Payload:**
```javascript
{
  code: oauthCode,              // From FB.login callback
  waba_id: wabaId,              // From postMessage event
  phone_number_id: phoneNumberId, // From postMessage event
  redirect_uri: window.location.href
}
```

**Headers:**
```javascript
{
  'Authorization': `Bearer ${jwtToken}`,
  'Content-Type': 'application/json'
}
```

**Expected Response (Success - 200 OK):**
```javascript
{
  "success": true,
  "message": "WhatsApp Business API onboarding completed successfully",
  "tenant_id": "your-tenant-id",
  "config_id": 1,
  "waba_id": "123456789",
  "phone_number_id": "987654321"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid code or missing parameters
- `401 Unauthorized` - Missing/invalid JWT token
- `502 Bad Gateway` - Failed to communicate with Meta
- `500 Internal Server Error` - Backend error

### 5. Auto-Trigger API Call

Use a `useEffect` to automatically call the backend when all data is available:

```javascript
useEffect(() => {
  if (oauthCode && wabaId && phoneNumberId && !loading && !success) {
    completeOnboarding();
  }
}, [oauthCode, wabaId, phoneNumberId]);
```

---

## Complete Implementation Example

See the full working example in: **`docs/FRONTEND_WHATSAPP_SIGNUP_IMPLEMENTATION.md`**

The documentation includes:
- Complete React component with state management
- Error handling and loading states
- Progress indicators
- Success/error messages
- Automatic redirect on success

---

## State Management

Your component should maintain these states:

```javascript
const [oauthCode, setOauthCode] = useState(null);
const [wabaId, setWabaId] = useState(null);
const [phoneNumberId, setPhoneNumberId] = useState(null);
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);
const [success, setSuccess] = useState(false);
```

---

## Flow Diagram

```
User clicks button
    ↓
FB.login() called
    ↓
User authorizes in popup
    ↓
OAuth code received ✅
    ↓
postMessage event fired
    ↓
WABA ID & Phone ID received ✅
    ↓
Auto-trigger: Call backend API
    ↓
Backend exchanges code for token
    ↓
Configuration saved to database
    ↓
Success! Redirect to dashboard
```

---

## Testing Checklist

- [ ] Facebook SDK loads without errors
- [ ] Button triggers FB.login popup
- [ ] OAuth code is captured from callback
- [ ] postMessage listener receives WABA and Phone IDs
- [ ] API call is triggered with all three values
- [ ] Loading state shows during API call
- [ ] Success message displays on completion
- [ ] Error message displays on failure
- [ ] Automatic redirect to dashboard works

---

## Environment Variables Needed

```env
REACT_APP_API_URL=http://localhost:8002
REACT_APP_FB_APP_ID=your_facebook_app_id
REACT_APP_FB_CONFIG_ID=your_config_id_from_meta
```

---

## Questions?

Refer to the complete documentation:
- **Full Implementation Guide:** `docs/FRONTEND_WHATSAPP_SIGNUP_IMPLEMENTATION.md`
- **Backend API Reference:** `docs/TENANT_CONFIG_GUIDE.md`
- **Admin Endpoints:** `docs/ADMIN_ENDPOINTS.md`

---

## API Quick Reference

### Onboarding Endpoint

```
POST /api/v1/tenant/onboard/whatsapp-client
Authorization: Bearer {jwt_token}
Content-Type: application/json

Body:
{
  "code": "AUTH_CODE_FROM_FB",
  "waba_id": "123456789",
  "phone_number_id": "987654321",
  "redirect_uri": "https://yourdomain.com/current-page"
}
```

### Delete All Configs (Admin Only - Testing)

```
DELETE /api/v1/tenant/admin/configs/delete-all?confirmation=DELETE_ALL_CONFIGS_PERMANENTLY
Authorization: Bearer {jwt_token}
```

---

**Implementation Time Estimate:** 2-4 hours

**Priority:** High

**Dependencies:** Facebook SDK, axios/fetch for API calls

---

Good luck! 🚀
