"""One error format for every /api response: {"status": "error", "message": "..."} (PM Plan 3.2)."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

import config

logger = logging.getLogger("oceansight_server")

# Fields whose validation error is reported as "<field> out of valid range [low, high]".
VALID_RANGES = {
    "temperature": config.TEMPERATURE_VALID,
    "pressure": config.PRESSURE_VALID,
    "limit": (1, config.HISTORY_LIMIT_MAX),
}


class ApiError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def error_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"status": "error", "message": message})


def describe(error: dict) -> str:
    """Turn one pydantic validation error into the message the client sees."""
    kind = error["type"]
    field = next((str(part) for part in reversed(error["loc"]) if part not in ("body", "query", "path")), None)
    if kind == "json_invalid":
        return "malformed JSON body"
    if kind == "model_attributes_type":
        return "request body must be a JSON object"
    if kind == "missing":
        return f"missing field: {field}" if field else "missing request body"
    if kind in ("greater_than_equal", "less_than_equal") and field in VALID_RANGES:
        low, high = VALID_RANGES[field]
        return f"{field} out of valid range [{low:g}, {high:g}]"
    if kind in ("float_type", "float_parsing"):
        return f"{field} must be a number"
    if kind in ("int_type", "int_parsing"):
        return f"{field} must be an integer"
    if kind == "string_type":
        return f"{field} must be a string"
    if kind == "timestamp_type":
        return "timestamp must be an ISO-8601 string, e.g. 2026-10-09T15:00:05Z"
    if kind == "timezone_aware":
        return "timestamp must include a timezone, e.g. 2026-10-09T15:00:05Z"
    if kind.startswith("datetime"):
        return "timestamp is not a valid ISO-8601 datetime"
    return f"{field}: {error['msg']}" if field else error["msg"]


def register_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError):
        logger.warning("rejected %s %s: %s", request.method, request.url.path, exc.message)
        return error_response(exc.status_code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        # FastAPI answers 422 by default; the contract says 400.
        message = describe(exc.errors()[0])
        logger.warning("rejected %s %s: %s (body=%.200r)", request.method, request.url.path, message, exc.body)
        return error_response(400, message)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):
        return error_response(exc.status_code, str(exc.detail))

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return error_response(500, "internal server error")
