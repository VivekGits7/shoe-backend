import csv
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from error import AppException, BadRequestException, NotFoundException, validate_uuid
from limiter import limiter
from logger import get_logger
from models.activity import Activity
from models.session import ActivitySession
from models.user import User
from schema.response import COMMON_ERROR_RESPONSES, BadRequestResponse, NotFoundResponse
from schema.sessions.sessions import (
    BulkDeleteRequest,
    DeleteResponse,
    SessionCreate,
    SessionOut,
    SessionPage,
    SessionResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


@router.post(
    "/bulk-delete",
    response_model=DeleteResponse,
    summary="Delete multiple sessions by IDs",
    responses={
        **COMMON_ERROR_RESPONSES,
        200: {"model": DeleteResponse, "description": "Number of sessions deleted"},
        400: {"model": BadRequestResponse, "description": "session_ids list is empty or contains invalid UUIDs"},
    },
)
@limiter.limit("10/minute")
async def bulk_delete_sessions(request: Request, payload: BulkDeleteRequest) -> DeleteResponse:
    """
    Delete multiple sessions in one call.

    - **session_ids** (list[str], required): List of session UUIDs to delete
    """
    try:
        for sid in payload.session_ids:
            validate_uuid((sid, "session_id"))
        deleted = await ActivitySession.bulk_delete(payload.session_ids)
        return DeleteResponse(success=True, message=f"Deleted {deleted} sessions", deleted=deleted)
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"Bulk delete error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# NOTE: This parameterized POST must be declared AFTER the literal "/bulk-delete"
# route above — otherwise FastAPI matches "bulk-delete" as a {user_id}.
@router.post(
    "/{user_id}",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new activity session",
    responses={
        **COMMON_ERROR_RESPONSES,
        201: {"model": SessionResponse, "description": "Session recorded successfully"},
        400: {"model": BadRequestResponse, "description": "Invalid user_id UUID or end_time not after start_time"},
        404: {"model": NotFoundResponse, "description": "User or activity not found"},
    },
)
@limiter.limit("60/minute")
async def create_session(request: Request, user_id: str, payload: SessionCreate) -> SessionResponse:
    """
    Record a new activity session for a user.

    - **user_id** (path): User UUID
    - **activity** (str, required): Activity name (e.g. walking, running)
    - **device** (str, required): Hardware device identifier
    - **device_name** (str, required): Device type. Values: `shoe`, `sandal`
    - **start_time** (datetime, required): Session start (ISO 8601)
    - **end_time** (datetime, required): Session end (ISO 8601, must be after start_time)
    """
    try:
        validate_uuid((user_id, "user_id"))

        if payload.end_time <= payload.start_time:
            raise BadRequestException("end_time must be after start_time")

        user = await User.find_by_id(user_id)
        if not user:
            raise NotFoundException(
                "User not found. Create the user first via POST /api/users/create-user"
            )

        activity = await Activity.find_by_name(payload.activity)
        if not activity:
            raise NotFoundException(
                "Activity not found. Create it first via POST /api/activities/create-activity"
            )

        duration = int((payload.end_time - payload.start_time).total_seconds())
        session = await ActivitySession.create(
            user_id=user.user_id,
            activity_id=activity.activity_id,
            device_id=payload.device,
            device_name=payload.device_name,
            start_time=payload.start_time,
            end_time=payload.end_time,
            duration_seconds=duration,
        )

        return SessionResponse(
            success=True,
            message="Session recorded successfully",
            data=SessionOut(
                session_id=session.session_id,
                user_id=session.user_id,
                user_name=user.user_name,
                activity=activity.activity_name,
                device=session.device_id,
                device_name=session.device_name,
                start_time=session.start_time,
                end_time=session.end_time,
                duration_seconds=session.duration_seconds,
                duration_hms=session.duration_hms,
                created_at=session.created_at,
            ),
        )
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"Create session error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "",
    response_model=SessionPage,
    summary="List sessions with filters and pagination",
    responses={
        **COMMON_ERROR_RESPONSES,
        200: {"model": SessionPage, "description": "Paginated list of sessions"},
        400: {"model": BadRequestResponse, "description": "Invalid activity_id UUID format"},
    },
)
@limiter.limit("60/minute")
async def list_sessions(
    request: Request,
    limit: int = Query(default=20, ge=1, le=500, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Items to skip"),
    search: Optional[str] = Query(None, description="Case-insensitive partial search across user name and activity name"),
    activity_id: Optional[str] = Query(None, description="Filter by exact activity UUID"),
    start_date: Optional[date] = Query(None, description="Inclusive lower bound on start_time (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Inclusive upper bound on start_time (YYYY-MM-DD)"),
) -> SessionPage:
    """
    List sessions with optional filters.

    - **search** (query, optional): Partial match across user name and activity name
    - **activity_id** (query, optional): Filter by activity UUID
    - **start_date** (query, optional): Filter from date (YYYY-MM-DD)
    - **end_date** (query, optional): Filter to date (YYYY-MM-DD)
    - **limit** (query, optional): Page size 1-500. Default: `20`
    - **offset** (query, optional): Skip N items. Default: `0`
    """
    try:
        if activity_id:
            validate_uuid((activity_id, "activity_id"))
        sessions, total = await ActivitySession.get_list(
            limit=limit,
            offset=offset,
            search=search,
            activity_id=activity_id,
            start_date=start_date,
            end_date=end_date,
        )
        return SessionPage(
            success=True,
            data=[
                SessionOut(
                    session_id=s.session_id,
                    user_id=s.user_id,
                    user_name=s.user_name,
                    activity=s.activity_name,
                    device=s.device_id,
                    device_name=s.device_name,
                    start_time=s.start_time,
                    end_time=s.end_time,
                    duration_seconds=s.duration_seconds,
                    duration_hms=s.duration_hms,
                    created_at=s.created_at,
                )
                for s in sessions
            ],
            total=total,
            limit=limit,
            offset=offset,
        )
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"List sessions error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/export",
    summary="Export sessions as CSV",
    responses={
        **COMMON_ERROR_RESPONSES,
        200: {"description": "CSV file download of matching sessions"},
        400: {"model": BadRequestResponse, "description": "Invalid user_id or activity_id UUID format"},
    },
)
@limiter.limit("10/minute")
async def export_sessions(
    request: Request,
    user_id: Optional[str] = Query(None, description="Filter by exact user UUID"),
    activity_id: Optional[str] = Query(None, description="Filter by exact activity UUID"),
    start_date: Optional[date] = Query(None, description="Inclusive lower bound (YYYY-MM-DD) on start_time"),
    end_date: Optional[date] = Query(None, description="Inclusive upper bound (YYYY-MM-DD) on start_time"),
) -> StreamingResponse:
    """
    Download sessions as a CSV file.

    - **user_id** (query, optional): Filter by user UUID
    - **activity_id** (query, optional): Filter by activity UUID
    - **start_date** / **end_date** (query, optional): Date range filter
    """
    try:
        if user_id:
            validate_uuid((user_id, "user_id"))
        if activity_id:
            validate_uuid((activity_id, "activity_id"))

        rows = await ActivitySession.get_all_for_export(
            user_id=user_id,
            activity_id=activity_id,
            start_date=start_date,
            end_date=end_date,
        )

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["session_id", "user_name", "activity", "device", "device_name",
                         "start_time", "end_time", "duration_seconds", "duration_hms", "created_at"])
        for r in rows:
            writer.writerow([
                r.session_id, r.user_name, r.activity_name, r.device_id, r.device_name,
                r.start_time.isoformat() if r.start_time else "",
                r.end_time.isoformat() if r.end_time else "",
                r.duration_seconds,
                r.duration_hms,
                r.created_at.isoformat() if r.created_at else "",
            ])

        # Build descriptive filename (user_id is already filename-safe UUID chars)
        parts = ["activities"]
        if user_id:
            parts.append(user_id)
        if start_date and end_date and start_date == end_date:
            parts.append(start_date.isoformat())
        elif start_date or end_date:
            parts.append(
                f"{start_date.isoformat() if start_date else 'start'}"
                f"_to_{end_date.isoformat() if end_date else 'end'}"
            )
        filename = "_".join(parts) + ".csv"

        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"Export sessions error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a session by ID",
    responses={
        **COMMON_ERROR_RESPONSES,
        204: {"description": "Session deleted (no body)"},
        400: {"model": BadRequestResponse, "description": "Invalid UUID format"},
        404: {"model": NotFoundResponse, "description": "Session not found"},
    },
)
@limiter.limit("30/minute")
async def delete_session(request: Request, session_id: str):
    """
    Delete a single session.

    - **session_id** (path): Session UUID
    """
    try:
        validate_uuid((session_id, "session_id"))
        session = await ActivitySession.find_by_id(session_id)
        if not session:
            raise NotFoundException("Session not found")
        await session.delete()
    except (HTTPException, AppException):
        raise
    except Exception as e:
        logger.error(f"Delete session error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------------
# DISABLED: DELETE /api/sessions (delete ALL sessions) is commented out by
# request. Bulk-wiping every session is too destructive to expose. Use
# DELETE /api/sessions/{session_id} or POST /api/sessions/bulk-delete instead.
# Re-enable only if a deliberate full-wipe endpoint is genuinely needed.
# ---------------------------------------------------------------------------
# @router.delete(
#     "",
#     response_model=DeleteResponse,
#     summary="Delete ALL sessions",
#     responses={
#         **COMMON_ERROR_RESPONSES,
#         200: {"model": DeleteResponse, "description": "All sessions deleted"},
#         400: {"model": BadRequestResponse, "description": "confirm=true not passed"},
#     },
# )
# @limiter.limit("5/minute")
# async def delete_all_sessions(
#     request: Request,
#     confirm: bool = Query(False, description="Must be true to delete all sessions"),
# ) -> DeleteResponse:
#     """
#     Delete every session in the database.
#
#     - **confirm** (query, required): Must be `true` — safety guard
#     """
#     try:
#         if not confirm:
#             raise BadRequestException("Pass confirm=true to delete all sessions")
#         deleted = await ActivitySession.delete_all()
#         return DeleteResponse(success=True, message=f"Deleted {deleted} sessions", deleted=deleted)
#     except (HTTPException, AppException):
#         raise
#     except Exception as e:
#         logger.error(f"Delete all sessions error: {e}")
#         raise HTTPException(status_code=500, detail="Internal server error")
