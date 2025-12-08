# WhatsApp Flow Builder - Frontend Integration Guide

## Table of Contents
1. [Overview](#overview)
2. [API Endpoints](#api-endpoints)
3. [Flow JSON Structure](#flow-json-structure)
4. [Creating Flows](#creating-flows)
5. [Managing Flows](#managing-flows)
6. [Flow Components Reference](#flow-components-reference)
7. [Common Patterns](#common-patterns)
8. [Error Handling](#error-handling)
9. [Best Practices](#best-practices)

---

## Overview

The Flow Builder API allows you to create, manage, and publish WhatsApp Flows through a RESTful API. Flows are interactive forms that users can fill out within WhatsApp conversations.

**Base URL:** `/api/v1/flows`

**Authentication:** Include `X-Tenant-Id` header or use JWT authentication

---

## API Endpoints

### 1. Create Flow
**POST** `/api/v1/flows/`

Create a new WhatsApp Flow.

**Request Body:**
```json
{
  "name": "Customer Support Flow",
  "description": "Flow for customer support queries",
  "flow_json": {
    "version": "3.0",
    "screens": [...]
  },
  "category": "CUSTOMER_SUPPORT",
  "version": "3.0",
  "data_api_version": "3.0",
  "endpoint_uri": "https://myapp.com/flow-endpoint",
  "tags": ["support", "customer-service"]
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "tenant_id": "your-tenant-id",
  "flow_id": "uuid-generated",
  "name": "Customer Support Flow",
  "description": "Flow for customer support queries",
  "flow_json": {...},
  "category": "CUSTOMER_SUPPORT",
  "version": "3.0",
  "status": "DRAFT",
  "is_active": true,
  "created_at": "2025-12-09T10:00:00",
  "updated_at": "2025-12-09T10:00:00"
}
```

---

### 2. List Flows
**GET** `/api/v1/flows/`

Get paginated list of flows with filters.

**Query Parameters:**
- `page` (int, default: 1) - Page number
- `page_size` (int, default: 20, max: 100) - Items per page
- `status` (string) - Filter by status: `DRAFT`, `PUBLISHED`, `DEPRECATED`
- `category` (string) - Filter by category
- `is_active` (boolean) - Filter by active status
- `search` (string) - Search by name or description

**Example:**
```
GET /api/v1/flows/?page=1&page_size=20&status=PUBLISHED&search=support
```

**Response:** `200 OK`
```json
{
  "total": 45,
  "flows": [...],
  "page": 1,
  "page_size": 20
}
```

---

### 3. Get Single Flow
**GET** `/api/v1/flows/{flow_id}`

Get a specific flow by ID.

**Response:** `200 OK`
```json
{
  "id": 1,
  "flow_id": "uuid",
  "name": "Customer Support Flow",
  ...
}
```

---

### 4. Update Flow
**PUT** `/api/v1/flows/{flow_id}`

Update an existing flow. Only provided fields will be updated.

**Request Body:**
```json
{
  "name": "Updated Flow Name",
  "flow_json": {...},
  "status": "PUBLISHED"
}
```

**Response:** `200 OK`

---

### 5. Delete Flow
**DELETE** `/api/v1/flows/{flow_id}?hard_delete=false`

Delete a flow (soft delete by default).

**Query Parameters:**
- `hard_delete` (boolean, default: false) - If true, permanently delete

**Response:** `200 OK`
```json
{
  "message": "Flow deactivated",
  "flow_id": "uuid"
}
```

---

### 6. Publish Flow
**POST** `/api/v1/flows/{flow_id}/publish`

Change flow status to PUBLISHED.

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Flow published successfully",
  "flow_id": "uuid",
  "status": "PUBLISHED"
}
```

---

### 7. Unpublish Flow
**POST** `/api/v1/flows/{flow_id}/unpublish`

Change flow status back to DRAFT.

---

### 8. Duplicate Flow
**POST** `/api/v1/flows/{flow_id}/duplicate?new_name=Flow Copy`

Create a copy of an existing flow.

**Query Parameters:**
- `new_name` (string, optional) - Name for the duplicated flow

---

### 9. Validate Flow
**POST** `/api/v1/flows/{flow_id}/validate`

Validate flow JSON structure.

**Response:** `200 OK`
```json
{
  "is_valid": true,
  "errors": [],
  "warnings": ["Flow should have at least one terminal screen"]
}
```

---

### 10. Get Flow Statistics
**GET** `/api/v1/flows/stats`

Get flow statistics for the tenant.

**Response:** `200 OK`
```json
{
  "total_flows": 45,
  "draft_flows": 20,
  "published_flows": 25,
  "active_flows": 40,
  "flows_by_category": {
    "CUSTOMER_SUPPORT": 15,
    "SIGN_UP": 10,
    "APPOINTMENT_BOOKING": 20
  }
}
```

---

## Flow JSON Structure

### Minimum Flow JSON

```json
{
  "version": "3.0",
  "screens": [
    {
      "id": "START",
      "title": "Welcome",
      "terminal": true,
      "layout": {
        "type": "SingleColumnLayout",
        "children": [
          {
            "type": "Form",
            "name": "form",
            "children": [
              {
                "type": "TextHeading",
                "text": "Welcome to our service!"
              }
            ]
          },
          {
            "type": "Footer",
            "label": "Continue",
            "on-click-action": {
              "name": "complete",
              "payload": {}
            }
          }
        ]
      }
    }
  ]
}
```

### Flow JSON with Multiple Screens

```json
{
  "version": "3.0",
  "screens": [
    {
      "id": "START",
      "title": "Personal Info",
      "data": [
        {
          "key": "user_name",
          "example": "John Doe"
        }
      ],
      "layout": {
        "type": "SingleColumnLayout",
        "children": [
          {
            "type": "Form",
            "name": "form",
            "children": [
              {
                "type": "TextHeading",
                "text": "Enter Your Details"
              },
              {
                "type": "TextInput",
                "name": "name",
                "label": "Full Name",
                "required": true,
                "input-type": "text"
              },
              {
                "type": "TextInput",
                "name": "email",
                "label": "Email",
                "required": true,
                "input-type": "email"
              }
            ]
          },
          {
            "type": "Footer",
            "label": "Next",
            "on-click-action": {
              "name": "navigate",
              "next": {
                "name": "CONFIRM"
              },
              "payload": {
                "name": "${form.name}",
                "email": "${form.email}"
              }
            }
          }
        ]
      }
    },
    {
      "id": "CONFIRM",
      "title": "Confirmation",
      "terminal": true,
      "data": [
        {
          "key": "name",
          "example": "John Doe"
        },
        {
          "key": "email",
          "example": "john@example.com"
        }
      ],
      "layout": {
        "type": "SingleColumnLayout",
        "children": [
          {
            "type": "Form",
            "name": "form",
            "children": [
              {
                "type": "TextHeading",
                "text": "Confirm Your Details"
              },
              {
                "type": "TextBody",
                "text": "Name: ${data.name}"
              },
              {
                "type": "TextBody",
                "text": "Email: ${data.email}"
              }
            ]
          },
          {
            "type": "Footer",
            "label": "Submit",
            "on-click-action": {
              "name": "complete",
              "payload": {
                "name": "${data.name}",
                "email": "${data.email}"
              }
            }
          }
        ]
      }
    }
  ]
}
```

---

## Creating Flows

### Step 1: Build Flow JSON in Frontend

Your frontend UI builder should construct a valid Flow JSON object following WhatsApp's specification.

**Frontend Flow Builder Components:**
1. **Screen Manager** - Add/remove/reorder screens
2. **Component Palette** - Drag-and-drop components
3. **Property Editor** - Edit component properties
4. **JSON Preview** - Show live JSON
5. **Validator** - Real-time validation

### Step 2: Send to API

```javascript
async function createFlow(flowData) {
  const response = await fetch('/api/v1/flows/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-Id': 'your-tenant-id'
    },
    body: JSON.stringify({
      name: flowData.name,
      description: flowData.description,
      flow_json: flowData.flowJson, // Your constructed JSON
      category: flowData.category,
      version: "3.0",
      endpoint_uri: flowData.endpointUri,
      tags: flowData.tags
    })
  });

  if (!response.ok) {
    throw new Error('Failed to create flow');
  }

  return await response.json();
}
```

### Step 3: Validate Before Publishing

```javascript
async function validateAndPublish(flowId) {
  // First validate
  const validationResponse = await fetch(`/api/v1/flows/${flowId}/validate`, {
    method: 'POST',
    headers: {
      'X-Tenant-Id': 'your-tenant-id'
    }
  });

  const validation = await validationResponse.json();

  if (!validation.is_valid) {
    console.error('Validation errors:', validation.errors);
    return false;
  }

  // Show warnings to user
  if (validation.warnings.length > 0) {
    console.warn('Warnings:', validation.warnings);
  }

  // Publish if valid
  const publishResponse = await fetch(`/api/v1/flows/${flowId}/publish`, {
    method: 'POST',
    headers: {
      'X-Tenant-Id': 'your-tenant-id'
    }
  });

  return await publishResponse.json();
}
```

---

## Managing Flows

### Loading Flows for Editing

```javascript
async function loadFlow(flowId) {
  const response = await fetch(`/api/v1/flows/${flowId}`, {
    headers: {
      'X-Tenant-Id': 'your-tenant-id'
    }
  });

  const flow = await response.json();

  // Parse flow_json and populate your UI builder
  return {
    id: flow.id,
    flowId: flow.flow_id,
    name: flow.name,
    description: flow.description,
    flowJson: flow.flow_json, // Parse this into your builder
    status: flow.status,
    category: flow.category
  };
}
```

### Updating Flow

```javascript
async function updateFlow(flowId, updates) {
  const response = await fetch(`/api/v1/flows/${flowId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-Id': 'your-tenant-id'
    },
    body: JSON.stringify(updates)
  });

  return await response.json();
}

// Example: Update only the flow JSON
await updateFlow('flow-uuid', {
  flow_json: updatedFlowJson
});

// Example: Update name and status
await updateFlow('flow-uuid', {
  name: 'New Flow Name',
  status: 'PUBLISHED'
});
```

### Autosave Implementation

```javascript
let autosaveTimer;

function setupAutosave(flowId) {
  function scheduleAutosave(flowJson) {
    clearTimeout(autosaveTimer);
    autosaveTimer = setTimeout(async () => {
      await updateFlow(flowId, { flow_json: flowJson });
      console.log('Flow autosaved');
    }, 2000); // Save 2 seconds after last change
  }

  return scheduleAutosave;
}

// Usage in your UI builder
const autosave = setupAutosave('flow-uuid');

// Call this whenever user makes changes
function onFlowJsonChange(newFlowJson) {
  autosave(newFlowJson);
}
```

---

## Flow Components Reference

### Text Components

#### TextHeading
```json
{
  "type": "TextHeading",
  "text": "Welcome",
  "visible": true
}
```

#### TextSubheading
```json
{
  "type": "TextSubheading",
  "text": "Please fill out the form",
  "visible": true
}
```

#### TextBody
```json
{
  "type": "TextBody",
  "text": "This is body text",
  "font-weight": "bold",
  "strikethrough": false,
  "visible": true
}
```

#### TextCaption
```json
{
  "type": "TextCaption",
  "text": "Small caption text",
  "font-weight": "italic",
  "visible": true
}
```

### Input Components

#### TextInput
```json
{
  "type": "TextInput",
  "name": "email",
  "label": "Email Address",
  "input-type": "email",
  "required": true,
  "min-chars": 5,
  "max-chars": 100,
  "helper-text": "Enter your email",
  "enabled": true,
  "visible": true
}
```

**Input Types:** `text`, `number`, `email`, `password`, `passcode`, `phone`

#### TextArea
```json
{
  "type": "TextArea",
  "name": "message",
  "label": "Your Message",
  "required": true,
  "max-length": 500,
  "helper-text": "Enter your message",
  "enabled": true,
  "visible": true
}
```

#### CheckboxGroup
```json
{
  "type": "CheckboxGroup",
  "name": "interests",
  "label": "Select Your Interests",
  "data-source": [
    {"id": "1", "title": "Sports"},
    {"id": "2", "title": "Music"},
    {"id": "3", "title": "Reading"}
  ],
  "min-selected-items": 1,
  "max-selected-items": 3,
  "required": true
}
```

#### RadioButtonsGroup
```json
{
  "type": "RadioButtonsGroup",
  "name": "gender",
  "label": "Gender",
  "data-source": [
    {"id": "male", "title": "Male"},
    {"id": "female", "title": "Female"},
    {"id": "other", "title": "Other"}
  ],
  "required": true
}
```

#### Dropdown
```json
{
  "type": "Dropdown",
  "name": "country",
  "label": "Select Country",
  "data-source": [
    {"id": "us", "title": "United States"},
    {"id": "uk", "title": "United Kingdom"},
    {"id": "in", "title": "India"}
  ],
  "required": true
}
```

#### DatePicker
```json
{
  "type": "DatePicker",
  "name": "appointment_date",
  "label": "Select Date",
  "min-date": "2025-01-01",
  "max-date": "2025-12-31",
  "required": true,
  "helper-text": "Choose your appointment date"
}
```

#### OptIn
```json
{
  "type": "OptIn",
  "name": "terms_accepted",
  "label": "I agree to terms and conditions",
  "required": true
}
```

### Layout Components

#### Footer
```json
{
  "type": "Footer",
  "label": "Continue",
  "on-click-action": {
    "name": "navigate",
    "next": {"name": "NEXT_SCREEN"},
    "payload": {}
  }
}
```

#### Image
```json
{
  "type": "Image",
  "src": "base64-encoded-image-data",
  "width": 300,
  "height": 200,
  "scale-type": "contain",
  "aspect-ratio": 1.5,
  "alt-text": "Product image"
}
```

---

## Common Patterns

### Pattern 1: Multi-Step Form

```json
{
  "version": "3.0",
  "screens": [
    {
      "id": "STEP_1",
      "title": "Step 1: Personal Info",
      "layout": {
        "type": "SingleColumnLayout",
        "children": [
          {
            "type": "Form",
            "name": "form",
            "children": [
              {"type": "TextInput", "name": "name", "label": "Name", "required": true},
              {"type": "TextInput", "name": "email", "label": "Email", "input-type": "email", "required": true}
            ]
          },
          {
            "type": "Footer",
            "label": "Next",
            "on-click-action": {
              "name": "navigate",
              "next": {"name": "STEP_2"},
              "payload": {"name": "${form.name}", "email": "${form.email}"}
            }
          }
        ]
      }
    },
    {
      "id": "STEP_2",
      "title": "Step 2: Preferences",
      "terminal": true,
      "layout": {
        "type": "SingleColumnLayout",
        "children": [
          {
            "type": "Form",
            "name": "form",
            "children": [
              {
                "type": "CheckboxGroup",
                "name": "interests",
                "label": "Interests",
                "data-source": [
                  {"id": "1", "title": "Sports"},
                  {"id": "2", "title": "Music"}
                ]
              }
            ]
          },
          {
            "type": "Footer",
            "label": "Submit",
            "on-click-action": {
              "name": "complete",
              "payload": {"interests": "${form.interests}"}
            }
          }
        ]
      }
    }
  ]
}
```

### Pattern 2: Conditional Display

Use screen data to show/hide components:

```json
{
  "id": "CONDITIONAL_SCREEN",
  "data": [
    {"key": "show_email", "example": true}
  ],
  "layout": {
    "type": "SingleColumnLayout",
    "children": [
      {
        "type": "Form",
        "name": "form",
        "children": [
          {
            "type": "OptIn",
            "name": "email_opt_in",
            "label": "Want to receive emails?"
          },
          {
            "type": "TextInput",
            "name": "email",
            "label": "Email",
            "visible": "${data.show_email}"
          }
        ]
      }
    ]
  }
}
```

### Pattern 3: Dynamic Data Source

```json
{
  "id": "DYNAMIC_SCREEN",
  "data": [
    {
      "key": "product_options",
      "example": [
        {"id": "1", "title": "Product A"},
        {"id": "2", "title": "Product B"}
      ]
    }
  ],
  "layout": {
    "type": "SingleColumnLayout",
    "children": [
      {
        "type": "Form",
        "name": "form",
        "children": [
          {
            "type": "RadioButtonsGroup",
            "name": "product",
            "label": "Select Product",
            "data-source": "${data.product_options}"
          }
        ]
      }
    ]
  }
}
```

---

## Error Handling

### Validation Errors

The API returns validation errors in a structured format:

```json
{
  "is_valid": false,
  "errors": [
    "Flow JSON must have a 'version' field",
    "Screen 'START' missing 'layout' field",
    "Terminal screen 'END' must have a Footer component"
  ],
  "warnings": [
    "Flow should have at least one terminal screen"
  ]
}
```

**Display these errors in your UI:**
- Show errors as blocking issues (red)
- Show warnings as recommendations (yellow)
- Prevent publishing if errors exist

### HTTP Error Codes

- `400 Bad Request` - Invalid input data
- `404 Not Found` - Flow not found
- `422 Unprocessable Entity` - Validation failed
- `500 Internal Server Error` - Server error

```javascript
async function handleFlowOperation(operation) {
  try {
    const result = await operation();
    return { success: true, data: result };
  } catch (error) {
    if (error.status === 404) {
      return { success: false, error: 'Flow not found' };
    } else if (error.status === 400) {
      return { success: false, error: 'Invalid flow data' };
    } else {
      return { success: false, error: 'An error occurred' };
    }
  }
}
```

---

## Best Practices

### 1. JSON Structure
- Always validate JSON before sending
- Use proper nesting for components
- Include all required fields
- Test with WhatsApp's Flow JSON validator

### 2. Performance
- Implement autosave to prevent data loss
- Cache flow list for faster navigation
- Use pagination for large flow lists
- Debounce search inputs

### 3. User Experience
- Show real-time validation feedback
- Provide JSON preview alongside UI builder
- Allow import/export of Flow JSON
- Show flow statistics dashboard

### 4. State Management
- Track unsaved changes
- Implement undo/redo functionality
- Handle concurrent editing gracefully
- Sync status across tabs

### 5. Security
- Validate all user inputs
- Sanitize flow names and descriptions
- Use tenant isolation properly
- Don't expose internal IDs in URLs

### 6. Categories
Use standard WhatsApp Flow categories:
- `SIGN_UP` - User registration
- `SIGN_IN` - User login
- `APPOINTMENT_BOOKING` - Scheduling
- `LEAD_GENERATION` - Lead capture
- `CONTACT_US` - Contact forms
- `CUSTOMER_SUPPORT` - Support tickets
- `SURVEY` - Surveys and feedback
- `OTHER` - Custom flows

---

## Complete Example: Frontend Implementation

```javascript
class FlowBuilder {
  constructor(apiBaseUrl, tenantId) {
    this.apiBaseUrl = apiBaseUrl;
    this.tenantId = tenantId;
  }

  async createFlow(flowData) {
    const response = await fetch(`${this.apiBaseUrl}/flows/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-Id': this.tenantId
      },
      body: JSON.stringify(flowData)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create flow');
    }

    return await response.json();
  }

  async listFlows(filters = {}) {
    const params = new URLSearchParams(filters);
    const response = await fetch(`${this.apiBaseUrl}/flows/?${params}`, {
      headers: { 'X-Tenant-Id': this.tenantId }
    });

    return await response.json();
  }

  async updateFlow(flowId, updates) {
    const response = await fetch(`${this.apiBaseUrl}/flows/${flowId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-Id': this.tenantId
      },
      body: JSON.stringify(updates)
    });

    return await response.json();
  }

  async publishFlow(flowId) {
    // Validate first
    const validation = await this.validateFlow(flowId);

    if (!validation.is_valid) {
      throw new Error(`Validation failed: ${validation.errors.join(', ')}`);
    }

    // Publish
    const response = await fetch(`${this.apiBaseUrl}/flows/${flowId}/publish`, {
      method: 'POST',
      headers: { 'X-Tenant-Id': this.tenantId }
    });

    return await response.json();
  }

  async validateFlow(flowId) {
    const response = await fetch(`${this.apiBaseUrl}/flows/${flowId}/validate`, {
      method: 'POST',
      headers: { 'X-Tenant-Id': this.tenantId }
    });

    return await response.json();
  }
}

// Usage
const flowBuilder = new FlowBuilder('/api/v1', 'my-tenant-id');

// Create a flow
const newFlow = await flowBuilder.createFlow({
  name: 'My First Flow',
  description: 'A simple flow',
  flow_json: { /* your flow JSON */ },
  category: 'SIGN_UP',
  version: '3.0'
});

// List flows
const flows = await flowBuilder.listFlows({
  page: 1,
  page_size: 20,
  status: 'DRAFT'
});

// Publish
await flowBuilder.publishFlow(newFlow.flow_id);
```

---

## Support

For questions or issues:
1. Check the validation endpoint for errors
2. Refer to WhatsApp Flow JSON specification
3. Review API error messages
4. Contact backend team for API issues

---

**Last Updated:** 2025-12-09
**API Version:** 1.0
**Flow JSON Version:** 3.0
