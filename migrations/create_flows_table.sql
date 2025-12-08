-- Migration: Create flows table
-- Description: Creates the flows table for storing WhatsApp Flow configurations
-- Date: 2025-12-09

-- Create flows table
CREATE TABLE IF NOT EXISTS flows (
    -- Primary key and tenant
    id SERIAL,
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'default',

    -- Basic Flow Information
    flow_id VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Flow Configuration
    flow_json JSONB NOT NULL,
    category VARCHAR(50),

    -- Flow Metadata
    version VARCHAR(10) NOT NULL DEFAULT '3.0',
    data_api_version VARCHAR(10) DEFAULT '3.0',
    endpoint_uri VARCHAR(500),

    -- Status and Publishing
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    is_active BOOLEAN DEFAULT TRUE,
    published_at VARCHAR(50),

    -- Additional metadata
    tags JSONB DEFAULT '[]'::jsonb,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT flows_pkey PRIMARY KEY (id),
    CONSTRAINT flows_flow_id_key UNIQUE (flow_id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_flows_tenant_id ON flows(tenant_id);
CREATE INDEX IF NOT EXISTS idx_flows_flow_id ON flows(flow_id);
CREATE INDEX IF NOT EXISTS idx_flows_status ON flows(status);
CREATE INDEX IF NOT EXISTS idx_flows_category ON flows(category);
CREATE INDEX IF NOT EXISTS idx_flows_is_active ON flows(is_active);
CREATE INDEX IF NOT EXISTS idx_flows_created_at ON flows(created_at DESC);

-- Create GIN index for JSONB columns for better JSON query performance
CREATE INDEX IF NOT EXISTS idx_flows_flow_json ON flows USING GIN (flow_json);
CREATE INDEX IF NOT EXISTS idx_flows_tags ON flows USING GIN (tags);

-- Create trigger to auto-update updated_at timestamp
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

-- Add comments for documentation
COMMENT ON TABLE flows IS 'Stores WhatsApp Flow configurations and metadata';
COMMENT ON COLUMN flows.flow_id IS 'Unique identifier for the WhatsApp Flow';
COMMENT ON COLUMN flows.flow_json IS 'Complete Flow JSON structure following WhatsApp Flow JSON specification';
COMMENT ON COLUMN flows.category IS 'Flow category (e.g., SIGN_UP, APPOINTMENT_BOOKING, LEAD_GENERATION, etc.)';
COMMENT ON COLUMN flows.status IS 'Flow status: DRAFT, PUBLISHED, or DEPRECATED';
COMMENT ON COLUMN flows.version IS 'Flow JSON version (e.g., 3.0, 4.0)';
COMMENT ON COLUMN flows.data_api_version IS 'WhatsApp Flow Data API version';
COMMENT ON COLUMN flows.endpoint_uri IS 'HTTP endpoint for Flow data exchange';
