from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ==================== BASE RESPONSE ====================

class BaseResponse(BaseModel):
    success: bool = Field(default=True, description="Whether the request succeeded")
    message: str = Field(..., description="Human-readable result message")


# ==================== ERROR DETAIL MODELS ====================

class ErrorDetail(BaseModel):
    field: str = Field(..., description="Dot-separated path to the invalid field", examples=["body.email"])
    message: str = Field(..., description="Validation error message", examples=["value is not a valid email"])
    type: str = Field(..., description="Machine-readable error type", examples=["value_error.email"])


class ErrorBody(BaseModel):
    status_code: int = Field(..., description="HTTP status code", examples=[400])
    status_message: str = Field(..., description="HTTP status text", examples=["BAD REQUEST"])
    message: str = Field(..., description="User-friendly error message", examples=["Invalid request."])
    code: Optional[str] = Field(None, description="Machine-readable error code", examples=["BAD_REQUEST"])
    details: Optional[List[ErrorDetail]] = Field(None, description="Per-field validation errors (422 only)")


# ==================== ERROR RESPONSE MODELS ====================

class BadRequestResponse(BaseModel):
    success: bool = Field(default=False)
    error: ErrorBody

    model_config = ConfigDict(json_schema_extra={"example": {
        "success": False,
        "error": {"status_code": 400, "status_message": "BAD REQUEST",
                  "message": "Invalid request. Please check your input.", "code": "BAD_REQUEST"}
    }})


class NotFoundResponse(BaseModel):
    success: bool = Field(default=False)
    error: ErrorBody

    model_config = ConfigDict(json_schema_extra={"example": {
        "success": False,
        "error": {"status_code": 404, "status_message": "NOT FOUND",
                  "message": "The requested resource was not found.", "code": "NOT_FOUND"}
    }})


class ConflictResponse(BaseModel):
    success: bool = Field(default=False)
    error: ErrorBody

    model_config = ConfigDict(json_schema_extra={"example": {
        "success": False,
        "error": {"status_code": 409, "status_message": "CONFLICT",
                  "message": "This resource already exists.", "code": "CONFLICT"}
    }})


class ValidationErrorResponse(BaseModel):
    success: bool = Field(default=False)
    error: ErrorBody

    model_config = ConfigDict(json_schema_extra={"example": {
        "success": False,
        "error": {"status_code": 422, "status_message": "UNPROCESSABLE ENTITY",
                  "message": "Please check your input and try again.", "code": "VALIDATION_ERROR",
                  "details": [{"field": "body.activity", "message": "field required", "type": "missing"}]}
    }})


class RateLimitResponse(BaseModel):
    success: bool = Field(default=False)
    error: ErrorBody

    model_config = ConfigDict(json_schema_extra={"example": {
        "success": False,
        "error": {"status_code": 429, "status_message": "TOO MANY REQUESTS",
                  "message": "Rate limit exceeded. Please try again later.", "code": "RATE_LIMITED"}
    }})


class InternalServerErrorResponse(BaseModel):
    success: bool = Field(default=False)
    error: ErrorBody

    model_config = ConfigDict(json_schema_extra={"example": {
        "success": False,
        "error": {"status_code": 500, "status_message": "INTERNAL SERVER ERROR",
                  "message": "Something went wrong. Please try again later.", "code": "INTERNAL_ERROR"}
    }})


# ==================== COMMON SWAGGER RESPONSES ====================
# Spread into every endpoint: responses={**COMMON_ERROR_RESPONSES, ...}

COMMON_ERROR_RESPONSES = {
    422: {"model": ValidationErrorResponse, "description": "Request body failed schema validation"},
    429: {"model": RateLimitResponse, "description": "Rate limit exceeded"},
    500: {"model": InternalServerErrorResponse, "description": "Unexpected server error"},
}
