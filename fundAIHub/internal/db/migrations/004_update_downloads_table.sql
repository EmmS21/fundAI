-- Add new columns to existing downloads table
ALTER TABLE downloads
    ADD COLUMN user_id TEXT,
    ADD COLUMN bytes_downloaded BIGINT DEFAULT 0,
    ADD COLUMN total_bytes BIGINT,
    ADD COLUMN last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ADD COLUMN error_message TEXT,
    ADD COLUMN resume_position BIGINT DEFAULT 0;

-- Update status constraint to include new statuses
ALTER TABLE downloads
    DROP CONSTRAINT IF EXISTS valid_status,
    ADD CONSTRAINT valid_status CHECK (status IN ('started', 'paused', 'resuming', 'completed', 'failed'));