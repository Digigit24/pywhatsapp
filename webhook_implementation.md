# WhatsApp Business API and Webhook Guide

**Version:** 3.0.0  
**Last Updated:** December 2025  
**A comprehensive guide to the backend API, webhook handling, and real-time event system.**

---

## 1. Overview

This document provides a complete guide to the WhatsApp Business API backend. It covers two main areas:
1.  **Webhook Implementation:** How the system processes real-time events from Meta (incoming messages, status updates, etc.).
2.  **REST API Endpoints:** How a frontend application can interact with the backend to send messages, manage conversations, and perform other actions.

**Key Features:**
-   **Centralized Webhook Handling:** All incoming webhooks are processed in a single, robust module.
-   **Rich Messaging:** Full support for sending text, media (images, videos, audio, voice notes, documents), locations, contacts, stickers, and interactive messages with buttons.
-   **Product Catalogs:** Endpoints to send single products, multi-product carousels, and catalog previews.
-   **Dynamic Media Handling:** Media files are not stored on the server. Instead, metadata is saved, and files are fetched on-the-fly from WhatsApp's servers, saving disk space and simplifying management.
-   **Real-time UI Updates:** A WebSocket interface broadcasts events to connected clients for a live, responsive user experience.
-   **Comprehensive API:** A full suite of RESTful endpoints to manage the entire messaging lifecycle.

---

## 2. Webhook Implementation

The backend uses the `pywa` library to handle webhooks from Meta. All webhook logic is centralized in `app/services/whatsapp_handlers.py`.

### 2.1. Registered Handlers

The following handlers are registered to listen for events from WhatsApp:
-   `@wa_client.on_message()`: Handles all incoming message types (text, media, location, etc.).
-   `@wa_client.on_message_status()`: Handles status updates for outgoing messages (sent, delivered, read).
-   `@wa_client.on_callback_button()`: Handles user clicks on interactive reply buttons.
-   `@wa_client.on_callback_selection()`: Handles user selections from interactive lists.

### 2.2. Core Webhook Logic

When a webhook is received, the system performs the following actions:
1.  **Authentication:** Verifies the request signature to ensure it came from Meta.
2.  **Deduplication:** Checks the `message_id` to prevent processing the same event multiple times (handles Meta's webhook retries).
3.  **Contact Management:** Creates or updates the contact in the database.
4.  **Message Processing:**
    -   For media messages, saves the media metadata (e.g., WhatsApp media ID) without downloading the file.
    -   Saves the message content and details to the `messages` table.
5.  **WebSocket Broadcast:** Pushes a real-time event to connected frontend clients (e.g., `message_incoming`).
6.  **Auto-Reply:** (Optional) Triggers auto-reply logic based on message content (e.g., the `/poll` command).

---

## 3. REST API Documentation

This section details the API endpoints available for a frontend application.

**Authentication:** All endpoints require a valid authentication token (either a JWT in the `Authorization: Bearer <token>` header or a session cookie) and a `X-Tenant-Id` header.

### 3.1. Message Sending

#### Send Text Message
Send a versatile text message with an optional header, footer, interactive buttons, a URL preview, or as a reply to a previous message.

-   **Endpoint:** `POST /api/v1/send/text`
-   **Request Body (`MessageCreate`):**
    ```json
    {
      "to": "919876543210",
      "text": "Hello! Check out our website: https://example.com",
      "header": "Welcome!",
      "footer": "Powered by Celiyo",
      "buttons": [
        { "title": "Visit Us", "url": "https://example.com" },
        { "title": "Get Help", "callback_data": "HELP_CLICK" }
      ],
      "preview_url": true,
      "reply_to_message_id": "wamid.ID_OF_MESSAGE_TO_REPLY"
    }
    ```
-   **Success Response (`200 OK`):**
    ```json
    {
      "ok": true,
      "message_id": "wamid.XYZ==",
      "phone": "919876543210",
      "text": "Hello! Check out our website: https://example.com",
      "timestamp": "2025-12-09T12:00:00.000000Z"
    }
    ```

#### Send Media (Image, Video, Audio, Document)
Send a media file by providing its `media_id` (obtained from the `/upload/media` endpoint).

-   **Endpoint:** `POST /api/v1/send/media`
-   **Request Body (`MediaMessageCreate`):**
    ```json
    {
      "to": "919876543210",
      "media_id": "internal-media-uuid-from-upload",
      "media_type": "image",
      "caption": "Here is the photo you requested.",
      "reply_to_message_id": "wamid.ID_OF_MESSAGE_TO_REPLY"
    }
    ```
-   **Success Response (`200 OK`):** `{"ok": true, "message_id": "wamid.XYZ=="}`

#### Send Voice Message
Send an audio file as a voice note. The media must be an OGG file with the OPUS codec.

-   **Endpoint:** `POST /api/v1/send/voice`
-   **Request Body (`VoiceMessageCreate`):**
    ```json
    {
      "to": "919876543210",
      "media_id": "internal-media-uuid-of-voice-file",
      "reply_to_message_id": "wamid.ID_OF_MESSAGE_TO_REPLY"
    }
    ```
-   **Success Response (`200 OK`):** `{"ok": true, "message_id": "wamid.XYZ=="}`

#### Send Other Message Types
Similar `POST` endpoints are available for other message types under `/api/v1/send/`:
-   `/location` (`LocationMessageCreate`): Send a map location.
-   `/request_location` (`LocationRequestCreate`): Ask a user to share their location.
-   `/sticker` (`StickerMessageCreate`): Send a sticker.
-   `/contact` (`ContactMessageCreate`): Send a contact card.

### 3.2. Product & Catalog Messages

These endpoints require a product catalog to be set up in your Meta Commerce Manager account.

#### Send Catalog
Send a message that opens your full product catalog.

-   **Endpoint:** `POST /api/v1/send/catalog`
-   **Request Body (`CatalogMessageCreate`):**
    ```json
    {
      "to": "919876543210",
      "body": "Check out our latest collection!",
      "footer": "Shop now!",
      "thumbnail_product_sku": "SKU_FOR_THUMBNAIL"
    }
    ```
-   **Success Response (`200 OK`):** `{"ok": true, "message_id": "wamid.XYZ=="}`

#### Send Single Product
Feature a single product in a message.

-   **Endpoint:** `POST /api/v1/send/product`
-   **Request Body (`ProductMessageCreate`):**
    ```json
    {
      "to": "919876543210",
      "catalog_id": "YOUR_CATALOG_ID",
      "sku": "PRODUCT_SKU_123",
      "body": "This is our top-selling product!"
    }
    ```
-   **Success Response (`200 OK`):** `{"ok": true, "message_id": "wamid.XYZ=="}`

#### Send Multiple Products
Send a carousel of multiple products organized into sections.

-   **Endpoint:** `POST /api/v1/send/products`
-   **Request Body (`ProductsMessageCreate`):**
    ```json
    {
      "to": "919876543210",
      "catalog_id": "YOUR_CATALOG_ID",
      "body": "Explore our top picks!",
      "product_sections": [
        { "title": "Popular Items", "skus": ["SKU001", "SKU002"] },
        { "title": "New Arrivals", "skus": ["SKU003"] }
      ]
    }
    ```
-   **Success Response (`200 OK`):** `{"ok": true, "message_id": "wamid.XYZ=="}`

### 3.3. Message Interaction

#### Send Reaction
React to a message with an emoji.

-   **Endpoint:** `POST /api/v1/send/reaction`
-   **Request Body (`ReactionMessageCreate`):**
    ```json
    {
      "to": "919876543210",
      "emoji": "👍",
      "message_id": "wamid.ID_OF_MESSAGE_TO_REACT_TO"
    }
    ```
-   **Success Response (`200 OK`):** `{"ok": true, "message_id": "wamid.XYZ=="}`

#### Remove Reaction
Remove your emoji reaction from a message.

-   **Endpoint:** `DELETE /api/v1/messages/{message_id}/reaction`
-   **Success Response:** `204 No Content`

#### Mark Message as Read
Mark an incoming message as read.

-   **Endpoint:** `POST /api/v1/messages/{message_id}/read`
-   **Success Response:** `204 No Content`

#### Indicate Typing
Show a "typing..." indicator to the user.

-   **Endpoint:** `POST /api/v1/conversations/{phone}/typing`
-   **Request Body (`TypingIndicatorRequest`):**
    ```json
    { "message_id": "wamid.ID_OF_MESSAGE_BEING_REPLIED_TO" }
    ```
-   **Success Response:** `204 No Content`

### 3.4. Media Management

#### Upload Media
Upload a media file to get an internal `media_id` for use in send endpoints.

-   **Endpoint:** `POST /api/v1/upload/media`
-   **Request Body:** `multipart/form-data` with a `file` field.
-   **Success Response (`200 OK`):**
    ```json
    {
      "ok": true,
      "media_id": "a-unique-internal-uuid",
      "filename": "my_image.jpg",
      "mime_type": "image/jpeg"
    }
    ```

#### Get Media Content
Retrieve the content of a media file.

-   **Endpoint:** `GET /api/v1/media/{media_id}`
-   **Success Response:** The raw binary content of the media file (e.g., the image itself).

#### Delete Media
Delete a media file from WhatsApp's servers and the local database record.

-   **Endpoint:** `DELETE /api/v1/media/{media_id}`
-   **Success Response:** `204 No Content`

### 3.5. Conversation Management

-   **List Conversations:** `GET /api/v1/conversations`
    -   Returns a list of all conversations with a preview of the last message.
-   **Get Conversation Details:** `GET /api/v1/conversations/{phone}`
    -   Returns the complete message history for a specific phone number.
-   **Delete Conversation:** `DELETE /api/v1/conversations/{phone}`
    -   Deletes all messages associated with a specific phone number.

---

## 4. WebSocket Events

The WebSocket API at `/ws/{tenant_id}` broadcasts real-time updates to connected clients. This allows the UI to update instantly without needing to poll the API.

### Event: `message_incoming`
Sent when a new message is received from a WhatsApp user. The payload includes the full message details and contact information.

```json
{
  "event": "message_incoming",
  "data": {
    "phone": "+919876543210",
    "name": "John Doe",
    "contact": { /* ...contact details... */ },
    "message": { /* ...message details... */ }
  }
}
```

### Event: `message_outgoing`
Sent when an outgoing message is successfully sent from the backend.

```json
{
  "event": "message_outgoing",
  "data": {
    "phone": "+919876543210",
    "name": "John Doe",
    "contact": { /* ...contact details... */ },
    "message": { /* ...message details... */ }
  }
}
```

### Event: `message_status`
Sent when the delivery status of an outgoing message changes (e.g., to `delivered` or `read`).

```json
{
  "event": "message_status",
  "data": {
    "message_id": "wamid.XYZ==",
    "status": "delivered",
    "timestamp": "1733656260"
  }
}
```

### Other Events
Custom events are also broadcast for interactive elements:
-   `button_clicked`: When a user clicks an interactive button.
-   `selection_made`: When a user selects an option from a list.
-   **Listener Events (e.g., for `/poll`):**
    -   A `poll_started` event could be sent when `wa_client.listen` is called.
    -   A `poll_response` event could be sent when the user provides an answer.
    -   A `poll_ended` event could be sent on timeout or cancellation.

This real-time system ensures that a connected frontend application always has the most up-to-date information.