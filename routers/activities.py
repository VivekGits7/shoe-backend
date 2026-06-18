import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request, status

from error import AppException, ConflictException, NotFoundException, validate_uuid
from limiter import limiter
from logger import get_logger
from models.activity import Activity
from models.auth import Admin, get_current_admin
from schema.activities.activities import (
    ActivityListResponse,
    ActivityOption,
    CreateActivityRequest,
    CreateActivityResponse,
)
from schema.response import (
    COMMON_ERROR_RESPONSES,
    BadRequestResponse,
    ConflictResponse,
    NotFoundResponse,
    UnauthorizedResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/activities", tags=["Activities"])


@router.get(
    "",
    response_model=ActivityListResponse,
    summary="List all activities",
    responses={
        **COMMON_ERROR_RESPONSES,
        200: {"model": ActivityListResponse, "description": "All activities stored in the database"},
    },
)
@limiter.limit("60/minute")
async def list_activities(request: Request) -> ActivityListResponse:
    """Return all activities, each with its activity_id plus value/label pair."""
    try:
        activities = await Activity.get_all()
        return ActivityListResponse(
            success=True,
            data=[
                ActivityOption(
                    activity_id=a.activity_id,
                    value=a.activity_name.lower(),
                    label=a.activity_name.replace("_", " ").replace("-", " ").title(),
                )
                for a in activities
            ],
        )
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"List activities error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/create-activity",
    response_model=CreateActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new activity",
    responses={
        **COMMON_ERROR_RESPONSES,
        201: {"model": CreateActivityResponse, "description": "Activity created successfully"},
        401: {"model": UnauthorizedResponse, "description": "Admin authentication required"},
        409: {"model": ConflictResponse, "description": "Activity with this name already exists"},
    },
)
@limiter.limit("20/minute")
async def create_activity(
    request: Request,
    data: CreateActivityRequest,
    current_admin: Admin = Depends(get_current_admin),
) -> CreateActivityResponse:
    """
    Create a new activity type. **Requires admin authentication** (Bearer token).

    - **activity_name** (str, required): Name of the activity to create (e.g. swimming, yoga)
    """
    try:
        existing = await Activity.find_by_name(data.activity_name)
        if existing:
            raise ConflictException("Activity already exists")

        activity = await Activity.create(data.activity_name)
        return CreateActivityResponse(
            success=True,
            message="Activity created successfully",
            data=ActivityOption(
                activity_id=activity.activity_id,
                value=activity.activity_name.lower(),
                label=activity.activity_name.replace("_", " ").replace("-", " ").title(),
            ),
        )
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"Create activity error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete(
    "/{activity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an activity by ID",
    responses={
        **COMMON_ERROR_RESPONSES,
        204: {"description": "Activity deleted (no body)"},
        400: {"model": BadRequestResponse, "description": "Invalid activity_id UUID format"},
        401: {"model": UnauthorizedResponse, "description": "Admin authentication required"},
        404: {"model": NotFoundResponse, "description": "Activity not found"},
        409: {"model": ConflictResponse, "description": "Activity still has recorded sessions"},
    },
)
@limiter.limit("20/minute")
async def delete_activity(
    request: Request,
    activity_id: str,
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Delete an activity by ID. **Requires admin authentication** (Bearer token).

    - **activity_id** (path): Activity UUID
    - Note: Fails with 409 if any session still references this activity — delete those first
    """
    try:
        validate_uuid((activity_id, "activity_id"))
        activity = await Activity.find_by_id(activity_id)
        if not activity:
            raise NotFoundException("Activity not found")
        try:
            await activity.delete()
        except asyncpg.ForeignKeyViolationError:
            raise ConflictException(
                "Activity has recorded sessions. Delete those sessions before deleting the activity."
            )
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"Delete activity error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
