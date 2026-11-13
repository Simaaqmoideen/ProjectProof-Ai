import uuid
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: list[dict[str, Any]] | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []
        super().__init__(message)


class UnauthenticatedError(AppError):
    def __init__(
        self, message: str = "Authentication required", details: list[dict[str, Any]] | None = None
    ):
        super().__init__(
            code="unauthenticated",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class ForbiddenError(AppError):
    def __init__(
        self, message: str = "Access forbidden", details: list[dict[str, Any]] | None = None
    ):
        super().__init__(
            code="forbidden",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class NotFoundError(AppError):
    def __init__(
        self, message: str = "Resource not found", details: list[dict[str, Any]] | None = None
    ):
        super().__init__(
            code="not_found",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ConflictError(AppError):
    def __init__(
        self, message: str = "Resource state conflict", details: list[dict[str, Any]] | None = None
    ):
        super().__init__(
            code="conflict",
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class ValidationError(AppError):
    def __init__(
        self, message: str = "Validation failed", details: list[dict[str, Any]] | None = None
    ):
        super().__init__(
            code="validation_error",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class BadRequestError(AppError):
    def __init__(self, message: str = "Bad request", details: list[dict[str, Any]] | None = None):
        super().__init__(
            code="bad_request",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class FileTooLargeError(AppError):
    def __init__(
        self,
        message: str = "File exceeds maximum permitted size",
        details: list[dict[str, Any]] | None = None,
    ):
        super().__init__(
            code="file_too_large",
            message=message,
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            details=details,
        )


class RateLimitedError(AppError):
    def __init__(
        self,
        message: str = "Too many requests. Please try again later.",
        details: list[dict[str, Any]] | None = None,
    ):
        super().__init__(
            code="rate_limited",
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
        )


def format_error_response(
    code: str, message: str, request_id: str, details: list[dict[str, Any]] | None = None
) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "request_id": request_id,
        }
    }


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = get_request_id(request)
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(exc.code, exc.message, request_id, exc.details),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = get_request_id(request)
    details = []
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err.get("loc", []))
        details.append(
            {
                "field": field,
                "issue": err.get("msg", "invalid"),
            }
        )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=format_error_response(
            "validation_error", "Request validation failed", request_id, details
        ),
    )


async def starlette_http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    request_id = get_request_id(request)
    code_map = {
        400: "validation_error",
        401: "unauthenticated",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        413: "file_too_large",
        429: "rate_limited",
    }
    code = code_map.get(exc.status_code, "server_error")
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(code, str(exc.detail), request_id, []),
        headers=exc.headers,
    )
