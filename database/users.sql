CREATE TABLE IF NOT EXISTS users (
    user_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_name  VARCHAR(100) NOT NULL,
    device_id  VARCHAR(100) NOT NULL,
    device_name VARCHAR(100) NOT NULL DEFAULT 'shoe',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS users_user_id_key ON users (user_id);
