CREATE TABLE IF NOT EXISTS activity_sessions (
    session_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL REFERENCES users(user_id),
    activity_id      UUID NOT NULL REFERENCES activity(activity_id),
    device_id        VARCHAR(100) NOT NULL,
    device_name      VARCHAR(20) NOT NULL DEFAULT 'shoe',
    start_time       TIMESTAMPTZ NOT NULL,
    end_time         TIMESTAMPTZ NOT NULL,
    duration_seconds INTEGER NOT NULL,
    duration_hms     TEXT GENERATED ALWAYS AS (
                         LPAD((duration_seconds / 3600)::TEXT,        2, '0') || ':' ||
                         LPAD(((duration_seconds % 3600) / 60)::TEXT, 2, '0') || ':' ||
                         LPAD((duration_seconds % 60)::TEXT,          2, '0')
                     ) STORED,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_activity_sessions_user_id     ON activity_sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_activity_sessions_activity_id ON activity_sessions (activity_id);
CREATE INDEX IF NOT EXISTS ix_activity_sessions_device_id   ON activity_sessions (device_id);
CREATE INDEX IF NOT EXISTS ix_activity_sessions_created_at  ON activity_sessions (created_at);
