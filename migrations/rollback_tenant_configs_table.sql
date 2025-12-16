-- Rollback: Drop tenant_configs table
-- Description: Remove tenant_configs table and all related objects
-- Date: 2025-12-11
--
-- WARNING: This will permanently delete all tenant configuration data!
-- Make sure to backup your data before running this script.

-- Drop trigger first
DROP TRIGGER IF EXISTS trigger_tenant_configs_updated_at ON tenant_configs;

-- Drop trigger function
DROP FUNCTION IF EXISTS update_tenant_configs_updated_at();

-- Drop indexes
DROP INDEX IF EXISTS idx_tenant_configs_unique_tenant;
DROP INDEX IF EXISTS idx_tenant_user;
DROP INDEX IF EXISTS idx_tenant_configs_is_active;
DROP INDEX IF EXISTS idx_tenant_configs_user_id;
DROP INDEX IF EXISTS idx_tenant_configs_tenant_id;

-- Drop table
DROP TABLE IF EXISTS tenant_configs CASCADE;

-- Success message
SELECT 'tenant_configs table and related objects dropped successfully!' AS status;
