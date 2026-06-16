import uuid as _uuid
from typing import Optional

import asyncpg
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from logger import get_logger

logger = get_logger(__name__)


# ==================== CUSTOM EXCEPTIONS ====================

class AppException(Exception):
    def __init__(
        self,
        status_code: int = 500,
        detail: str = "Internal server error",
        error_code: Optional[str] = None,
        headers: Optional[dict] = None,
    ):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code
        self.headers = headers
        super().__init__(self.detail)


class NotFoundException(AppException):
    def __init__(self, detail: str = "Resource not found", error_code: str = "NOT_FOUND"):
        super().__init__(status_code=404, detail=detail, error_code=error_code)


class BadRequestException(AppException):
    def __init__(self, detail: str = "Bad request", error_code: str = "BAD_REQUEST"):
        super().__init__(status_code=400, detail=detail, error_code=error_code)


class ConflictException(AppException):
    def __init__(self, detail: str = "Resource already exists", error_code: str = "CONFLICT"):
        super().__init__(status_code=409, detail=detail, error_code=error_code)


class ExternalServiceException(AppException):
    def __init__(self, detail: str = "External service error", error_code: str = "EXTERNAL_SERVICE_ERROR"):
        super().__init__(status_code=502, detail=detail, error_code=error_code)


# ==================== UUID VALIDATION ====================

def validate_uuid(*values: tuple) -> None:
    """Validate UUID strings. Raises BadRequestException on invalid input."""
    for value, param_name in values:
        try:
            _uuid.UUID(str(value))
        except (ValueError, AttributeError):
            raise BadRequestException(f"Invalid {param_name} format. Expected a valid UUID.")


# ==================== ERROR RESPONSE FORMAT ====================

HTTP_STATUS_MESSAGES = {
    400: "BAD REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT FOUND",
    409: "CONFLICT",
    422: "UNPROCESSABLE ENTITY",
    429: "TOO MANY REQUESTS",
    500: "INTERNAL SERVER ERROR",
    502: "BAD GATEWAY",
    503: "SERVICE UNAVAILABLE",
}

USER_FRIENDLY_MESSAGES = {
    "NOT_FOUND": "The requested resource was not found.",
    "BAD_REQUEST": "Invalid request. Please check your input.",
    "CONFLICT": "This resource already exists.",
    "EXTERNAL_SERVICE_ERROR": "Service temporarily unavailable. Please try again later.",
    "DATABASE_ERROR": "Something went wrong. Please try again later.",
    "INTERNAL_ERROR": "Something went wrong. Please try again later.",
}


def create_error_response(status_code: int, detail: str, error_code: Optional[str] = None) -> dict:
    status_message = HTTP_STATUS_MESSAGES.get(status_code, "ERROR")
    response: dict = {
        "success": False,
        "error": {
            "status_code": status_code,
            "status_message": status_message,
            "message": detail,
        },
    }
    if error_code:
        response["error"]["code"] = error_code
    return response


# ==================== EXCEPTION HANDLERS ====================

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    logger.error(f"AppException: {exc.detail} | Path: {request.url.path}")
    message = USER_FRIENDLY_MESSAGES.get(exc.error_code, exc.detail) if exc.error_code else exc.detail
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(exc.status_code, message, exc.error_code),
        headers=exc.headers,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if exc.status_code >= 500:
        logger.error(f"HTTPException: {exc.detail} | Path: {request.url.path}")
    else:
        logger.warning(f"HTTPException: {exc.detail} | Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(exc.status_code, str(exc.detail)),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"field": ".".join(str(loc) for loc in e["loc"]), "message": e["msg"], "type": e["type"]}
        for e in exc.errors()
    ]
    logger.warning(f"Validation error | Path: {request.url.path}")
    response = create_error_response(422, "Please check your input and try again.", "VALIDATION_ERROR")
    response["error"]["details"] = errors
    return JSONResponse(status_code=422, content=response)


async def pydantic_validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
    logger.warning(f"Pydantic validation error | Path: {request.url.path}")
    return JSONResponse(
        status_code=422,
        content=create_error_response(422, "Please check your input and try again.", "VALIDATION_ERROR"),
    )


async def asyncpg_exception_handler(request: Request, exc: asyncpg.PostgresError) -> JSONResponse:
    logger.error(f"Database error | Path: {request.url.path} | Error: {str(exc)}")
    if isinstance(exc, asyncpg.UniqueViolationError):
        return JSONResponse(
            status_code=409,
            content=create_error_response(409, USER_FRIENDLY_MESSAGES["CONFLICT"], "CONFLICT"),
        )
    return JSONResponse(
        status_code=500,
        content=create_error_response(500, USER_FRIENDLY_MESSAGES["DATABASE_ERROR"], "DATABASE_ERROR"),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled exception | Path: {request.url.path} | Error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=create_error_response(500, USER_FRIENDLY_MESSAGES["INTERNAL_ERROR"], "INTERNAL_ERROR"),
    )


# ==================== SETUP FUNCTION ====================

def setup_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_handler)
    app.add_exception_handler(asyncpg.PostgresError, asyncpg_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    logger.info("Error handlers registered")
