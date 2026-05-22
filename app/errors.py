import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)


class AppError(Exception):
    http_status: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, code: str | None = None,
                 http_status: int | None = None, **extra: Any) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if http_status is not None:
            self.http_status = http_status
        self.extra = extra


class NotFound(AppError):
    http_status = 404
    code = "not_found"

    def __init__(self, message: str = "not found", **extra: Any) -> None:
        super().__init__(message, **extra)


class Forbidden(AppError):
    http_status = 403
    code = "forbidden"

    def __init__(self, message: str = "forbidden", **extra: Any) -> None:
        super().__init__(message, **extra)


class ValidationFailed(AppError):
    http_status = 422
    code = "validation_failed"


class RateLimited(AppError):
    http_status = 429
    code = "rate_limited"


class FileTooLarge(AppError):
    http_status = 413
    code = "file_too_large"


class StorageError(AppError):
    http_status = 500
    code = "storage_error"


def register_exception_handlers(app: FastAPI) -> None:
    from fastapi.responses import HTMLResponse
    from app.templating import templates  # local import to avoid circular

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse | HTMLResponse:
        log.warning("app_error", extra={
            "code": exc.code, "path": request.url.path, "error_msg": exc.message,
        })
        wants_html = "text/html" in request.headers.get("accept", "")
        if wants_html:
            # Map common statuses to dedicated templates.
            template_name = {
                404: "pages/404.html",
                403: "pages/403.html",
            }.get(exc.http_status, "pages/500.html")
            return templates.TemplateResponse(
                request=request, name=template_name,
                context={"message": exc.message},
                status_code=exc.http_status,
            )
        return JSONResponse(
            status_code=exc.http_status,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
