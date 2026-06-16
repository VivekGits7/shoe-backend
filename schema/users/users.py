from pydantic import BaseModel, ConfigDict, Field


# ==================== REQUEST SCHEMAS ====================

class CreateUserRequest(BaseModel):
    user_name: str = Field(..., min_length=1, max_length=100, description="Display name for the user", examples=["vivek_vishwakarma"])
    device_id: str = Field(..., min_length=1, max_length=100, description="Unique device identifier from the hardware", examples=["IyqSLj"])


# ==================== RESPONSE DATA MODELS ====================

class UserData(BaseModel):
    user_id: str = Field(..., description="Unique UUID of the user", examples=["c9636f46-1080-4729-8f88-d2acd16fcfe7"])
    user_name: str = Field(..., description="Display name", examples=["vivek_vishwakarma"])
    device_id: str = Field(..., description="Hardware device identifier", examples=["IyqSLj"])
    device_name: str = Field(..., description="Device type", examples=["shoe"])
    created_at: str = Field(..., description="ISO 8601 creation timestamp", examples=["2025-01-15T10:30:00"])


class UserOption(BaseModel):
    user_id: str = Field(..., description="Unique UUID of the user", examples=["c9636f46-1080-4729-8f88-d2acd16fcfe7"])
    user_name: str = Field(..., description="Display name", examples=["vivek_vishwakarma"])
    device_id: str = Field(..., description="Hardware device identifier", examples=["IyqSLj"])


class UserDeviceInfo(BaseModel):
    device_id: str = Field(..., description="Hardware device identifier", examples=["IyqSLj"])
    device_name: str = Field(..., description="Device type", examples=["shoe"])


# ==================== RESPONSE SCHEMAS ====================

class CreateUserResponse(BaseModel):
    success: bool = Field(default=True)
    message: str = Field(..., description="Result message", examples=["User created successfully"])
    data: UserData

    model_config = ConfigDict(json_schema_extra={"example": {
        "success": True,
        "message": "User created successfully",
        "data": {
            "user_id": "c9636f46-1080-4729-8f88-d2acd16fcfe7",
            "user_name": "vivek_vishwakarma",
            "device_id": "IyqSLj",
            "device_name": "shoe",
            "created_at": "2025-01-15T10:30:00"
        }
    }})


class UserNamesResponse(BaseModel):
    success: bool = Field(default=True)
    data: list[UserOption]

    model_config = ConfigDict(json_schema_extra={"example": {
        "success": True,
        "data": [
            {"user_id": "c9636f46-1080-4729-8f88-d2acd16fcfe7", "user_name": "vivek_vishwakarma", "device_id": "IyqSLj"},
            {"user_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab", "user_name": "deep", "device_id": "Ab12Cd"}
        ]
    }})


class UserDeviceResponse(BaseModel):
    success: bool = Field(default=True)
    data: UserDeviceInfo

    model_config = ConfigDict(json_schema_extra={"example": {
        "success": True,
        "data": {"device_id": "IyqSLj", "device_name": "shoe"}
    }})
