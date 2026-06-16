import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from devices import DEVICE_VALUES


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "_", value.strip().lower())


# ==================== REQUEST SCHEMAS ====================

class SessionCreate(BaseModel):
    activity: str = Field(..., min_length=1, max_length=100, description="Activity name (e.g. walking, running)", examples=["walking"])
    device: str = Field(..., min_length=1, max_length=100, description="Hardware device identifier", examples=["IyqSLj"])
    device_name: str = Field(..., description=f"Device type. Values: {', '.join(sorted(DEVICE_VALUES))}", examples=["shoe"])
    start_time: datetime = Field(..., description="Session start time (ISO 8601)", examples=["2025-01-15T08:00:00Z"])
    end_time: datetime = Field(..., description="Session end time (ISO 8601)", examples=["2025-01-15T08:30:00Z"])

    @field_validator("activity")
    @classmethod
    def validate_activity(cls, v: str) -> str:
        v = _normalize(v)
        if not v:
            raise ValueError("activity must not be empty")
        return v

    @field_validator("device_name")
    @classmethod
    def validate_device_name(cls, v: str) -> str:
        v = _normalize(v)
        if v not in DEVICE_VALUES:
            raise ValueError(f"device_name must be one of: {sorted(DEVICE_VALUES)}")
        return v


class BulkDeleteRequest(BaseModel):
    session_ids: list[str] = Field(..., min_length=1, description="List of session UUIDs to delete", examples=[["c9636f46-1080-4729-8f88-d2acd16fcfe7"]])


# ==================== RESPONSE DATA MODELS ====================

class SessionOut(BaseModel):
    session_id: str = Field(..., description="Unique UUID of the session", examples=["c9636f46-1080-4729-8f88-d2acd16fcfe7"])
    user_id: str = Field(..., description="UUID of the user", examples=["a1b2c3d4-5678-90ab-cdef-1234567890ab"])
    user_name: str = Field(..., description="Display name of the user", examples=["vivek_vishwakarma"])
    activity: str = Field(..., description="Activity name", examples=["walking"])
    device: str = Field(..., description="Hardware device identifier", examples=["IyqSLj"])
    device_name: str = Field(..., description="Device type", examples=["shoe"])
    start_time: datetime = Field(..., description="Session start time")
    end_time: datetime = Field(..., description="Session end time")
    duration_seconds: int = Field(..., description="Total session duration in seconds", examples=[1800])
    duration_hms: str = Field(..., description="Duration formatted as HH:MM:SS", examples=["00:30:00"])
    created_at: datetime = Field(..., description="Record creation timestamp")

    model_config = ConfigDict(from_attributes=True)


# ==================== RESPONSE SCHEMAS ====================

class SessionResponse(BaseModel):
    success: bool = Field(default=True)
    message: str = Field(..., examples=["Session created successfully"])
    data: SessionOut

    model_config = ConfigDict(json_schema_extra={"example": {
        "success": True,
        "message": "Session created successfully",
        "data": {
            "session_id": "c9636f46-1080-4729-8f88-d2acd16fcfe7",
            "user_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
            "user_name": "vivek_vishwakarma",
            "activity": "walking",
            "device": "IyqSLj",
            "device_name": "shoe",
            "start_time": "2025-01-15T08:00:00Z",
            "end_time": "2025-01-15T08:30:00Z",
            "duration_seconds": 1800,
            "duration_hms": "00:30:00",
            "created_at": "2025-01-15T08:30:01Z"
        }
    }})


class SessionPage(BaseModel):
    success: bool = Field(default=True)
    data: list[SessionOut]
    total: int = Field(..., description="Total matching sessions", examples=[493])
    limit: int = Field(..., description="Items per page", examples=[20])
    offset: int = Field(..., description="Items skipped", examples=[0])

    model_config = ConfigDict(json_schema_extra={"example": {
        "success": True,
        "data": [{
            "session_id": "c9636f46-1080-4729-8f88-d2acd16fcfe7",
            "user_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
            "user_name": "vivek_vishwakarma",
            "activity": "walking",
            "device": "IyqSLj",
            "device_name": "shoe",
            "start_time": "2025-01-15T08:00:00Z",
            "end_time": "2025-01-15T08:30:00Z",
            "duration_seconds": 1800,
            "duration_hms": "00:30:00",
            "created_at": "2025-01-15T08:30:01Z"
        }],
        "total": 493,
        "limit": 20,
        "offset": 0
    }})


class DeleteResponse(BaseModel):
    success: bool = Field(default=True)
    message: str = Field(..., examples=["Deleted 3 sessions"])
    deleted: int = Field(..., description="Number of rows deleted", examples=[3])

    model_config = ConfigDict(json_schema_extra={"example": {
        "success": True,
        "message": "Deleted 3 sessions",
        "deleted": 3
    }})


