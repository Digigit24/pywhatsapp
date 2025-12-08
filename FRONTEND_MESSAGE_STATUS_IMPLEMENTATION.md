# Frontend Implementation Guide: Message Status (Double Tick & Blue Tick)

## Overview
The backend now fully supports WhatsApp message status tracking with real-time updates via WebSocket. Your frontend needs to handle these status updates to display delivery indicators (double tick) and read receipts (blue tick).

---

## Backend Changes Summary

### ✅ What's Already Implemented:

1. **Database Schema**: Added `status` field to `Message` model
   - Values: `'sent'`, `'delivered'`, `'read'`, `'failed'`
   - Default: `'sent'`

2. **WebSocket Events**: Real-time status broadcasts
   - Event type: `message_status`
   - Contains: `message_id`, `status`, `phone`, `timestamp`

3. **API Response**: All message endpoints now include `status` field
   - `/api/v1/messages`
   - `/api/v1/conversations/{phone}`
   - Message responses include current status

4. **Webhook Handler**: Automatically processes WhatsApp status webhooks
   - Updates database
   - Broadcasts to connected WebSocket clients

---

## Frontend Implementation Steps

### 1. WebSocket Connection & Event Handling

**Connect to WebSocket** (if not already connected):
```javascript
const ws = new WebSocket(`ws://localhost:8002/ws?tenant_id=${tenantId}`);
```

**Listen for Status Updates**:
```javascript
ws.onmessage = (event) => {
  const payload = JSON.parse(event.data);

  if (payload.event === 'message_status') {
    const { message_id, status, phone, timestamp } = payload.data;

    // Update message in your state/UI
    updateMessageStatus(message_id, status);
  }
};
```

### 2. Update Message Display Logic

**Message Status Enum**:
```javascript
const MessageStatus = {
  SENT: 'sent',         // Single grey tick ✓
  DELIVERED: 'delivered', // Double grey tick ✓✓
  READ: 'read',          // Double blue tick ✓✓ (blue)
  FAILED: 'failed'       // Red indicator ✗
};
```

**Display Status Icons**:
```javascript
function getStatusIcon(status) {
  switch(status) {
    case 'sent':
      return '✓';  // Single grey tick
    case 'delivered':
      return '✓✓'; // Double grey tick
    case 'read':
      return '✓✓'; // Double blue tick (style with blue color)
    case 'failed':
      return '✗';  // Red X
    default:
      return '○';  // Pending/sending
  }
}
```

**CSS Styling Example**:
```css
.message-status {
  font-size: 12px;
  margin-left: 5px;
}

.status-sent {
  color: #999; /* Grey */
}

.status-delivered {
  color: #999; /* Grey */
}

.status-read {
  color: #0088cc; /* WhatsApp blue */
}

.status-failed {
  color: #ff0000; /* Red */
}
```

### 3. React Component Example

```jsx
import React, { useState, useEffect } from 'react';

function MessageItem({ message }) {
  const [status, setStatus] = useState(message.status || 'sent');

  useEffect(() => {
    // Subscribe to WebSocket updates
    const handleStatusUpdate = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.event === 'message_status' &&
          payload.data.message_id === message.message_id) {
        setStatus(payload.data.status);
      }
    };

    window.ws.addEventListener('message', handleStatusUpdate);
    return () => window.ws.removeEventListener('message', handleStatusUpdate);
  }, [message.message_id]);

  const getStatusIcon = () => {
    switch(status) {
      case 'sent': return <span className="status-sent">✓</span>;
      case 'delivered': return <span className="status-delivered">✓✓</span>;
      case 'read': return <span className="status-read">✓✓</span>;
      case 'failed': return <span className="status-failed">✗</span>;
      default: return <span className="status-pending">○</span>;
    }
  };

  return (
    <div className="message-item">
      <span className="message-text">{message.text}</span>
      {message.direction === 'outgoing' && (
        <span className="message-status">{getStatusIcon()}</span>
      )}
    </div>
  );
}
```

### 4. Vue.js Component Example

```vue
<template>
  <div class="message-item">
    <span class="message-text">{{ message.text }}</span>
    <span v-if="message.direction === 'outgoing'" class="message-status">
      <span :class="statusClass">{{ statusIcon }}</span>
    </span>
  </div>
</template>

<script>
export default {
  props: ['message'],
  data() {
    return {
      currentStatus: this.message.status || 'sent'
    };
  },
  computed: {
    statusIcon() {
      const icons = {
        sent: '✓',
        delivered: '✓✓',
        read: '✓✓',
        failed: '✗'
      };
      return icons[this.currentStatus] || '○';
    },
    statusClass() {
      return `status-${this.currentStatus}`;
    }
  },
  mounted() {
    this.subscribeToStatusUpdates();
  },
  methods: {
    subscribeToStatusUpdates() {
      this.$ws.addEventListener('message', (event) => {
        const payload = JSON.parse(event.data);
        if (payload.event === 'message_status' &&
            payload.data.message_id === this.message.message_id) {
          this.currentStatus = payload.data.status;
        }
      });
    }
  }
};
</script>
```

### 5. State Management (Redux/Vuex)

**Redux Action**:
```javascript
// actions.js
export const updateMessageStatus = (messageId, status) => ({
  type: 'UPDATE_MESSAGE_STATUS',
  payload: { messageId, status }
});

// reducer.js
case 'UPDATE_MESSAGE_STATUS':
  return {
    ...state,
    messages: state.messages.map(msg =>
      msg.message_id === action.payload.messageId
        ? { ...msg, status: action.payload.status }
        : msg
    )
  };
```

**Vuex Mutation**:
```javascript
// store.js
mutations: {
  UPDATE_MESSAGE_STATUS(state, { messageId, status }) {
    const message = state.messages.find(m => m.message_id === messageId);
    if (message) {
      message.status = status;
    }
  }
}
```

### 6. Initial Message Load

When fetching conversations or messages, the `status` field is already included:

```javascript
// Fetch conversation
const response = await fetch(`/api/v1/conversations/${phone}`);
const data = await response.json();

// Each message already has status field
data.data.messages.forEach(message => {
  console.log(message.status); // 'sent', 'delivered', 'read', 'failed'
});
```

---

## WebSocket Event Structure

### Message Status Update Event

```json
{
  "event": "message_status",
  "data": {
    "message_id": "wamid.HBgNOTE5ODc2NTQzMjEwFQIAERgSQTNBNzM5RjY2M0Y1RTEwQzQA",
    "status": "delivered",
    "phone": "+919876543210",
    "timestamp": "2025-12-09T10:30:45.123456"
  }
}
```

### Status Values:
- `"sent"` - Message sent from your server (single grey tick)
- `"delivered"` - Message delivered to recipient's device (double grey tick)
- `"read"` - Message read by recipient (double blue tick)
- `"failed"` - Message failed to send (red indicator)

---

## Important Notes

### 1. **Only Show Status for Outgoing Messages**
```javascript
{message.direction === 'outgoing' && <StatusIcon status={status} />}
```

### 2. **Status Progression**
Messages follow this flow:
```
sent → delivered → read
```
Never show a "downgrade" (e.g., from `read` to `delivered`)

### 3. **Handle Missing message_id**
```javascript
if (!message.message_id) {
  // Show "sending" indicator for messages not yet synced
  return <span>○</span>;
}
```

### 4. **Reconnection Handling**
```javascript
ws.onclose = () => {
  setTimeout(() => connectWebSocket(), 3000);
};
```

### 5. **Fallback: Polling (Optional)**
If WebSocket connection fails, you can poll the API:
```javascript
// Poll status updates every 5 seconds (not recommended, use WebSocket)
setInterval(async () => {
  const response = await fetch(`/api/v1/messages/${messageId}`);
  const data = await response.json();
  updateStatus(data.data.status);
}, 5000);
```

---

## Testing Checklist

- [ ] WebSocket connects successfully
- [ ] Receives `message_status` events
- [ ] Updates UI when status changes
- [ ] Shows correct icons (✓, ✓✓, ✓✓ blue)
- [ ] Only displays status for outgoing messages
- [ ] Handles reconnection gracefully
- [ ] Initial message load includes status
- [ ] Status persists after page refresh

---

## Troubleshooting

### Issue: Status not updating in UI
**Solution**: Check WebSocket connection and event listener registration

### Issue: Wrong status displayed
**Solution**: Ensure you're matching by `message_id`, not by index or phone

### Issue: Status showing for incoming messages
**Solution**: Add `direction === 'outgoing'` check

### Issue: Status disappears after refresh
**Solution**: Fetch messages with status from API on load

---

## API Endpoints Reference

### Get Messages (with status)
```
GET /api/v1/messages?phone={phone}&limit=50
```

Response includes `status` field:
```json
{
  "data": {
    "items": [
      {
        "id": 123,
        "message_id": "wamid.xxx",
        "phone": "+919876543210",
        "text": "Hello",
        "direction": "outgoing",
        "status": "delivered",
        "created_at": "2025-12-09T10:30:00"
      }
    ]
  }
}
```

### Get Conversation (with status)
```
GET /api/v1/conversations/{phone}
```

---

## Summary

✅ **Backend is fully ready** - No additional backend work needed
✅ **WebSocket broadcasts status updates** in real-time
✅ **API responses include status** for initial load
✅ **Database stores status** persistently

**Your frontend needs to:**
1. Listen to WebSocket `message_status` events
2. Update message status in state when event received
3. Display appropriate tick icons based on status
4. Only show status for outgoing messages

**Status Flow:**
```
User sends message → Backend returns message_id
↓
WhatsApp webhook sends "sent" → WebSocket broadcast
↓
WhatsApp webhook sends "delivered" → WebSocket broadcast (show ✓✓ grey)
↓
User reads message → WhatsApp webhook sends "read" → WebSocket broadcast (show ✓✓ blue)
```

---

## Contact
For issues or questions, check backend logs at `logs/debug.log`
