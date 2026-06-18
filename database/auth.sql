-- Admin accounts — the only authenticated entity in the system.
CREATE TABLE IF NOT EXISTS admins (
    admin_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name     VARCHAR(255) NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

-- Case-insensitive email lookups (find_by_email uses LOWER(email)).
CREATE INDEX IF NOT EXISTS idx_admins_email_lower ON admins (LOWER(email));

-- Server-side JWT blocklist — lets /logout invalidate a token before its natural exp.
CREATE TABLE IF NOT EXISTS revoked_tokens (
    jti        VARCHAR(64) PRIMARY KEY,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Speeds up the periodic cleanup that drops rows past their expiry.
CREATE INDEX IF NOT EXISTS idx_revoked_tokens_expires_at ON revoked_tokens (expires_at);
