-- SQL Script to Add Status Column to Messages Table
-- Run this directly on your PostgreSQL database

-- Add status column to messages table
ALTER TABLE messages
ADD COLUMN status VARCHAR(20) DEFAULT 'sent';

-- Add comment to document the column
COMMENT ON COLUMN messages.status IS 'Message delivery status: sent, delivered, read, failed';

-- Optional: Update existing messages to have 'sent' status if NULL
UPDATE messages
SET status = 'sent'
WHERE status IS NULL;

-- Optional: Create index for faster status queries (recommended for large datasets)
CREATE INDEX idx_messages_status ON messages(status);

-- Verify the change
SELECT column_name, data_type, character_maximum_length, column_default
FROM information_schema.columns
WHERE table_name = 'messages' AND column_name = 'status';
