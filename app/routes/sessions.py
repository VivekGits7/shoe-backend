import csv
import io
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Activity, ActivitySession, User
from app.schemas import SessionCreate, SessionOut, SessionPage


class BulkDeleteRequest(BaseModel):
    ids: list[int] = Field(min_length=1)


router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut, status_code=201)
def create_session(payload: SessionCreate, db: Session = Depends(get_db)):
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    # # payload.user_id is actually device_id from the form
    # device_id = payload.user_id

    # Get or create user by device_id and user_name
    user = (
        db.query(User)
        .filter(User.device_id == payload.device, User.user_name.ilike(payload.user_name))
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found. Please create the user first using the /api/users/create-user endpoint.",
        )

    # Get or create activity
    activity = (
        db.query(Activity)
        .filter(func.lower(Activity.activity_name) == payload.activity.lower())
        .first()
    )
    if not activity:
        raise HTTPException(
            status_code=404,
            detail="Activity not found. Please create the activity first using the /api/activities endpoint.",
        )

    duration = int((payload.end_time - payload.start_time).total_seconds())

    session = ActivitySession(
        user_id=user.user_id,
        activity_id=activity.activity_id,
        device_id=payload.device,
        start_time=payload.start_time,
        end_time=payload.end_time,
        duration_seconds=duration,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {
        "id": session.id,
        "user_id": session.user.user_id,
        "user_name": session.user.user_name,
        "activity": session.activity.activity_name,
        "device": session.device_id,
        "start_time": session.start_time,
        "end_time": session.end_time,
        "duration_seconds": session.duration_seconds,
        "created_at": session.created_at,
    }


def _apply_filters(query, user_name, activity, start_date, end_date):
    if user_name:
        query = query.filter(
            func.lower(User.user_name).contains(user_name.strip().lower())
        ).join(User, ActivitySession.user_id == User.user_id)
    if activity:
        query = query.filter(
            func.lower(Activity.activity_name).contains(activity.strip().lower())
        ).join(Activity, ActivitySession.activity_id == Activity.activity_id)
    if start_date:
        start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        query = query.filter(ActivitySession.start_time >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, time.min, tzinfo=timezone.utc) + timedelta(
            days=1
        )
        query = query.filter(ActivitySession.start_time < end_dt)
    return query


@router.get("", response_model=SessionPage)
def list_sessions(
    limit: int = Query(20, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_name: str | None = Query(
        None, description="Case-insensitive substring match on user name"
    ),
    activity: str | None = Query(
        None, description="Exact activity value (e.g. running)"
    ),
    start_date: date | None = Query(
        None, description="Inclusive lower bound on session start_time (YYYY-MM-DD)"
    ),
    end_date: date | None = Query(
        None, description="Inclusive upper bound on session start_time (YYYY-MM-DD)"
    ),
    db: Session = Depends(get_db),
):
    query = db.query(ActivitySession)
    query = _apply_filters(query, user_name, activity, start_date, end_date)
    total = query.count()
    sessions = (
        query.order_by(ActivitySession.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    items = [
        {
            "id": s.id,
            "user_id": s.user.user_id,
            "user_name": s.user.user_name,
            "activity": s.activity.activity_name,
            "device": s.device_id,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "duration_seconds": s.duration_seconds,
            "created_at": s.created_at,
        }
        for s in sessions
    ]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/export")
def export_sessions(
    user_name: str | None = Query(
        None, description="Optional case-insensitive substring match on user name"
    ),
    activity: str | None = Query(
        None, description="Optional case-insensitive substring match on activity"
    ),
    start_date: date | None = Query(
        None, description="Inclusive lower bound (YYYY-MM-DD) on start_time"
    ),
    end_date: date | None = Query(
        None, description="Inclusive upper bound (YYYY-MM-DD) on start_time"
    ),
    db: Session = Depends(get_db),
):
    query = db.query(ActivitySession)
    query = _apply_filters(query, user_name, activity, start_date, end_date)
    rows = query.order_by(ActivitySession.start_time.asc()).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "user_name",
            "activity",
            "device",
            "start_time",
            "end_time",
            "duration_seconds",
            "created_at",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                r.id,
                r.user.user_name,
                r.activity.activity_name,
                r.device_id,
                r.start_time.isoformat(),
                r.end_time.isoformat(),
                r.duration_seconds,
                r.created_at.isoformat(),
            ]
        )

    parts = ["activities"]
    if user_name and user_name.strip():
        safe_user = "".join(
            c if c.isalnum() or c in ("-", "_") else "_" for c in user_name.strip()
        )
        parts.append(safe_user)
    if start_date and end_date and start_date == end_date:
        parts.append(start_date.isoformat())
    elif start_date or end_date:
        parts.append(
            f"{start_date.isoformat() if start_date else 'start'}_to_{end_date.isoformat() if end_date else 'end'}"
        )
    filename = "_".join(parts) + ".csv"

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ActivitySession).filter(ActivitySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return None


@router.post("/bulk-delete")
def bulk_delete_sessions(payload: BulkDeleteRequest, db: Session = Depends(get_db)):
    deleted = (
        db.query(ActivitySession)
        .filter(ActivitySession.id.in_(payload.ids))
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"deleted": deleted}


@router.delete("")
def delete_all_sessions(
    confirm: bool = Query(False, description="Must be true to delete all sessions"),
    db: Session = Depends(get_db),
):
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Pass confirm=true to delete all sessions",
        )
    deleted = db.query(ActivitySession).delete(synchronize_session=False)
    db.commit()
    return {"deleted": deleted}
