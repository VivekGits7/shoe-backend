from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from error import AppException, ConflictException, UnauthorizedException
from limiter import limiter
from logger import get_logger
from models.auth import (
    Admin,
    RevokedToken,
    create_access_token,
    decode_token,
    get_current_admin,
    get_password_hash,
    oauth2_scheme,
    verify_password,
)
from schema.auth.auth import (
    AdminProfile,
    AuthResponse,
    LogoutResponse,
    RegisterAdminRequest,
)
from schema.response import (
    COMMON_ERROR_RESPONSES,
    ConflictResponse,
    UnauthorizedResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _build_admin_profile(admin: Admin) -> AdminProfile:
    """Build an AdminProfile from an Admin instance (never exposes password_hash)."""
    return AdminProfile(
        admin_id=str(admin.admin_id),
        full_name=admin.full_name,
        email=admin.email,
        created_at=admin.created_at.isoformat() if admin.created_at else None,
        last_login_at=admin.last_login_at.isoformat() if admin.last_login_at else None,
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new admin",
    responses={
        **COMMON_ERROR_RESPONSES,
        201: {"model": AuthResponse, "description": "Admin registered, returns JWT token"},
        409: {"model": ConflictResponse, "description": "Email already registered"},
    },
)
@limiter.limit("10/minute")
async def register(request: Request, data: RegisterAdminRequest) -> AuthResponse:
    """
    Register a new admin account. Returns a JWT used to authorize protected (write/delete) endpoints.

    - **full_name** (str, required): Admin's full name (2-255 chars)
    - **email** (str, required): Unique email — used as login identifier
    - **password** (str, required): Min 8 characters
    """
    try:
        existing = await Admin.find_by_email(data.email)
        if existing:
            raise ConflictException("Email already registered. Please login.")

        admin = await Admin.create(
            full_name=data.full_name,
            email=data.email,
            password_hash=get_password_hash(data.password),
        )
        await admin.update_last_login()
        access_token = create_access_token(data={"sub": admin.email})

        return AuthResponse(
            success=True,
            message="Admin registered successfully",
            access_token=access_token,
            token_type="bearer",
            admin=_build_admin_profile(admin),
        )
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"Admin register error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Admin login",
    responses={
        **COMMON_ERROR_RESPONSES,
        200: {"model": AuthResponse, "description": "Login successful, returns JWT token"},
        401: {"model": UnauthorizedResponse, "description": "Invalid email or password"},
    },
)
@limiter.limit("10/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()) -> AuthResponse:
    """
    Authenticate an admin and receive a JWT. Uses OAuth2 form login (Swagger "Authorize" compatible).

    - **username** (form, required): Admin's email address
    - **password** (form, required): Admin's password
    """
    try:
        admin = await Admin.find_by_email(form_data.username)
        if not admin or not verify_password(form_data.password, admin.password_hash):
            raise UnauthorizedException("Invalid email or password")

        await admin.update_last_login()
        access_token = create_access_token(data={"sub": admin.email})

        return AuthResponse(
            success=True,
            message="Login successful",
            access_token=access_token,
            token_type="bearer",
            admin=_build_admin_profile(admin),
        )
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"Admin login error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Admin logout (revoke token)",
    responses={
        **COMMON_ERROR_RESPONSES,
        200: {"model": LogoutResponse, "description": "Logged out — token revoked"},
        401: {"model": UnauthorizedResponse, "description": "Missing, invalid, or revoked token"},
    },
)
@limiter.limit("30/minute")
async def logout(
    request: Request,
    token: str = Depends(oauth2_scheme),
    current_admin: Admin = Depends(get_current_admin),
) -> LogoutResponse:
    """
    Log out the current admin by revoking their JWT server-side.

    - Requires a valid `Authorization: Bearer <token>` header
    - The token's `jti` is added to the blocklist; any later request with it returns 401
    """
    try:
        payload = decode_token(token)
        jti = payload.get("jti")
        exp_unix = payload.get("exp")

        if jti and exp_unix:
            await RevokedToken.add(jti=jti, expires_at=datetime.fromtimestamp(exp_unix))
            logger.info(f"Admin {current_admin.email} logged out (jti={jti[:8]}...)")

        return LogoutResponse(success=True, message="Logged out successfully")
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"Admin logout error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
