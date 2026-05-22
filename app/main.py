from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from sqlalchemy import text

from app.config import get_settings
from app.db import SessionLocal

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup: nothing yet; later tasks add scheduler, etc.
    yield
    # Shutdown


app = FastAPI(
    title="Couple Diary",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if settings.app_env == "production" else "/docs",
    redoc_url=None,
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
