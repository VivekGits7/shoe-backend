import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from config import settings
from services.database import execute_command, execute_command_with_return, execute_query_one

# bcrypt password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme — tokenUrl MUST match the login endpoint path (drives Swagger "Authorize")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def _row(record) -> dict:
    return {k: record[k] for k in record.keys()}


# ==================== ADMIN MODEL ====================


class Admin:
    """Admin account — the only authenticated entity in the system."""

    def __init__(self, **kwargs):
        self.admin_id: str = str(kwargs.get("admin_id", ""))
        self.full_name: str = kwargs.get("full_name", "")
        self.email: str = kwargs.get("email", "")
        self.password_hash: str = kwargs.get("password_hash", "")
        self.created_at = kwargs.get("created_at")
        self.updated_at = kwargs.get("updated_at")
        self.last_login_at = kwargs.get("last_login_at")

    @classmethod
    async def find_by_id(cls, admin_id: str) -> Optional["Admin"]:
        row = await execute_query_one("SELECT * FROM admins WHERE admin_id = $1", uuid.UUID(admin_id))
        return cls(**_row(row)) if row else None

    @classmethod
    async def find_by_email(cls, email: str) -> Optional["Admin"]:
        """Find admin by email (case-insensitive)."""
        row = await execute_query_one("SELECT * FROM admins WHERE LOWER(email) = LOWER($1)", email)
        return cls(**_row(row)) if row else None

    @classmethod
    async def create(cls, full_name: str, email: str, password_hash: str) -> "Admin":
        query = """
            INSERT INTO admins (admin_id, full_name, email, password_hash, created_at, updated_at)
            VALUES ($1, $2, $3, $4, NOW(), NOW())
            RETURNING *
        """
        row = await execute_command_with_return(query, uuid.uuid4(), full_name, email, password_hash)
        if row is None:
            raise RuntimeError("INSERT RETURNING returned None unexpectedly")
        return cls(**_row(row))

    async def update_last_login(self) -> bool:
        await execute_command(
            "UPDATE admins SET last_login_at = NOW(), updated_at = NOW() WHERE admin_id = $1",
            uuid.UUID(self.admin_id),
        )
        return True

    def to_public_dict(self) -> dict[str, Any]:
        """Public representation — never exposes password_hash."""
        return {
            "admin_id": self.admin_id,
            "full_name": self.full_name,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }


# ==================== REVOKED TOKEN MODEL (Logout Blocklist) ====================


class RevokedToken:
    """Server-side blocklist of revoked JWT IDs — lets /logout invalidate a token before its natural exp."""

    @classmethod
    async def add(cls, jti: str, expires_at: datetime) -> bool:
        """Add a token's jti to the blocklist. Idempotent (multi-tab logout is a no-op)."""
        query = """
            INSERT INTO revoked_tokens (jti, expires_at, revoked_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (jti) DO NOTHING
        """
        await execute_command(query, jti, expires_at)
        return True

    @classmethod
    async def is_revoked(cls, jti: str) -> bool:
        """Check whether a jti is blocklisted — called on every authenticated request."""
        row = await execute_query_one("SELECT 1 FROM revoked_tokens WHERE jti = $1", jti)
        return row is not None

    @classmethod
    async def cleanup_expired(cls) -> bool:
        """Drop blocklist rows past their natural expiry. Run periodically to keep the table small."""
        await execute_command("DELETE FROM revoked_tokens WHERE expires_at < NOW()")
        return True


# ==================== AUTH HELPERS ====================


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash (truncate to 72 bytes for bcrypt)."""
    while len(plain_password.encode("utf-8")) > 72:
        plain_password = plain_password[:-1]
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password (truncates to 72 bytes for bcrypt compatibility)."""
    password = password.encode("utf-8")[:72].decode("utf-8", errors="ignore")
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with a unique jti so it can be revoked on logout."""
    to_encode = data.copy()
    expire = datetime.now() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "jti": secrets.token_urlsafe(32)})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode + validate a JWT signature/expiry. Raises 401 on failure."""
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_admin(token: str = Depends(oauth2_scheme)) -> Admin:
    """FastAPI dependency — resolve the current admin from a JWT. Rejects revoked tokens."""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    email = payload.get("sub")
    jti = payload.get("jti")
    if email is None:
        raise credentials_exception

    if jti and await RevokedToken.is_revoked(jti):
        raise HTTPException(
            status_code=401,
            detail="Token has been revoked. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    admin = await Admin.find_by_email(email)
    if admin is None:
        raise credentials_exception
    return admin
