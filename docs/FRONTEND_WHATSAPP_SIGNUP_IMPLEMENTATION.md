# WhatsApp Embedded Signup - Frontend Implementation Guide

## 🎯 Objective

Implement WhatsApp embedded signup flow that captures OAuth code and business account details, then sends them to the backend for onboarding.

---

## 📋 Implementation Steps

### 1. Add postMessage Listener (React Component)

Create a React component that handles the WhatsApp embedded signup flow:

```jsx
import React, { useState, useEffect } from 'react';

function WhatsAppEmbeddedSignup() {
  // State to capture data from both sources
  const [oauthCode, setOauthCode] = useState(null);
  const [wabaId, setWabaId] = useState(null);
  const [phoneNumberId, setPhoneNumberId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  // Listen for postMessage from Facebook embedded signup
  useEffect(() => {
    const handleMessage = (event) => {
      // Security: Verify origin is from Facebook
      if (event.origin !== "https://www.facebook.com") {
        console.warn('Ignoring message from untrusted origin:', event.origin);
        return;
      }

      try {
        // Parse message data
        const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;

        console.log('Received postMessage:', data);

        // Check for WhatsApp signup completion
        if (data.type === 'WA_EMBEDDED_SIGNUP' && data.event === 'FINISH') {
          console.log('WhatsApp signup finished!');

          // Extract business account data
          const setupData = data.data;

          if (setupData.waba_id && setupData.phone_number_id) {
            console.log('WABA ID:', setupData.waba_id);
            console.log('Phone Number ID:', setupData.phone_number_id);

            setWabaId(setupData.waba_id);
            setPhoneNumberId(setupData.phone_number_id);
          }
        }
      } catch (err) {
        console.error('Error parsing postMessage data:', err);
      }
    };

    // Add event listener
    window.addEventListener('message', handleMessage);

    // Cleanup on unmount
    return () => {
      window.removeEventListener('message', handleMessage);
    };
  }, []);

  // Trigger when all data is available
  useEffect(() => {
    if (oauthCode && wabaId && phoneNumberId && !loading && !success) {
      completeOnboarding();
    }
  }, [oauthCode, wabaId, phoneNumberId]);

  // Facebook Login callback
  const handleFacebookLogin = () => {
    setLoading(true);
    setError(null);

    // Facebook SDK login
    window.FB.login(
      (response) => {
        if (response.authResponse) {
          console.log('FB Login successful!');
          console.log('Auth Code:', response.authResponse.code);

          // Capture OAuth code
          setOauthCode(response.authResponse.code);
        } else {
          console.log('User cancelled login or did not fully authorize.');
          setError('Login cancelled or authorization failed');
          setLoading(false);
        }
      },
      {
        config_id: 'YOUR_CONFIG_ID', // Get from Meta App settings
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

  // Call backend API to complete onboarding
  const completeOnboarding = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/tenant/onboard/whatsapp-client', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          code: oauthCode,
          waba_id: wabaId,
          phone_number_id: phoneNumberId,
          redirect_uri: window.location.href
        })
      });

      const data = await response.json();

      if (response.ok && data.success) {
        console.log('Onboarding complete!', data);
        setSuccess(true);

        // Optional: Redirect to dashboard
        setTimeout(() => {
          window.location.href = '/dashboard';
        }, 2000);
      } else {
        throw new Error(data.detail || 'Onboarding failed');
      }
    } catch (err) {
      console.error('Onboarding error:', err);
      setError(err.message || 'Failed to complete onboarding');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="whatsapp-signup">
      <h2>Connect WhatsApp Business Account</h2>

      {error && (
        <div className="error-message" style={{ color: 'red', padding: '10px', marginBottom: '10px' }}>
          ❌ {error}
        </div>
      )}

      {success && (
        <div className="success-message" style={{ color: 'green', padding: '10px', marginBottom: '10px' }}>
          ✅ WhatsApp connected successfully! Redirecting...
        </div>
      )}

      {!success && (
        <>
          <button
            onClick={handleFacebookLogin}
            disabled={loading}
            className="btn-primary"
            style={{
              padding: '12px 24px',
              fontSize: '16px',
              backgroundColor: '#25D366',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.6 : 1
            }}
          >
            {loading ? 'Connecting...' : 'Connect WhatsApp Business'}
          </button>

          {/* Debug info */}
          <div style={{ marginTop: '20px', fontSize: '12px', color: '#666' }}>
            <p>Status:</p>
            <ul>
              <li>OAuth Code: {oauthCode ? '✅ Received' : '⏳ Waiting...'}</li>
              <li>WABA ID: {wabaId ? `✅ ${wabaId}` : '⏳ Waiting...'}</li>
              <li>Phone ID: {phoneNumberId ? `✅ ${phoneNumberId}` : '⏳ Waiting...'}</li>
            </ul>
          </div>
        </>
      )}
    </div>
  );
}

export default WhatsAppEmbeddedSignup;
```

---

## 🔌 Backend API Reference

### Endpoint Details

**URL:** `POST /api/v1/tenant/onboard/whatsapp-client`

**Authentication:** Required (JWT Bearer token)

**Content-Type:** `application/json`

---

### Request Payload

```typescript
interface OnboardingRequest {
  code: string;              // OAuth authorization code from FB.login
  waba_id: string;           // WhatsApp Business Account ID from postMessage
  phone_number_id: string;   // Phone Number ID from postMessage
  redirect_uri: string;      // Current page URL (window.location.href)
}
```

**Example:**
```json
{
  "code": "AQBxh5F7G8...",
  "waba_id": "123456789012345",
  "phone_number_id": "987654321098765",
  "redirect_uri": "https://yourdomain.com/whatsapp-setup"
}
```

---

### Response Format

#### Success Response (200 OK)

```typescript
interface OnboardingResponse {
  success: boolean;           // Always true on success
  message: string;            // Success message
  tenant_id: string;          // Your tenant identifier
  config_id: number;          // Database ID of created config
  waba_id: string;            // WhatsApp Business Account ID
  phone_number_id: string;    // Phone Number ID
}
```

**Example:**
```json
{
  "success": true,
  "message": "WhatsApp Business API onboarding completed successfully",
  "tenant_id": "d2bcd1ee-e5c5-4c9f-bff2-aaf901d40440",
  "config_id": 1,
  "waba_id": "123456789012345",
  "phone_number_id": "987654321098765"
}
```

#### Error Responses

**400 Bad Request** - Invalid code or missing parameters
```json
{
  "detail": "Failed to obtain access token from Meta"
}
```

**401 Unauthorized** - Missing or invalid JWT token
```json
{
  "detail": "Authentication required"
}
```

**502 Bad Gateway** - Failed to communicate with Meta
```json
{
  "detail": "Failed to exchange code with Meta: Connection timeout"
}
```

**500 Internal Server Error** - Database or unexpected error
```json
{
  "detail": "Failed to save configuration: Database error"
}
```

---

## 📝 Complete Implementation Example

### Full Component with Error Handling

```jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8002';

function WhatsAppOnboardingPage() {
  const [state, setState] = useState({
    code: null,
    wabaId: null,
    phoneNumberId: null,
    loading: false,
    error: null,
    success: false,
    progress: 'idle' // idle, waiting-for-data, calling-api, complete
  });

  // Initialize Facebook SDK
  useEffect(() => {
    // Load FB SDK if not already loaded
    if (!window.FB) {
      loadFacebookSDK();
    }
  }, []);

  const loadFacebookSDK = () => {
    window.fbAsyncInit = function() {
      window.FB.init({
        appId: process.env.REACT_APP_FB_APP_ID,
        cookie: true,
        xfbml: true,
        version: 'v19.0'
      });
    };

    // Load SDK script
    (function(d, s, id) {
      var js, fjs = d.getElementsByTagName(s)[0];
      if (d.getElementById(id)) return;
      js = d.createElement(s);
      js.id = id;
      js.src = "https://connect.facebook.net/en_US/sdk.js";
      fjs.parentNode.insertBefore(js, fjs);
    }(document, 'script', 'facebook-jssdk'));
  };

  // Listen for postMessage
  useEffect(() => {
    const handleMessage = (event) => {
      // IMPORTANT: Verify origin for security
      if (event.origin !== "https://www.facebook.com") {
        return;
      }

      try {
        const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;

        if (data.type === 'WA_EMBEDDED_SIGNUP' && data.event === 'FINISH') {
          const { waba_id, phone_number_id } = data.data;

          console.log('✅ Received WhatsApp account data');

          setState(prev => ({
            ...prev,
            wabaId: waba_id,
            phoneNumberId: phone_number_id,
            progress: prev.code ? 'calling-api' : 'waiting-for-data'
          }));
        }
      } catch (err) {
        console.error('Error parsing message:', err);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  // Auto-trigger API call when all data is ready
  useEffect(() => {
    if (state.code && state.wabaId && state.phoneNumberId && state.progress === 'waiting-for-data') {
      completeOnboarding();
    }
  }, [state.code, state.wabaId, state.phoneNumberId, state.progress]);

  // Start Facebook login flow
  const startOnboarding = () => {
    if (!window.FB) {
      setState(prev => ({ ...prev, error: 'Facebook SDK not loaded' }));
      return;
    }

    setState(prev => ({ ...prev, loading: true, error: null, progress: 'waiting-for-data' }));

    window.FB.login(
      (response) => {
        if (response.authResponse && response.authResponse.code) {
          console.log('✅ Received OAuth code');

          setState(prev => ({
            ...prev,
            code: response.authResponse.code,
            progress: prev.wabaId && prev.phoneNumberId ? 'calling-api' : 'waiting-for-data'
          }));
        } else {
          setState(prev => ({
            ...prev,
            loading: false,
            error: 'Login cancelled or authorization failed',
            progress: 'idle'
          }));
        }
      },
      {
        config_id: process.env.REACT_APP_FB_CONFIG_ID,
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

  // Call backend API
  const completeOnboarding = async () => {
    setState(prev => ({ ...prev, loading: true, error: null, progress: 'calling-api' }));

    try {
      const jwtToken = localStorage.getItem('jwt_token') || sessionStorage.getItem('jwt_token');

      if (!jwtToken) {
        throw new Error('Not authenticated. Please log in first.');
      }

      const response = await axios.post(
        `${API_BASE_URL}/api/v1/tenant/onboard/whatsapp-client`,
        {
          code: state.code,
          waba_id: state.wabaId,
          phone_number_id: state.phoneNumberId,
          redirect_uri: window.location.href
        },
        {
          headers: {
            'Authorization': `Bearer ${jwtToken}`,
            'Content-Type': 'application/json'
          }
        }
      );

      console.log('✅ Onboarding complete:', response.data);

      setState(prev => ({
        ...prev,
        loading: false,
        success: true,
        progress: 'complete'
      }));

      // Redirect after 2 seconds
      setTimeout(() => {
        window.location.href = '/dashboard';
      }, 2000);

    } catch (err) {
      console.error('❌ Onboarding failed:', err);

      const errorMessage = err.response?.data?.detail || err.message || 'Failed to complete onboarding';

      setState(prev => ({
        ...prev,
        loading: false,
        error: errorMessage,
        progress: 'idle'
      }));
    }
  };

  return (
    <div style={{ padding: '40px', maxWidth: '600px', margin: '0 auto' }}>
      <h1>WhatsApp Business Setup</h1>
      <p>Connect your WhatsApp Business Account to start messaging</p>

      {/* Error Message */}
      {state.error && (
        <div style={{
          padding: '15px',
          backgroundColor: '#fee',
          border: '1px solid #fcc',
          borderRadius: '8px',
          marginBottom: '20px',
          color: '#c00'
        }}>
          <strong>❌ Error:</strong> {state.error}
        </div>
      )}

      {/* Success Message */}
      {state.success && (
        <div style={{
          padding: '15px',
          backgroundColor: '#efe',
          border: '1px solid #cfc',
          borderRadius: '8px',
          marginBottom: '20px',
          color: '#060'
        }}>
          <strong>✅ Success!</strong> WhatsApp connected successfully. Redirecting to dashboard...
        </div>
      )}

      {/* Progress Indicators */}
      {state.progress !== 'idle' && !state.success && (
        <div style={{
          padding: '15px',
          backgroundColor: '#f5f5f5',
          borderRadius: '8px',
          marginBottom: '20px'
        }}>
          <h3>Progress:</h3>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            <li>
              {state.code ? '✅' : '⏳'} OAuth Code: {state.code ? 'Received' : 'Waiting...'}
            </li>
            <li>
              {state.wabaId ? '✅' : '⏳'} WABA ID: {state.wabaId || 'Waiting...'}
            </li>
            <li>
              {state.phoneNumberId ? '✅' : '⏳'} Phone ID: {state.phoneNumberId || 'Waiting...'}
            </li>
            <li>
              {state.progress === 'calling-api' ? '⏳' : state.success ? '✅' : '⬜'} API Call: {
                state.progress === 'calling-api' ? 'In progress...' :
                state.success ? 'Complete' :
                'Pending'
              }
            </li>
          </ul>
        </div>
      )}

      {/* Action Button */}
      {!state.success && (
        <button
          onClick={startOnboarding}
          disabled={state.loading}
          style={{
            padding: '15px 30px',
            fontSize: '18px',
            backgroundColor: state.loading ? '#ccc' : '#25D366',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: state.loading ? 'not-allowed' : 'pointer',
            width: '100%',
            fontWeight: 'bold'
          }}
        >
          {state.loading ? '⏳ Connecting...' : '🔗 Connect WhatsApp Business'}
        </button>
      )}

      {/* Help Text */}
      <div style={{ marginTop: '30px', fontSize: '14px', color: '#666' }}>
        <p><strong>What happens next?</strong></p>
        <ol>
          <li>Click the button to open Facebook login</li>
          <li>Authorize your WhatsApp Business Account</li>
          <li>We'll automatically complete the setup</li>
          <li>You'll be redirected to the dashboard</li>
        </ol>
      </div>
    </div>
  );
}

export default WhatsAppOnboardingPage;
```

---

## 🔧 Environment Variables Required

Add these to your `.env` file:

```env
# React App
REACT_APP_API_URL=http://localhost:8002
REACT_APP_FB_APP_ID=your_facebook_app_id
REACT_APP_FB_CONFIG_ID=your_config_id_from_meta
```

---

## 🧪 Testing Checklist

- [ ] Facebook SDK loads correctly
- [ ] postMessage listener captures WABA and Phone IDs
- [ ] OAuth code is received from FB.login
- [ ] All three values (code, waba_id, phone_number_id) are captured
- [ ] API call is triggered automatically
- [ ] Success/error messages display correctly
- [ ] Redirect to dashboard works
- [ ] Error handling for failed API calls
- [ ] Error handling for cancelled login

---

## 🐛 Troubleshooting

### Issue: postMessage not received

**Solution:**
- Verify origin check: `event.origin === "https://www.facebook.com"`
- Check browser console for parsing errors
- Ensure Facebook embedded signup is properly configured in Meta Business Manager

### Issue: API returns 401 Unauthorized

**Solution:**
- Verify JWT token is stored in localStorage or sessionStorage
- Check Authorization header format: `Bearer <token>`
- Ensure user is logged in before accessing this page

### Issue: API returns 502 Bad Gateway

**Solution:**
- Check backend .env has correct FB_APP_ID and FB_APP_SECRET
- Verify code hasn't expired (codes expire quickly, ~10 minutes)
- Ensure backend can reach Meta's servers (firewall/proxy issues)

---

## 📚 Additional Resources

- [Meta WhatsApp Embedded Signup Docs](https://developers.facebook.com/docs/whatsapp/embedded-signup)
- [Facebook Login for Web](https://developers.facebook.com/docs/facebook-login/web)
- Backend API Documentation: `docs/TENANT_CONFIG_GUIDE.md`

---

**Last Updated:** 2025-12-11
