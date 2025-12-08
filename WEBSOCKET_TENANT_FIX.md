# WebSocket Tenant ID Fix - Frontend Guide

## 🔴 Problem
Your frontend shows "Connected" but backend logs show:
```
⚠️ No WebSocket connections for tenant d2bcd1ee-e5c5-4c9f-bff2-aaf901d40440
```

**Root Cause:** Frontend is connecting with **wrong or missing tenant_id** in WebSocket URL.

---

## ✅ Solution

### 1. **Get the Correct Tenant ID**

Your backend's tenant ID is: `d2bcd1ee-e5c5-4c9f-bff2-aaf901d40440`

**How to get it:**
- Check your `.env` file: `DEFAULT_TENANT_ID=d2bcd1ee-e5c5-4c9f-bff2-aaf901d40440`
- OR get it from login response (if using JWT auth)
- OR hardcode it for now (single-tenant setup)

### 2. **Fix WebSocket Connection URL**

**Current (WRONG):**
```javascript
// Missing tenant_id or wrong value
ws = new WebSocket('ws://your-server.com/ws');
// OR
ws = new WebSocket('ws://your-server.com/ws?tenant_id=wrong-value');
```

**Correct (RIGHT):**
```javascript
const TENANT_ID = 'd2bcd1ee-e5c5-4c9f-bff2-aaf901d40440'; // From .env or API

ws = new WebSocket(`ws://your-server.com/ws?tenant_id=${TENANT_ID}`);
```

### 3. **Full Implementation Example**

```javascript
// config.js or constants.js
export const TENANT_ID = 'd2bcd1ee-e5c5-4c9f-bff2-aaf901d40440';
export const WS_URL = 'ws://localhost:8002/ws'; // or your server URL

// websocket.js
import { TENANT_ID, WS_URL } from './config';

let ws = null;

function connectWebSocket() {
  // Ensure tenant_id is in URL
  const wsUrl = `${WS_URL}?tenant_id=${TENANT_ID}`;

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log('✅ WebSocket Connected with tenant:', TENANT_ID);
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('📩 WebSocket message:', data);

    if (data.event === 'message_status') {
      // Update message status in UI
      updateMessageStatus(data.data.message_id, data.data.status);
    }
  };

  ws.onerror = (error) => {
    console.error('❌ WebSocket error:', error);
  };

  ws.onclose = () => {
    console.log('🔌 WebSocket disconnected, reconnecting...');
    setTimeout(connectWebSocket, 3000);
  };
}

// Initialize
connectWebSocket();
```

### 4. **React Example**

```jsx
import React, { useEffect, useRef } from 'react';

const TENANT_ID = 'd2bcd1ee-e5c5-4c9f-bff2-aaf901d40440';

function ChatComponent() {
  const wsRef = useRef(null);

  useEffect(() => {
    // Connect with correct tenant_id
    const ws = new WebSocket(`ws://localhost:8002/ws?tenant_id=${TENANT_ID}`);

    ws.onopen = () => {
      console.log('✅ WebSocket Connected');
    };

    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data);

      if (payload.event === 'message_status') {
        // Handle status update
        console.log('Status update:', payload.data);
      }
    };

    wsRef.current = ws;

    return () => ws.close();
  }, []);

  return <div>Chat UI</div>;
}
```

### 5. **Debugging - Check Connection**

**Browser Console:**
```javascript
// Check if WebSocket is connected
console.log('WebSocket state:', ws.readyState);
// 0 = CONNECTING, 1 = OPEN, 2 = CLOSING, 3 = CLOSED

// Check the URL
console.log('WebSocket URL:', ws.url);
// Should show: ws://localhost:8002/ws?tenant_id=d2bcd1ee-e5c5-4c9f-bff2-aaf901d40440
```

**Test in Browser DevTools:**
```javascript
// Open browser console and run:
const ws = new WebSocket('ws://localhost:8002/ws?tenant_id=d2bcd1ee-e5c5-4c9f-bff2-aaf901d40440');

ws.onopen = () => console.log('✅ Connected!');
ws.onmessage = (e) => console.log('📩 Message:', JSON.parse(e.data));
```

---

## 🔍 Verify It Works

After fixing, you should see in **backend logs**:
```
✅ WS connected: tenant=d2bcd1ee-e5c5-4c9f-bff2-aaf901d40440 total=1
```

Instead of:
```
⚠️ No WebSocket connections for tenant d2bcd1ee-e5c5-4c9f-bff2-aaf901d40440
```

---

## ⚠️ Common Mistakes

### Mistake 1: Hardcoded Wrong Tenant ID
```javascript
// DON'T DO THIS (unless it matches your .env)
const TENANT_ID = 'default';
```

### Mistake 2: Missing tenant_id Query Parameter
```javascript
// WRONG - Missing tenant_id
ws = new WebSocket('ws://localhost:8002/ws');

// RIGHT - Has tenant_id
ws = new WebSocket('ws://localhost:8002/ws?tenant_id=d2bcd1ee-e5c5-4c9f-bff2-aaf901d40440');
```

### Mistake 3: Using http instead of ws
```javascript
// WRONG
ws = new WebSocket('http://localhost:8002/ws');

// RIGHT
ws = new WebSocket('ws://localhost:8002/ws?tenant_id=...');
```

---

## 📋 Quick Checklist

- [ ] Get tenant_id from backend `.env` file
- [ ] Update frontend WebSocket URL to include `?tenant_id=...`
- [ ] Verify WebSocket URL in browser DevTools Network tab
- [ ] Check backend logs for "WS connected" message
- [ ] Test by sending a message and checking status updates

---

## 🚨 Security Note

For production:
- **Don't hardcode tenant_id** in frontend code
- Get it from login API response
- Store in session/localStorage
- Include in WebSocket connection dynamically

```javascript
// Better approach for production
const token = localStorage.getItem('auth_token');
const tenantId = localStorage.getItem('tenant_id'); // From login response

const ws = new WebSocket(`ws://your-server.com/ws?tenant_id=${tenantId}`);
```
