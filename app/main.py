from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.db import SessionLocal
from app.errors import register_exception_handlers
from app.logging import setup_logging
from app.modules.auth.router import router as auth_router
from app.modules.cycle.router import router as cycle_router
from app.modules.daily_log.router import router as daily_log_router
from app.rate_limit import limiter
from app.templating import templates

settings = get_settings()


def _wants_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging(level="INFO" if settings.app_env == "production" else "DEBUG")
    yield


app = FastAPI(
    title="Couple Diary",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if settings.app_env == "production" else "/docs",
    redoc_url=None,
)

register_exception_handlers(app)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": {"code": "rate_limited", "message": "too many requests"}},
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_failed", "message": str(exc.errors())}},
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if _wants_html(request):
        template_name = {
            404: "pages/404.html",
            403: "pages/403.html",
        }.get(exc.status_code, "pages/500.html")
        return templates.TemplateResponse(
            request=request, name=template_name,
            context={"message": exc.detail},
            status_code=exc.status_code,
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": str(exc.detail)}},
    )


app.include_router(auth_router)
app.include_router(cycle_router)
app.include_router(daily_log_router)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

SW_PATH = STATIC_DIR / "sw.js"


@app.get("/sw.js")
def service_worker():
    return FileResponse(
        SW_PATH,
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
    )


@app.get("/")
def root(request: Request):
    # Placeholder home page until T42 (today aggregator) lands. Extends base.
    return templates.TemplateResponse(
        request=request,
        name="base.html",
        context={"active": "today"},
    )


@app.get("/healthz")
def healthz() -> dict[str, str]:
    db_status = "ok"
    try:
        with SessionLocal() as s:
            s.execute(text("SELECT 1"))
    except Exception:
        db_status = "fail"
    return {"status": "ok" if db_status == "ok" else "degraded", "db": db_status}
