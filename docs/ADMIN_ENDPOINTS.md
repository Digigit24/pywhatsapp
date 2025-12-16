# Admin Endpoints - Tenant Configuration Management

## ⚠️ Warning

These are **ADMIN-ONLY** endpoints with dangerous operations. Use with caution!

All endpoints require JWT authentication.

---

## 📋 Table of Contents

1. [Get All Configurations](#1-get-all-configurations)
2. [Get Configuration Statistics](#2-get-configuration-statistics)
3. [Delete All Configurations](#3-delete-all-configurations)
4. [Delete Specific Tenant Configuration](#4-delete-specific-tenant-configuration)

---

## 1. Get All Configurations

**Endpoint:** `GET /api/v1/tenant/admin/configs/all`

**Description:** Retrieve all tenant configurations across the entire system. Sensitive data is masked.

**Authentication:** Required (JWT Bearer token)

**Query Parameters:**
- `skip` (optional, default: 0) - Number of records to skip
- `limit` (optional, default: 100) - Maximum records to return

### Request Example

```bash
curl -X GET "http://localhost:8002/api/v1/tenant/admin/configs/all?skip=0&limit=50" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Response Example

```json
{
  "total": 125,
  "returned": 50,
  "configs": [
    {
      "id": 1,
      "tenant_id": "tenant-uuid-1",
      "user_id": "user-123",
      "waba_id": "123456789",
      "phone_number_id": "987654321",
      "access_token": "***xyz789",
      "fb_app_id": "app-id-123",
      "fb_app_secret": "***abc456",
      "callback_url": "https://domain.com/webhook",
      "redirect_url": "https://domain.com/oauth",
      "verify_token": "verify123",
      "is_active": true,
      "onboarding_completed": true,
      "onboarded_at": "2025-12-11T10:30:00Z",
      "created_at": "2025-12-11T10:30:00Z",
      "updated_at": "2025-12-11T10:30:00Z"
    },
    // ... more configs
  ]
}
```

---

## 2. Get Configuration Statistics

**Endpoint:** `GET /api/v1/tenant/admin/configs/stats`

**Description:** Get summary statistics about tenant configurations.

**Authentication:** Required (JWT Bearer token)

### Request Example

```bash
curl -X GET "http://localhost:8002/api/v1/tenant/admin/configs/stats" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Response Example

```json
{
  "total_configs": 125,
  "active_configs": 110,
  "inactive_configs": 15,
  "onboarded_configs": 105,
  "pending_onboarding": 20
}
```

**Response Fields:**
- `total_configs` - Total number of configurations
- `active_configs` - Configurations with `is_active = true`
- `inactive_configs` - Configurations with `is_active = false`
- `onboarded_configs` - Configurations with `onboarding_completed = true`
- `pending_onboarding` - Configurations not yet onboarded

---

## 3. Delete All Configurations

**Endpoint:** `DELETE /api/v1/tenant/admin/configs/delete-all`

**Description:** ⚠️ **DANGER!** Delete ALL tenant configurations from the database. This is **irreversible**.

**Authentication:** Required (JWT Bearer token)

**Safety Requirement:** Must provide exact confirmation string

**Query Parameters:**
- `confirmation` (required) - Must be exactly: `DELETE_ALL_CONFIGS_PERMANENTLY`

### Request Example

```bash
curl -X DELETE "http://localhost:8002/api/v1/tenant/admin/configs/delete-all?confirmation=DELETE_ALL_CONFIGS_PERMANENTLY" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Success Response

```json
{
  "success": true,
  "message": "Successfully deleted all tenant configurations",
  "deleted_count": 125,
  "warning": "This action cannot be undone"
}
```

### Error Response (Invalid Confirmation)

```json
{
  "detail": "Invalid confirmation. To delete all configs, set confirmation='DELETE_ALL_CONFIGS_PERMANENTLY'"
}
```

### No Configs to Delete

```json
{
  "success": true,
  "message": "No configurations to delete",
  "deleted_count": 0
}
```

---

## 4. Delete Specific Tenant Configuration

**Endpoint:** `DELETE /api/v1/tenant/admin/configs/delete-tenant/{target_tenant_id}`

**Description:** Delete configuration for a specific tenant (admin override).

**Authentication:** Required (JWT Bearer token)

**Path Parameters:**
- `target_tenant_id` (required) - The tenant ID whose config should be deleted

### Request Example

```bash
curl -X DELETE "http://localhost:8002/api/v1/tenant/admin/configs/delete-tenant/tenant-uuid-123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Success Response

```json
{
  "success": true,
  "message": "Successfully deleted configuration for tenant tenant-uuid-123",
  "deleted_config": {
    "id": 5,
    "tenant_id": "tenant-uuid-123",
    "waba_id": "123456789"
  }
}
```

### Error Response (Not Found)

```json
{
  "detail": "Configuration not found for tenant: tenant-uuid-123"
}
```

---

## 🧪 Testing with cURL

### Complete Test Script

```bash
#!/bin/bash

# Set your JWT token
JWT_TOKEN="your_jwt_token_here"
API_URL="http://localhost:8002/api/v1/tenant"

echo "=== Tenant Config Admin Endpoints Test ==="
echo ""

# 1. Get statistics
echo "1. Getting statistics..."
curl -s -X GET "$API_URL/admin/configs/stats" \
  -H "Authorization: Bearer $JWT_TOKEN" | jq .
echo ""

# 2. Get all configs (first 10)
echo "2. Getting all configs (limit 10)..."
curl -s -X GET "$API_URL/admin/configs/all?limit=10" \
  -H "Authorization: Bearer $JWT_TOKEN" | jq .
echo ""

# 3. Delete specific tenant config
echo "3. Deleting specific tenant config..."
TENANT_TO_DELETE="test-tenant-id"
curl -s -X DELETE "$API_URL/admin/configs/delete-tenant/$TENANT_TO_DELETE" \
  -H "Authorization: Bearer $JWT_TOKEN" | jq .
echo ""

# 4. Delete all configs (DANGEROUS - commented out by default)
# echo "4. Deleting ALL configs (DANGER!)..."
# curl -s -X DELETE "$API_URL/admin/configs/delete-all?confirmation=DELETE_ALL_CONFIGS_PERMANENTLY" \
#   -H "Authorization: Bearer $JWT_TOKEN" | jq .
# echo ""

echo "=== Test Complete ==="
```

---

## 🔒 Security Considerations

### 1. Authentication Required

All admin endpoints require valid JWT authentication:

```javascript
const response = await fetch('/api/v1/tenant/admin/configs/stats', {
  headers: {
    'Authorization': `Bearer ${jwtToken}`
  }
});
```

### 2. Admin-Only Access

**TODO:** Consider adding an admin role check:

```python
def require_admin_role(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(403, "Admin access required")
    return current_user

@router.delete("/admin/configs/delete-all")
async def admin_delete_all(
    current_user: dict = Depends(require_admin_role),  # Add admin check
    # ...
):
    pass
```

### 3. Audit Logging

Consider logging all admin operations:

```python
import logging

logger = logging.getLogger(__name__)

@router.delete("/admin/configs/delete-all")
async def admin_delete_all(...):
    logger.warning(
        f"ADMIN ACTION: User {current_user['user_id']} deleted {count_before} configs"
    )
```

### 4. Rate Limiting

Consider rate limiting admin endpoints to prevent abuse.

---

## 🚨 Dangerous Operations Checklist

Before running `delete-all`:

- [ ] Have you backed up the database?
- [ ] Is this a development/test environment?
- [ ] Have you confirmed with stakeholders?
- [ ] Do you have a rollback plan?
- [ ] Have you tested the restore process?

### Backup Before Delete

```bash
# Backup tenant_configs table
pg_dump -h your-host -U your-user -d whatspy_db -t tenant_configs > tenant_configs_backup_$(date +%Y%m%d_%H%M%S).sql

# Restore if needed
psql -h your-host -U your-user -d whatspy_db < tenant_configs_backup_20251211_103000.sql
```

---

## 📊 Frontend Admin Dashboard Example

### React Component for Admin Management

```jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8002/api/v1/tenant';

function AdminTenantConfigDashboard() {
  const [stats, setStats] = useState(null);
  const [configs, setConfigs] = useState([]);
  const [loading, setLoading] = useState(false);

  const jwtToken = localStorage.getItem('jwt_token');

  // Fetch statistics
  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_URL}/admin/configs/stats`, {
        headers: { 'Authorization': `Bearer ${jwtToken}` }
      });
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  // Fetch all configs
  const fetchConfigs = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/admin/configs/all?limit=100`, {
        headers: { 'Authorization': `Bearer ${jwtToken}` }
      });
      setConfigs(response.data.configs);
    } catch (error) {
      console.error('Error fetching configs:', error);
    } finally {
      setLoading(false);
    }
  };

  // Delete specific tenant config
  const deleteTenantConfig = async (tenantId) => {
    if (!window.confirm(`Delete config for tenant ${tenantId}?`)) return;

    try {
      await axios.delete(`${API_URL}/admin/configs/delete-tenant/${tenantId}`, {
        headers: { 'Authorization': `Bearer ${jwtToken}` }
      });
      alert('Config deleted successfully');
      fetchConfigs(); // Refresh list
    } catch (error) {
      alert('Error deleting config: ' + error.response?.data?.detail);
    }
  };

  // Delete all configs (DANGEROUS)
  const deleteAllConfigs = async () => {
    const confirmation = window.prompt(
      'This will DELETE ALL configurations! Type "DELETE_ALL_CONFIGS_PERMANENTLY" to confirm:'
    );

    if (confirmation !== 'DELETE_ALL_CONFIGS_PERMANENTLY') {
      alert('Cancelled or invalid confirmation');
      return;
    }

    try {
      const response = await axios.delete(
        `${API_URL}/admin/configs/delete-all?confirmation=DELETE_ALL_CONFIGS_PERMANENTLY`,
        {
          headers: { 'Authorization': `Bearer ${jwtToken}` }
        }
      );
      alert(`Deleted ${response.data.deleted_count} configurations`);
      fetchStats();
      fetchConfigs();
    } catch (error) {
      alert('Error: ' + error.response?.data?.detail);
    }
  };

  useEffect(() => {
    fetchStats();
    fetchConfigs();
  }, []);

  return (
    <div style={{ padding: '20px' }}>
      <h1>Tenant Configuration Admin</h1>

      {/* Statistics */}
      {stats && (
        <div style={{ marginBottom: '30px', padding: '20px', background: '#f5f5f5', borderRadius: '8px' }}>
          <h2>Statistics</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '15px' }}>
            <div><strong>Total:</strong> {stats.total_configs}</div>
            <div><strong>Active:</strong> {stats.active_configs}</div>
            <div><strong>Inactive:</strong> {stats.inactive_configs}</div>
            <div><strong>Onboarded:</strong> {stats.onboarded_configs}</div>
            <div><strong>Pending:</strong> {stats.pending_onboarding}</div>
          </div>
        </div>
      )}

      {/* Dangerous Actions */}
      <div style={{ marginBottom: '30px' }}>
        <button
          onClick={deleteAllConfigs}
          style={{
            padding: '10px 20px',
            backgroundColor: '#d9534f',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          ⚠️ Delete All Configs
        </button>
      </div>

      {/* Configs List */}
      <h2>All Configurations ({configs.length})</h2>
      {loading ? (
        <p>Loading...</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ backgroundColor: '#f0f0f0' }}>
              <th style={{ padding: '10px', border: '1px solid #ddd' }}>Tenant ID</th>
              <th style={{ padding: '10px', border: '1px solid #ddd' }}>WABA ID</th>
              <th style={{ padding: '10px', border: '1px solid #ddd' }}>Phone ID</th>
              <th style={{ padding: '10px', border: '1px solid #ddd' }}>Status</th>
              <th style={{ padding: '10px', border: '1px solid #ddd' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {configs.map(config => (
              <tr key={config.id}>
                <td style={{ padding: '10px', border: '1px solid #ddd' }}>{config.tenant_id}</td>
                <td style={{ padding: '10px', border: '1px solid #ddd' }}>{config.waba_id}</td>
                <td style={{ padding: '10px', border: '1px solid #ddd' }}>{config.phone_number_id}</td>
                <td style={{ padding: '10px', border: '1px solid #ddd' }}>
                  {config.is_active ? '✅ Active' : '❌ Inactive'}
                  {config.onboarding_completed && ' | 🔗 Onboarded'}
                </td>
                <td style={{ padding: '10px', border: '1px solid #ddd' }}>
                  <button
                    onClick={() => deleteTenantConfig(config.tenant_id)}
                    style={{
                      padding: '5px 10px',
                      backgroundColor: '#f44336',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default AdminTenantConfigDashboard;
```

---

## 🔧 Python Script for Admin Operations

```python
#!/usr/bin/env python3
"""
Admin script for managing tenant configurations.
"""
import requests
import sys

API_URL = "http://localhost:8002/api/v1/tenant"
JWT_TOKEN = "your_jwt_token_here"

headers = {
    "Authorization": f"Bearer {JWT_TOKEN}"
}

def get_stats():
    """Get configuration statistics"""
    response = requests.get(f"{API_URL}/admin/configs/stats", headers=headers)
    response.raise_for_status()
    stats = response.json()

    print("=== Configuration Statistics ===")
    print(f"Total configs: {stats['total_configs']}")
    print(f"Active: {stats['active_configs']}")
    print(f"Inactive: {stats['inactive_configs']}")
    print(f"Onboarded: {stats['onboarded_configs']}")
    print(f"Pending: {stats['pending_onboarding']}")

def delete_tenant(tenant_id):
    """Delete specific tenant configuration"""
    response = requests.delete(
        f"{API_URL}/admin/configs/delete-tenant/{tenant_id}",
        headers=headers
    )
    response.raise_for_status()
    result = response.json()
    print(f"✅ {result['message']}")

def delete_all():
    """Delete all configurations (DANGEROUS!)"""
    confirm = input("Type 'DELETE_ALL_CONFIGS_PERMANENTLY' to confirm: ")

    if confirm != "DELETE_ALL_CONFIGS_PERMANENTLY":
        print("❌ Cancelled")
        return

    response = requests.delete(
        f"{API_URL}/admin/configs/delete-all",
        params={"confirmation": "DELETE_ALL_CONFIGS_PERMANENTLY"},
        headers=headers
    )
    response.raise_for_status()
    result = response.json()
    print(f"✅ {result['message']}")
    print(f"Deleted {result['deleted_count']} configurations")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python admin_script.py [stats|delete-tenant|delete-all]")
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "stats":
            get_stats()
        elif command == "delete-tenant":
            if len(sys.argv) < 3:
                print("Usage: python admin_script.py delete-tenant <tenant_id>")
                sys.exit(1)
            delete_tenant(sys.argv[2])
        elif command == "delete-all":
            delete_all()
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error: {e.response.json()}")
        sys.exit(1)
```

---

**Last Updated:** 2025-12-11
