import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.devices import DEVICE_VALUES


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "_", value.strip().lower())


class SessionCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    user_name: str = Field(min_length=1, max_length=100)
    activity: str = Field(min_length=1, max_length=100)
    device: str
    device_name: str
    start_time: datetime
    end_time: datetime

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("user_id must not be empty")
        return v

    @field_validator("user_name")
    @classmethod
    def validate_user_name(cls, v: str) -> str:
        v = _normalize(v)
        if not v:
            raise ValueError("user_name must not be empty")
        return v

    @field_validator("activity")
    @classmethod
    def validate_activity(cls, v: str) -> str:
        v = _normalize(v)
        if not v:
            raise ValueError("activity must not be empty")
        return v

    @field_validator("device_name")
    @classmethod
    def validate_device(cls, v: str) -> str:
        v = _normalize(v)
        if v not in DEVICE_VALUES:
            raise ValueError(f"device must be one of: {sorted(DEVICE_VALUES)}")
        return v

    @field_validator("device_name")
    @classmethod
    def validate_device_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("device_name must not be empty")
        return v


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str | None = None
    user_name: str
    activity: str
    device: str
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    created_at: datetime


class SessionPage(BaseModel):
    items: list[SessionOut]
    total: int
    limit: int
    offset: int
