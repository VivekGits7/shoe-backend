from typing import Optional

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from error import AppException, ConflictException, NotFoundException, validate_uuid
from limiter import limiter
from logger import get_logger
from models.auth import Admin, get_current_admin
from models.user import User
from schema.response import (
    COMMON_ERROR_RESPONSES,
    BadRequestResponse,
    ConflictResponse,
    NotFoundResponse,
    UnauthorizedResponse,
)
from schema.users.users import (
    CreateUserRequest,
    CreateUserResponse,
    UserData,
    UserDeviceInfo,
    UserDeviceResponse,
    UserNamesResponse,
    UserOption,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get(
    "",
    response_model=UserNamesResponse,
    summary="List all users",
    responses={
        **COMMON_ERROR_RESPONSES,
        200: {"model": UserNamesResponse, "description": "List of users with their IDs and device IDs"},
    },
)
@limiter.limit("60/minute")
async def list_users(
    request: Request,
    search: Optional[str] = Query(None, description="Case-insensitive partial search on user name"),
) -> UserNamesResponse:
    """
    Return all users as a list of (user_id, user_name, device_id) items.

    - **search** (query, optional): Partial, case-insensitive match on user name
    """
    try:
        users = await User.get_all(search=search)
        seen: set[str] = set()
        result: list[UserOption] = []
        for u in users:
            if u.user_name not in seen:
                result.append(UserOption(user_id=u.user_id, user_name=u.user_name, device_id=u.device_id))
                seen.add(u.user_name)
        return UserNamesResponse(success=True, data=result)
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"List users error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/{user_id}/device",
    response_model=UserDeviceResponse,
    summary="Get device info for a user",
    responses={
        **COMMON_ERROR_RESPONSES,
        200: {"model": UserDeviceResponse, "description": "Device info for the given user"},
        400: {"model": BadRequestResponse, "description": "Invalid user_id UUID format"},
        404: {"model": NotFoundResponse, "description": "User not found"},
    },
)
@limiter.limit("60/minute")
async def get_user_device(request: Request, user_id: str) -> UserDeviceResponse:
    """
    Return device_id and device_name for a user by ID.

    - **user_id** (path): User UUID
    """
    try:
        validate_uuid((user_id, "user_id"))
        user = await User.find_by_id(user_id)
        if not user:
            raise NotFoundException(f"User '{user_id}' not found")
        return UserDeviceResponse(
            success=True,
            data=UserDeviceInfo(
                device_id=user.device_id,
                device_name=user.device_name or "shoe",
            ),
        )
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"Get user device error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/create-user",
    response_model=CreateUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    responses={
        **COMMON_ERROR_RESPONSES,
        201: {"model": CreateUserResponse, "description": "User created successfully"},
        400: {"model": BadRequestResponse, "description": "Missing or invalid fields"},
        401: {"model": UnauthorizedResponse, "description": "Admin authentication required"},
        409: {"model": ConflictResponse, "description": "User with same name and device already exists"},
    },
)
@limiter.limit("20/minute")
async def create_user(
    request: Request,
    data: CreateUserRequest,
    current_admin: Admin = Depends(get_current_admin),
) -> CreateUserResponse:
    """
    Create a new user. **Requires admin authentication** (Bearer token).

    - **user_name** (str, required): Display name (1-100 chars)
    - **device_id** (str, required): Hardware device identifier
    """
    try:
        existing = await User.find_by_device_and_name(data.device_id, data.user_name)
        if existing:
            raise ConflictException("User with the same name and device already exists")

        user = await User.create(
            user_name=data.user_name,
            device_id=data.device_id,
            device_name="shoe",
        )
        return CreateUserResponse(
            success=True,
            message="User created successfully",
            data=UserData(
                user_id=user.user_id,
                user_name=user.user_name,
                device_id=user.device_id,
                device_name=user.device_name or "shoe",
                created_at=user.created_at.isoformat() if user.created_at else "",
            ),
        )
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"Create user error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user by ID",
    responses={
        **COMMON_ERROR_RESPONSES,
        204: {"description": "User deleted (no body)"},
        400: {"model": BadRequestResponse, "description": "Invalid user_id UUID format"},
        401: {"model": UnauthorizedResponse, "description": "Admin authentication required"},
        404: {"model": NotFoundResponse, "description": "User not found"},
        409: {"model": ConflictResponse, "description": "User still has activity sessions"},
    },
)
@limiter.limit("20/minute")
async def delete_user(
    request: Request,
    user_id: str,
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Delete a user by ID. **Requires admin authentication** (Bearer token).

    - **user_id** (path): User UUID
    - Note: Fails with 409 if the user still has activity sessions — delete those first
    """
    try:
        validate_uuid((user_id, "user_id"))
        user = await User.find_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        try:
            await user.delete()
        except asyncpg.ForeignKeyViolationError:
            raise ConflictException(
                "User has activity sessions. Delete those sessions before deleting the user."
            )
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
