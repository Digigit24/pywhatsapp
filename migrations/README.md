# Database Migrations - Flow Builder

## Quick Start

### Run the Migration

Connect to your PostgreSQL database and run:

```bash
psql -U postgres -d whatspy_db -f migrations/create_flows_table.sql
```

Or copy and paste the SQL directly into your database client.

---

## Migration File

**File:** `create_flows_table.sql`

This migration creates the `flows` table with all necessary indexes and triggers.

---

## What Gets Created

### 1. Flows Table
```sql
CREATE TABLE flows (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'default',
    flow_id VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    flow_json JSONB NOT NULL,
    category VARCHAR(50),
    version VARCHAR(10) NOT NULL DEFAULT '3.0',
    data_api_version VARCHAR(10) DEFAULT '3.0',
    endpoint_uri VARCHAR(500),
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    is_active BOOLEAN DEFAULT TRUE,
    published_at VARCHAR(50),
    tags JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Indexes
- `idx_flows_tenant_id` - For tenant filtering
- `idx_flows_flow_id` - For flow lookups
- `idx_flows_status` - For status filtering
- `idx_flows_category` - For category filtering
- `idx_flows_is_active` - For active/inactive filtering
- `idx_flows_created_at` - For sorting by date
- `idx_flows_flow_json` - GIN index for JSON queries
- `idx_flows_tags` - GIN index for tag queries

### 3. Triggers
- Auto-update `updated_at` timestamp on every update

---

## Manual SQL Commands

### Create Table Only
```sql
CREATE TABLE IF NOT EXISTS flows (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'default',
    flow_id VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    flow_json JSONB NOT NULL,
    category VARCHAR(50),
    version VARCHAR(10) NOT NULL DEFAULT '3.0',
    data_api_version VARCHAR(10) DEFAULT '3.0',
    endpoint_uri VARCHAR(500),
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    is_active BOOLEAN DEFAULT TRUE,
    published_at VARCHAR(50),
    tags JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### Add Indexes (if needed separately)
```sql
CREATE INDEX idx_flows_tenant_id ON flows(tenant_id);
CREATE INDEX idx_flows_flow_id ON flows(flow_id);
CREATE INDEX idx_flows_status ON flows(status);
CREATE INDEX idx_flows_category ON flows(category);
CREATE INDEX idx_flows_is_active ON flows(is_active);
CREATE INDEX idx_flows_created_at ON flows(created_at DESC);
CREATE INDEX idx_flows_flow_json ON flows USING GIN (flow_json);
CREATE INDEX idx_flows_tags ON flows USING GIN (tags);
```

### Add Auto-Update Trigger
```sql
CREATE OR REPLACE FUNCTION update_flows_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_flows_updated_at
    BEFORE UPDATE ON flows
    FOR EACH ROW
    EXECUTE FUNCTION update_flows_updated_at();
```

---

## Verify Installation

After running the migration, verify the table was created:

```sql
-- Check if table exists
SELECT table_name
FROM information_schema.tables
WHERE table_name = 'flows';

-- Check table structure
\d flows

-- Check indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'flows';

-- Count rows (should be 0 initially)
SELECT COUNT(*) FROM flows;
```

---

## Rollback (if needed)

To remove the flows table:

```sql
-- Drop triggers
DROP TRIGGER IF EXISTS trigger_flows_updated_at ON flows;
DROP FUNCTION IF EXISTS update_flows_updated_at();

-- Drop table
DROP TABLE IF EXISTS flows CASCADE;
```

---

## Adding Sample Data

Insert a test flow:

```sql
INSERT INTO flows (
    tenant_id,
    flow_id,
    name,
    description,
    flow_json,
    category,
    status
) VALUES (
    'default',
    'test-flow-001',
    'Test Customer Support Flow',
    'A simple test flow for customer support',
    '{
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
                        "children": [{
                            "type": "TextHeading",
                            "text": "How can we help you?"
                        }]
                    },
                    {
                        "type": "Footer",
                        "label": "Submit",
                        "on-click-action": {
                            "name": "complete",
                            "payload": {}
                        }
                    }
                ]
            }
        }]
    }'::jsonb,
    'CUSTOMER_SUPPORT',
    'DRAFT'
);
```

Verify the insert:

```sql
SELECT
    flow_id,
    name,
    category,
    status,
    created_at
FROM flows;
```

---

## Querying Flows

### Get all flows for a tenant
```sql
SELECT * FROM flows
WHERE tenant_id = 'default'
ORDER BY created_at DESC;
```

### Get published flows only
```sql
SELECT flow_id, name, category, published_at
FROM flows
WHERE status = 'PUBLISHED'
  AND is_active = true;
```

### Search flows by name
```sql
SELECT flow_id, name, description
FROM flows
WHERE name ILIKE '%support%'
   OR description ILIKE '%support%';
```

### Get flows by category
```sql
SELECT flow_id, name, status
FROM flows
WHERE category = 'CUSTOMER_SUPPORT';
```

### Query flow JSON content
```sql
-- Get flows with specific screen ID
SELECT flow_id, name
FROM flows
WHERE flow_json->'screens' @> '[{"id": "START"}]'::jsonb;

-- Get flows with version 3.0
SELECT flow_id, name
FROM flows
WHERE flow_json->>'version' = '3.0';
```

---

## Performance Tips

1. **Use indexes** - The migration creates all necessary indexes
2. **JSONB queries** - Use GIN indexes for efficient JSON queries
3. **Pagination** - Always use LIMIT and OFFSET for large result sets
4. **Tenant filtering** - Always filter by tenant_id first

---

## Troubleshooting

### Error: relation "flows" already exists
The table already exists. Either:
- Drop it first: `DROP TABLE flows CASCADE;`
- Or skip creation: Comment out CREATE TABLE in migration file

### Error: function update_flows_updated_at already exists
The function already exists. Either:
- Use `CREATE OR REPLACE FUNCTION` (already in migration)
- Or drop it first: `DROP FUNCTION update_flows_updated_at CASCADE;`

### Error: JSONB type not found
Your PostgreSQL version is too old (need 9.4+). Upgrade PostgreSQL or use JSON type instead.

---

## Next Steps

After running the migration:

1. ✅ Verify table creation
2. ✅ Test with sample data
3. ✅ Start using the Flow API endpoints
4. ✅ Build your frontend UI

---

**Migration Version:** 1.0
**Date Created:** 2025-12-09
**PostgreSQL Version Required:** 9.4+
