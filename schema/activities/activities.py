from pydantic import BaseModel, ConfigDict, Field, field_validator


# ==================== REQUEST SCHEMAS ====================

class CreateActivityRequest(BaseModel):
    activity_name: str = Field(..., min_length=1, max_length=100, description="Name of the activity to create (e.g. swimming, yoga)", examples=["swimming"])

    @field_validator("activity_name")
    @classmethod
    def validate_activity_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("activity_name must not be empty")
        return v


# ==================== RESPONSE DATA MODELS ====================

class ActivityOption(BaseModel):
    activity_id: str = Field(..., description="Unique UUID of the activity", examples=["c9636f46-1080-4729-8f88-d2acd16fcfe7"])
    value: str = Field(..., description="Normalized activity name (lowercase)", examples=["walking"])
    label: str = Field(..., description="Human-readable label", examples=["Walking"])


# ==================== RESPONSE SCHEMAS ====================

class ActivityListResponse(BaseModel):
    success: bool = Field(default=True)
    data: list[ActivityOption]

    model_config = ConfigDict(json_schema_extra={"example": {
        "success": True,
        "data": [
            {"activity_id": "c9636f46-1080-4729-8f88-d2acd16fcfe7", "value": "walking", "label": "Walking"},
            {"activity_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab", "value": "running", "label": "Running"}
        ]
    }})


class CreateActivityResponse(BaseModel):
    success: bool = Field(default=True)
    message: str = Field(..., examples=["Activity created successfully"])
    data: ActivityOption

    model_config = ConfigDict(json_schema_extra={"example": {
        "success": True,
        "message": "Activity created successfully",
        "data": {"activity_id": "c9636f46-1080-4729-8f88-d2acd16fcfe7", "value": "swimming", "label": "Swimming"}
    }})
