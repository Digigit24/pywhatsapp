-- Migration: Create tenant_configs table
-- Description: Store tenant-specific WhatsApp Business API configuration
-- Date: 2025-12-11
--
-- This table stores tenant-specific credentials and settings that override
-- the global .env configuration when available.

-- Create tenant_configs table
CREATE TABLE IF NOT EXISTS tenant_configs (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Multi-tenancy & Ownership
    tenant_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(255),

    -- WhatsApp Business Account Configuration
    waba_id VARCHAR(255),                    -- WhatsApp Business Account ID
    phone_number_id VARCHAR(255),            -- Phone Number ID
    access_token TEXT,                        -- Long-lived access token

    -- Facebook App Configuration
    fb_app_id VARCHAR(255),
    fb_app_secret VARCHAR(255),

    -- Webhook Configuration
    callback_url VARCHAR(500),                -- Webhook callback URL
    redirect_url VARCHAR(500),                -- OAuth redirect URL
    verify_token VARCHAR(255),                -- Webhook verify token

    -- Token Management
    token_expires_at TIMESTAMP,               -- Access token expiration
    refresh_token TEXT,                       -- Refresh token (if available)

    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE,

    -- Metadata
    onboarded_at TIMESTAMP,                   -- When onboarding was completed
    last_verified_at TIMESTAMP,               -- Last token verification

    -- Timestamps (inherited from BaseModel pattern)
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_tenant_configs_tenant_id ON tenant_configs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_configs_user_id ON tenant_configs(user_id);
CREATE INDEX IF NOT EXISTS idx_tenant_configs_is_active ON tenant_configs(is_active);

-- Create composite index for tenant + user lookups
CREATE INDEX IF NOT EXISTS idx_tenant_user ON tenant_configs(tenant_id, user_id);

-- Add unique constraint to ensure one config per tenant
CREATE UNIQUE INDEX IF NOT EXISTS idx_tenant_configs_unique_tenant
    ON tenant_configs(tenant_id)
    WHERE is_active = TRUE;

-- Create trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_tenant_configs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_tenant_configs_updated_at
    BEFORE UPDATE ON tenant_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_tenant_configs_updated_at();

-- Add comments for documentation
COMMENT ON TABLE tenant_configs IS 'Tenant-specific WhatsApp Business API configuration';
COMMENT ON COLUMN tenant_configs.tenant_id IS 'Tenant identifier from JWT or session';
COMMENT ON COLUMN tenant_configs.user_id IS 'User who created/owns this configuration';
COMMENT ON COLUMN tenant_configs.waba_id IS 'WhatsApp Business Account ID from Meta';
COMMENT ON COLUMN tenant_configs.phone_number_id IS 'Phone Number ID for sending messages';
COMMENT ON COLUMN tenant_configs.access_token IS 'Long-lived access token from OAuth';
COMMENT ON COLUMN tenant_configs.fb_app_id IS 'Facebook App ID';
COMMENT ON COLUMN tenant_configs.fb_app_secret IS 'Facebook App Secret (encrypted)';
COMMENT ON COLUMN tenant_configs.callback_url IS 'Webhook callback URL for receiving messages';
COMMENT ON COLUMN tenant_configs.redirect_url IS 'OAuth redirect URL for onboarding';
COMMENT ON COLUMN tenant_configs.verify_token IS 'Webhook verification token';
COMMENT ON COLUMN tenant_configs.token_expires_at IS 'When the access token expires';
COMMENT ON COLUMN tenant_configs.refresh_token IS 'Refresh token for token renewal';
COMMENT ON COLUMN tenant_configs.is_active IS 'Whether this config is currently active';
COMMENT ON COLUMN tenant_configs.onboarding_completed IS 'Whether OAuth onboarding is complete';
COMMENT ON COLUMN tenant_configs.onboarded_at IS 'Timestamp when onboarding was completed';
COMMENT ON COLUMN tenant_configs.last_verified_at IS 'Last time token was verified';

-- Success message
SELECT 'tenant_configs table created successfully!' AS status;
