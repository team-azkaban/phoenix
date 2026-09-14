-- Upgrade the initial prototype alert table to the incident lifecycle used by
-- the Alerts feature. Safe to run after 001_initial_schema.sql.
ALTER TABLE alerts
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE alerts
    ALTER COLUMN status SET DEFAULT 'new';

-- Preserve legacy loaded alerts but make their meaning explicit to the UI/API.
UPDATE alerts
SET status = 'new'
WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_alerts_status_created_at
    ON alerts (status, created_at DESC);
