# Frontend notes: Consuming WhatsApp webhooks and realtime updates

This document explains how your React app can consume realtime WhatsApp events and REST data from the FastAPI backend.

Source references:
- [app/main.py](app/main.py)
- [Python.register_handlers()](app/services/whatsapp_handlers.py:41)
- [Python.handle_message()](app/services/whatsapp_handlers.py:50)
- [Python.handle_status()](app/services/whatsapp_handlers.py:278)
- [Python.notify_clients_sync()](app/ws/manager.py:77)
- [GET /api/v1/webhooks/logs](app/api/v1/webhooks.py:29)
- [DELETE /api/v1/webhooks/logs/cleanup](app/api/v1/webhooks.py:52)

Overview

- Incoming Meta webhooks are handled in [Python.register_handlers()](app/services/whatsapp_handlers.py:41). Each message is saved, normalized, and broadcast to your frontend over WebSocket.
- Phone numbers are normalized with a leading "+" in [Python._save_message()](app/services/message_service.py:489).
- Outgoing auto-replies and manual sends are also broadcast so UI stays in sync.
- Status updates (sent/delivered/read) are logged via [Python.handle_status()](app/services/whatsapp_handlers.py:278).

Realtime stream (WebSocket)

- Endpoint: ws(s)://YOUR_API_HOST/ws/{tenant_id} implemented at [Python.websocket_endpoint()](app/main.py:442).
- The backend pushes JSON envelopes:

```json
{
  "event": "message_incoming" | "message_outgoing",
  "data": {
    "phone": "+911234567890",
    "name": "Contact name or null",
    "message": {
      "id": "wa_msg_id or null",
      "type": "text|image|video|audio|document|location|...",
      "text": "string or placeholder e.g. (image)",
      "timestamp": "ISO-8601 string",
      "direction": "incoming|outgoing"
    }
  }
}
```

React example (plain WebSocket)

```tsx
// ChatEvents.tsx
import { useEffect, useRef } from "react";

type WsEvent = {
  event: "message_incoming" | "message_outgoing";
  data: {
    phone: string;
    name?: string | null;
    message: { id?: string | null; type: string; text?: string | null; timestamp?: string; direction: "incoming" | "outgoing" };
  };
};

export function useChatStream(tenantId: string, onEvent: (e: WsEvent) => void) {
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!tenantId) return;
    let retry = 0;
    let closed = false;

    const connect = () => {
      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      const url = `${proto}://${window.location.host}/ws/${tenantId}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => { retry = 0; /* optionally send "ping" */ };
      ws.onmessage = (ev) => {
        try { onEvent(JSON.parse(ev.data) as WsEvent); } catch {}
      };
      ws.onclose = () => {
        if (closed) return;
        retry = Math.min(retry + 1, 6);
        setTimeout(connect, 500 * Math.pow(2, retry)); // backoff
      };
      ws.onerror = () => ws.close();
    };

    connect();
    return () => { closed = true; wsRef.current?.close(); };
  }, [tenantId, onEvent]);
}
```

REST endpoints used by the frontend

- Send text: POST /api/send/text implemented at [Python.send_text_message()](app/main.py:271)
  - Body: { "to": "+911234567890" | "911234567890", "text": "hello" }
  - Returns: { "message_id": "wa-id or null", "phone": "echo of to", "text": "hello" }

- List conversations: GET /api/conversations at [Python.list_conversations()](app/main.py:241)

- Conversation detail: GET /api/conversations/{phone} at [Python.get_conversation()](app/main.py:259)

- Webhook logs: GET /api/v1/webhooks/logs at [Python.get_webhook_logs()](app/api/v1/webhooks.py:29)
  - Query: limit (<=200), skip, log_type ("message"|"status"), phone (substring match)

- Cleanup old logs: DELETE /api/v1/webhooks/logs/cleanup at [Python.cleanup_old_logs()](app/api/v1/webhooks.py:52)

Example fetch (send message)

```ts
async function sendText(to: string, text: string, tenantId: string) {
  const res = await fetch("/api/send/text", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Tenant-Id": tenantId, // required if not using JWT/session
    },
    body: JSON.stringify({ to, text }),
    credentials: "include", // only if relying on session cookies
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as { message_id: string | null; phone: string; text: string };
}
```

Tenancy and auth

- If you call APIs without Authorization, the middleware tries to inject a tenant header using session at [Python.add_default_tenant_header()](app/main.py:133).
- For a standalone React SPA, prefer to always send X-Tenant-Id yourself on every request.
- WebSocket path must include tenant_id: ws://.../ws/{tenant_id}.

CORS for local React

- Allowed origins include http://localhost:3000 and 5173 in [Python.CORSMiddleware()](app/main.py:73).
- Credentials are allowed. If you rely on cookies, set fetch credentials: "include" and ensure origin matches the allowed list.

Message normalization and deduplication

- Phone numbers are normalized to begin with "+" in [Python._normalize_phone()](app/services/message_service.py:25) and enforced at save in [Python._save_message()](app/services/message_service.py:489).
- Duplicate inserts are avoided by message_id checks in [Python._save_message()](app/services/message_service.py:516).

Status updates

- Status webhooks are logged with log_type "status" via [Python.handle_status()](app/services/whatsapp_handlers.py:278). You can query them from [Python.get_webhook_logs()](app/api/v1/webhooks.py:29) with log_type=status.

Minimal UI wiring example

```tsx
// useChat.ts
import { useEffect, useState, useCallback } from "react";

type Msg = { phone: string; name?: string | null; type: string; text?: string | null; timestamp?: string; direction: "incoming" | "outgoing" };

export function useChat(tenantId: string) {
  const [messages, setMessages] = useState<Msg[]>([]);

  const onEvent = useCallback((e: any) => {
    const m = e?.data?.message;
    if (!m) return;
    setMessages((prev) => [...prev, { phone: e.data.phone, name: e.data.name, type: m.type, text: m.text, timestamp: m.timestamp, direction: m.direction }]);
  }, []);

  useChatStream(tenantId, onEvent);

  return { messages, sendText: (to: string, text: string) => sendText(to, text, tenantId) };
}
```

Useful diagnostics

- Health: GET /healthz at [Python.health()](app/main.py:321)
- Verify JWT: GET /api/auth/verify at [Python.verify_jwt()](app/main.py:423)

Notes and gotchas

- The backend uses a single DEFAULT_TENANT_ID for incoming webhooks (Meta doesn’t send tenant). See usage in [Python.register_handlers()](app/services/whatsapp_handlers.py:45) and [Python.handle_message()](app/services/whatsapp_handlers.py:65).
- For images/videos/documents, text will be a caption or a placeholder like "(image)".
- When displaying phones, do not re-add "+"; backend already normalizes.
- WebSocket may drop on network changes; use exponential backoff reconnect as in example.

Quick checklist

- Create tenant id in your app state.
- Open WebSocket to /ws/{tenant_id}.
- Render messages based on incoming/outgoing envelopes.
- Use POST /api/send/text to send messages.
- Optionally show webhook logs via GET /api/v1/webhooks/logs.

File map for further reading

- WebSocket manager: [app/ws/manager.py](app/ws/manager.py)
- WhatsApp handlers: [app/services/whatsapp_handlers.py](app/services/whatsapp_handlers.py)
- Message service: [app/services/message_service.py](app/services/message_service.py)
- Webhook logs API: [app/api/v1/webhooks.py](app/api/v1/webhooks.py)
- FastAPI app & routes: [app/main.py](app/main.py)