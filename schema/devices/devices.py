from pydantic import BaseModel, ConfigDict, Field


class DeviceOption(BaseModel):
    value: str = Field(..., description="Device type value", examples=["shoe"])
    label: str = Field(..., description="Human-readable label", examples=["Shoe"])


class DeviceListResponse(BaseModel):
    success: bool = Field(default=True)
    data: list[DeviceOption]

    model_config = ConfigDict(json_schema_extra={"example": {
        "success": True,
        "data": [
            {"value": "shoe", "label": "Shoe"},
            {"value": "sandal", "label": "Sandal"}
        ]
    }})
