CREATE TABLE IF NOT EXISTS activity (
    activity_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    activity_name VARCHAR(100) NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS activity_activity_id_key ON activity (activity_id);
