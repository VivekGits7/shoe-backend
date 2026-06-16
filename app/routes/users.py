import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

router = APIRouter(prefix="/api/users", tags=["users"])


class UserOption(BaseModel):
    user_name: str
    user_id: str


class UserDeviceInfo(BaseModel):
    device_id: str
    device_name: str


class CreateUserRequest(BaseModel):
    user_name: str
    device_id: str


@router.get("/names", response_model=list[UserOption])
def list_user_names(db: Session = Depends(get_db)):
    users = db.query(User).all()
    seen = set()
    result = []
    for user in users:
        user_name = str(user.user_name)
        user_id = str(user.user_id)
        if user_name not in seen:
            result.append(UserOption(user_name=user_name, user_id=user_id))
            seen.add(user_name)
    return result


@router.get("/{user_name}/device", response_model=UserDeviceInfo)
def get_user_device(user_name: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_name.ilike(user_name)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserDeviceInfo(
        device_id=str(user.device_id), device_name=str(user.device_name)
    )


@router.post("/create-user")
def create_user(request: CreateUserRequest, db: Session = Depends(get_db)):
    existing_user = (
        db.query(User)
        .filter(
            User.user_name.ilike(request.user_name),
            User.device_id == request.device_id,
        )
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=400, detail="User with the same name and device already exists"
        )

    new_user = User(
        user_id=str(uuid.uuid4()),
        user_name=request.user_name,
        device_id=request.device_id,
        device_name="shoe",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully", "user_id": new_user.user_id}
