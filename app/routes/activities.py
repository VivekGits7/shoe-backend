import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Activity
from app.schemas import _normalize

router = APIRouter(prefix="/api/activities", tags=["activities"])


class ActivityOption(BaseModel):
    value: str
    label: str


@router.get("", response_model=list[ActivityOption])
def list_activities(db: Session = Depends(get_db)):
    activities = db.query(Activity).all()
    return [
        ActivityOption(
            value=str(activity.activity_name).lower(),
            label=str(activity.activity_name).replace("_", " ").title(),
        )
        for activity in activities
    ]


@router.post(
    "/create-activity/{activity_name}", response_model=ActivityOption, status_code=201
)
def create_activity(activity_name: str, db: Session = Depends(get_db)):
    existing_activity = (
        db.query(Activity).filter(Activity.activity_name.ilike(activity_name)).first()
    )
    if existing_activity:
        raise HTTPException(status_code=400, detail="Activity already exists")

    new_activity = Activity(
        activity_name=activity_name,
        activity_id=str(uuid.uuid4()),
    )
    db.add(new_activity)
    db.commit()
    db.refresh(new_activity)

    return ActivityOption(
        value=str(new_activity.activity_name).lower(),
        label=str(new_activity.activity_name).replace("_", " ").title(),
    )
