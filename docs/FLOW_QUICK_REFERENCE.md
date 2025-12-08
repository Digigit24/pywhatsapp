# Flow Builder - Quick Reference Card

## 🚀 Setup (5 Minutes)

### 1. Run Migration
```bash
psql -U postgres -d whatspy_db -f migrations/create_flows_table.sql
```

### 2. Verify
```sql
SELECT COUNT(*) FROM flows;  -- Should return 0
```

### 3. Test API
```
http://localhost:8002/docs
```
Look for "Flows" section

---

## 📡 API Endpoints Cheat Sheet

| What | Method | Endpoint |
|------|--------|----------|
| Create | `POST` | `/api/v1/flows/` |
| List | `GET` | `/api/v1/flows/?page=1&page_size=20` |
| Get One | `GET` | `/api/v1/flows/{flow_id}` |
| Update | `PUT` | `/api/v1/flows/{flow_id}` |
| Delete | `DELETE` | `/api/v1/flows/{flow_id}` |
| Publish | `POST` | `/api/v1/flows/{flow_id}/publish` |
| Validate | `POST` | `/api/v1/flows/{flow_id}/validate` |
| Stats | `GET` | `/api/v1/flows/stats` |

---

## 🎨 Minimum Flow JSON

```json
{
  "version": "3.0",
  "screens": [{
    "id": "START",
    "title": "Welcome",
    "terminal": true,
    "layout": {
      "type": "SingleColumnLayout",
      "children": [
        {
          "type": "Form",
          "name": "form",
          "children": [{"type": "TextHeading", "text": "Hello!"}]
        },
        {
          "type": "Footer",
          "label": "Continue",
          "on-click-action": {"name": "complete", "payload": {}}
        }
      ]
    }
  }]
}
```

---

## 🧩 Common Components

### TextInput
```json
{
  "type": "TextInput",
  "name": "email",
  "label": "Email",
  "input-type": "email",
  "required": true
}
```

### RadioButtonsGroup
```json
{
  "type": "RadioButtonsGroup",
  "name": "choice",
  "label": "Choose One",
  "data-source": [
    {"id": "1", "title": "Option 1"},
    {"id": "2", "title": "Option 2"}
  ],
  "required": true
}
```

### Footer (Required on terminal screens)
```json
{
  "type": "Footer",
  "label": "Submit",
  "on-click-action": {
    "name": "complete",
    "payload": {}
  }
}
```

---

## 🔍 Query Examples

### List Published Flows
```bash
GET /api/v1/flows/?status=PUBLISHED
```

### Search by Name
```bash
GET /api/v1/flows/?search=support
```

### Filter by Category
```bash
GET /api/v1/flows/?category=CUSTOMER_SUPPORT
```

### Combine Filters
```bash
GET /api/v1/flows/?status=PUBLISHED&category=SIGN_UP&page=1&page_size=10
```

---

## 💾 SQL Quick Commands

### View All Flows
```sql
SELECT flow_id, name, status, category, created_at
FROM flows
WHERE tenant_id = 'default'
ORDER BY created_at DESC;
```

### Count by Status
```sql
SELECT status, COUNT(*)
FROM flows
GROUP BY status;
```

### Search Flow JSON
```sql
SELECT flow_id, name
FROM flows
WHERE flow_json->>'version' = '3.0';
```

### Delete Old Drafts
```sql
DELETE FROM flows
WHERE status = 'DRAFT'
  AND created_at < NOW() - INTERVAL '30 days';
```

---

## ✅ Validation Checklist

Before publishing, ensure:
- [ ] Flow has `version` field
- [ ] Flow has at least one screen
- [ ] All screen IDs are unique
- [ ] Each screen has `layout`
- [ ] Terminal screens have `Footer`
- [ ] All required fields are present
- [ ] JSON is properly formatted

---

## 🏷️ Flow Categories

- `SIGN_UP` - Registration
- `SIGN_IN` - Login
- `APPOINTMENT_BOOKING` - Scheduling
- `LEAD_GENERATION` - Lead capture
- `CONTACT_US` - Contact forms
- `CUSTOMER_SUPPORT` - Support
- `SURVEY` - Surveys
- `OTHER` - Custom

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| 404 on `/flows` | Check router registered, restart server |
| Table not found | Run migration SQL |
| Validation fails | Use `/validate` endpoint for details |
| Can't publish | Ensure flow has terminal screen with Footer |

---

## 📦 What Frontend Needs

1. **Create Flow UI**
   - Name, description, category inputs
   - Visual Flow JSON builder
   - Save button → `POST /api/v1/flows/`

2. **List Flows UI**
   - Table with pagination
   - Search bar
   - Filter dropdowns (status, category)
   - Fetch → `GET /api/v1/flows/`

3. **Edit Flow UI**
   - Load flow → `GET /api/v1/flows/{id}`
   - Visual editor for flow_json
   - Autosave → `PUT /api/v1/flows/{id}`

4. **Publish Flow**
   - Validate → `POST /api/v1/flows/{id}/validate`
   - Publish → `POST /api/v1/flows/{id}/publish`

---

## 🎯 Frontend JavaScript Template

```javascript
class FlowAPI {
  constructor(baseUrl, tenantId) {
    this.baseUrl = baseUrl;
    this.tenantId = tenantId;
  }

  headers() {
    return {
      'Content-Type': 'application/json',
      'X-Tenant-Id': this.tenantId
    };
  }

  async create(data) {
    const res = await fetch(`${this.baseUrl}/flows/`, {
      method: 'POST',
      headers: this.headers(),
      body: JSON.stringify(data)
    });
    return res.json();
  }

  async list(params = {}) {
    const query = new URLSearchParams(params);
    const res = await fetch(`${this.baseUrl}/flows/?${query}`, {
      headers: this.headers()
    });
    return res.json();
  }

  async get(flowId) {
    const res = await fetch(`${this.baseUrl}/flows/${flowId}`, {
      headers: this.headers()
    });
    return res.json();
  }

  async update(flowId, data) {
    const res = await fetch(`${this.baseUrl}/flows/${flowId}`, {
      method: 'PUT',
      headers: this.headers(),
      body: JSON.stringify(data)
    });
    return res.json();
  }

  async publish(flowId) {
    const res = await fetch(`${this.baseUrl}/flows/${flowId}/publish`, {
      method: 'POST',
      headers: this.headers()
    });
    return res.json();
  }

  async validate(flowId) {
    const res = await fetch(`${this.baseUrl}/flows/${flowId}/validate`, {
      method: 'POST',
      headers: this.headers()
    });
    return res.json();
  }
}

// Usage
const api = new FlowAPI('/api/v1', 'default');
const flows = await api.list({ page: 1, page_size: 20 });
```

---

## 📊 Response Formats

### Create/Update Response
```json
{
  "id": 1,
  "flow_id": "uuid",
  "name": "Flow Name",
  "status": "DRAFT",
  "created_at": "2025-12-09T10:00:00",
  ...
}
```

### List Response
```json
{
  "total": 45,
  "flows": [...],
  "page": 1,
  "page_size": 20
}
```

### Validation Response
```json
{
  "is_valid": true,
  "errors": [],
  "warnings": ["Warning message"]
}
```

---

## 🎓 Learning Resources

1. **Full Guide:** `docs/FLOW_API_FRONTEND_GUIDE.md`
2. **Summary:** `docs/FLOW_BUILDER_SUMMARY.md`
3. **Migration:** `migrations/README.md`
4. **API Docs:** `http://localhost:8002/docs`

---

**Quick Reference v1.0** | Created: 2025-12-09
