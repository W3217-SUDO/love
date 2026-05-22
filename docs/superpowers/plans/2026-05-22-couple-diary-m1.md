# Couple Diary M1 (MVP) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the M1 MVP — a closed two-person web app with invite-only login, period/BBT/daily-tag logging, a multi-signal cycle predictor (Calendar + LH + BBT), authenticated file uploads, a "Today" aggregator page, a calendar view, basic settings, automated local backup, and self-signed-HTTPS deployment on Tencent Cloud server 150.158.3.104.

**Architecture:** Single FastAPI monolith (Uvicorn) behind Nginx reverse proxy with self-signed TLS, MariaDB on 127.0.0.1, server-side sessions with Argon2id, Jinja2 templates with HTMX for partial updates and Alpine.js for local state, APScheduler in-process for backup/cleanup, files stored under `/data/uploads/` with sha256-named paths and authenticated `/media/{id}` streaming.

**Tech Stack:** Python 3.11 · FastAPI · Uvicorn · SQLAlchemy 2.x · Alembic · PyMySQL · Pydantic 2 · Argon2-cffi · Jinja2 · HTMX · Alpine.js · Chart.js · Pillow · APScheduler · slowapi · pytest · hypothesis · factory_boy · ruff · mypy.

**Spec:** [`docs/superpowers/specs/2026-05-22-couple-diary-design.md`](../specs/2026-05-22-couple-diary-design.md) — this plan implements §11 M1 scope only. M2 and M3 plans will be written after M1 ships.

**Conventions:**
- All work happens under `C:\Users\13533\Desktop\个人信息\love\` (Windows dev) and `/opt/couple_diary/` (server). Dev uses `couple_diary_test` DB; production uses `couple_diary`.
- Commit after every passing task. Commit messages use Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `docs:`).
- TDD always: write failing test → confirm fail → implement → confirm pass → commit.
- Repo will be `git init`'d in T1. Each task assumes prior tasks are merged.

**Pre-flight:**
- Workspace `C:\Users\13533\Desktop\个人信息\love\` is empty except for `密钥/tencent_cloud{,.pub}` and `docs/superpowers/specs/...`. The plan creates everything else from scratch.
- Server `150.158.3.104` is reachable as `root` via the key at `密钥/tencent_cloud`. MariaDB 10.11 listening on 3306 (will be hardened to 127.0.0.1 in T58). Port 80 is free.
- No domain yet — M1 ships with self-signed cert (browser warning on first visit, both partners accept once).

---

## Phase A — Project Scaffolding

### Task 1: Initialize project skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `app/__init__.py`
- Create: `app/modules/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py` (empty stub, fills in T7)

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "couple-diary"
version = "0.1.0"
description = "Private two-person health & intimacy diary"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115,<0.120",
    "uvicorn[standard]>=0.30",
    "jinja2>=3.1",
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "pymysql>=1.1",
    "cryptography>=43",
    "pydantic>=2.8",
    "pydantic-settings>=2.5",
    "python-multipart>=0.0.9",
    "argon2-cffi>=23",
    "itsdangerous>=2.2",
    "pillow>=10.4",
    "apscheduler>=3.10",
    "slowapi>=0.1.9",
    "python-dateutil>=2.9",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5",
    "hypothesis>=6",
    "factory-boy>=3.3",
    "ruff>=0.6",
    "mypy>=1.11",
    "types-python-dateutil",
]

[project.scripts]
couple-diary = "app.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["app*"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "S", "ASYNC"]
ignore = ["S101"]  # assert allowed in tests

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S105", "S106"]  # hardcoded passwords in tests OK

[tool.mypy]
python_version = "3.11"
strict = true
plugins = ["pydantic.mypy"]
exclude = ["alembic/versions/"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-ra --strict-markers"
```

- [ ] **Step 2: Create `.gitignore`**

```gitignore
__pycache__/
*.py[cod]
.venv/
.env
.env.production
.env.local
*.sqlite
*.sqlite-journal
.coverage
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
dist/
build/
*.egg-info/
.superpowers/
密钥/
```

- [ ] **Step 3: Create `README.md`**

```markdown
# Couple Diary

Private two-person web app for tracking cycle, intimacy, mood, and shared memories.

See [design spec](docs/superpowers/specs/2026-05-22-couple-diary-design.md) and [M1 plan](docs/superpowers/plans/2026-05-22-couple-diary-m1.md).

## Dev setup

```bash
python -m venv .venv
.venv/Scripts/activate  # Windows
# source .venv/bin/activate  # Linux
pip install -e ".[dev]"
cp .env.example .env  # then edit
alembic upgrade head
pytest
uvicorn app.main:app --reload
```
```

- [ ] **Step 4: Create empty package markers**

```bash
mkdir app app/modules tests
```

Create empty files: `app/__init__.py`, `app/modules/__init__.py`, `tests/__init__.py`, `tests/conftest.py`.

- [ ] **Step 5: Initialize git + install deps**

```bash
git init
git add -A
python -m venv .venv
.venv/Scripts/python.exe -m pip install --upgrade pip
.venv/Scripts/python.exe -m pip install -e ".[dev]"
```

- [ ] **Step 6: Verify ruff and mypy run**

```bash
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m mypy app/
```
Expected: both exit 0 (nothing to check yet but no errors).

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: initialize project scaffold with pyproject and tooling"
```

---

### Task 2: Configuration via pydantic-settings

**Files:**
- Create: `app/config.py`
- Create: `.env.example`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing test `tests/test_config.py`**

```python
import os
from app.config import Settings


def test_settings_loads_required_fields(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("SECRET_KEY", "a" * 64)
    monkeypatch.setenv(
        "DATABASE_URL",
        "mysql+pymysql://u:p@127.0.0.1/db?charset=utf8mb4",
    )
    monkeypatch.setenv("UPLOAD_DIR", "/tmp/uploads")
    monkeypatch.setenv("BACKUP_DIR", "/tmp/backups")
    monkeypatch.setenv("LOG_DIR", "/tmp/logs")
    s = Settings()
    assert s.app_env == "test"
    assert s.secret_key == "a" * 64
    assert s.session_max_age_days == 30  # default


def test_settings_secret_key_min_length(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("SECRET_KEY", "tooshort")
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://u:p@127.0.0.1/db")
    monkeypatch.setenv("UPLOAD_DIR", "/tmp/u")
    monkeypatch.setenv("BACKUP_DIR", "/tmp/b")
    monkeypatch.setenv("LOG_DIR", "/tmp/l")
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/test_config.py -v
```
Expected: ImportError — `app.config` does not exist.

- [ ] **Step 3: Implement `app/config.py`**

```python
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["dev", "test", "production"] = "dev"
    secret_key: str = Field(min_length=32)
    database_url: str
    database_test_url: str | None = None

    upload_dir: Path
    backup_dir: Path
    log_dir: Path

    session_cookie_name: str = "cdsid"
    session_max_age_days: int = 30
    cookie_secure: bool = True

    vapid_public_key: str | None = None
    vapid_private_key: str | None = None
    vapid_subject: str | None = None

    @field_validator("upload_dir", "backup_dir", "log_dir")
    @classmethod
    def must_be_absolute(cls, v: Path) -> Path:
        if not v.is_absolute():
            raise ValueError(f"must be absolute path, got {v}")
        return v


def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
```

- [ ] **Step 4: Create `.env.example`**

```bash
APP_ENV=dev
SECRET_KEY=change-me-to-32-plus-random-bytes-via-openssl-rand-hex-32
DATABASE_URL=mysql+pymysql://couple:devpwd@127.0.0.1/couple_diary?charset=utf8mb4
DATABASE_TEST_URL=mysql+pymysql://couple:devpwd@127.0.0.1/couple_diary_test?charset=utf8mb4
UPLOAD_DIR=C:/Users/13533/Desktop/个人信息/love/.data/uploads
BACKUP_DIR=C:/Users/13533/Desktop/个人信息/love/.data/backups
LOG_DIR=C:/Users/13533/Desktop/个人信息/love/.data/logs
SESSION_COOKIE_NAME=cdsid
SESSION_MAX_AGE_DAYS=30
COOKIE_SECURE=false
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
VAPID_SUBJECT=
```

- [ ] **Step 5: Run test to verify it passes**

```bash
.venv/Scripts/python.exe -m pytest tests/test_config.py -v
```
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add app/config.py .env.example tests/test_config.py
git commit -m "feat(config): add pydantic-settings configuration loader"
```

---

### Task 3: Database session + Alembic init

**Files:**
- Create: `app/db.py`
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/` (empty dir + `.gitkeep`)
- Create: `tests/test_db.py`

- [ ] **Step 1: Create database `couple_diary_test` on the local server**

For Windows dev without local MariaDB, use the server's MariaDB (already running):

```bash
ssh -i "C:/Users/13533/Desktop/个人信息/love/密钥/tencent_cloud" root@150.158.3.104 \
  "mysql -uroot -e \"CREATE DATABASE IF NOT EXISTS couple_diary CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE DATABASE IF NOT EXISTS couple_diary_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE USER IF NOT EXISTS 'couple'@'%' IDENTIFIED BY 'devpwd-change-in-prod'; GRANT ALL ON couple_diary.* TO 'couple'@'%'; GRANT ALL ON couple_diary_test.* TO 'couple'@'%'; FLUSH PRIVILEGES;\""
```

Then update `.env` to point `DATABASE_URL` at `mysql+pymysql://couple:devpwd-change-in-prod@150.158.3.104/couple_diary` for dev (will be locked to 127.0.0.1 in production via T58).

- [ ] **Step 2: Write failing test `tests/test_db.py`**

```python
from sqlalchemy import text
from app.db import engine, SessionLocal


def test_engine_connects_and_returns_one():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1


def test_session_factory_yields_session():
    with SessionLocal() as session:
        result = session.execute(text("SELECT 2")).scalar()
        assert result == 2
```

- [ ] **Step 3: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/test_db.py -v
```
Expected: ImportError — `app.db` missing.

- [ ] **Step 4: Implement `app/db.py`**

```python
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    future=True,
)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: Run test to verify it passes**

```bash
.venv/Scripts/python.exe -m pytest tests/test_db.py -v
```
Expected: 2 passed (requires `.env` with valid DATABASE_URL).

- [ ] **Step 6: Initialize Alembic**

```bash
.venv/Scripts/python.exe -m alembic init alembic
```

This creates `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/`.

- [ ] **Step 7: Edit `alembic.ini` — set `sqlalchemy.url` to placeholder**

Replace the `sqlalchemy.url = ...` line with:
```ini
sqlalchemy.url = driver://from-env
```

- [ ] **Step 8: Edit `alembic/env.py` — pull URL from `app.config` and metadata from `app.db`**

Replace the file with:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.db import Base
# Import all models so Alembic sees them
import app.modules  # noqa: F401  - re-exports all module models

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata,
        literal_binds=True, dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 9: Add re-export to `app/modules/__init__.py`**

```python
# Re-exports for Alembic autogenerate to discover all models.
# Modules are imported as they are added in later tasks.
```

(Leave empty for now; later tasks append imports.)

- [ ] **Step 10: Verify Alembic sees no changes (no models yet)**

```bash
.venv/Scripts/python.exe -m alembic check
```
Expected: "No new upgrade operations detected" or equivalent.

- [ ] **Step 11: Commit**

```bash
git add app/db.py alembic.ini alembic/ tests/test_db.py app/modules/__init__.py
git commit -m "feat(db): wire SQLAlchemy session and Alembic with shared metadata"
```

---

### Task 4: FastAPI app skeleton with /healthz

**Files:**
- Create: `app/main.py`
- Create: `tests/test_healthz.py`

- [ ] **Step 1: Write failing test `tests/test_healthz.py`**

```python
from fastapi.testclient import TestClient
from app.main import app


def test_healthz_returns_200_and_status_ok():
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "db" in body
    assert body["db"] == "ok"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/test_healthz.py -v
```
Expected: ImportError on `app.main`.

- [ ] **Step 3: Implement `app/main.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/Scripts/python.exe -m pytest tests/test_healthz.py -v
```
Expected: 1 passed.

- [ ] **Step 5: Manually verify app boots**

```bash
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8001
```
Open http://127.0.0.1:8001/healthz in browser → should see `{"status":"ok","db":"ok"}`. Ctrl+C to stop.

- [ ] **Step 6: Commit**

```bash
git add app/main.py tests/test_healthz.py
git commit -m "feat(app): bootstrap FastAPI app with /healthz endpoint"
```

---

### Task 5: Structured JSON logging

**Files:**
- Create: `app/logging.py`
- Create: `tests/test_logging.py`
- Modify: `app/main.py` (call `setup_logging()` in lifespan)

- [ ] **Step 1: Write failing test `tests/test_logging.py`**

```python
import json
import logging

from app.logging import setup_logging


def test_logger_emits_json_with_required_fields(capsys):
    setup_logging(level="INFO")
    logger = logging.getLogger("test")
    logger.info("hello", extra={"user_id": 42, "request_id": "abc"})
    captured = capsys.readouterr()
    record = json.loads(captured.err.strip().splitlines()[-1])
    assert record["msg"] == "hello"
    assert record["level"] == "INFO"
    assert record["user_id"] == 42
    assert record["request_id"] == "abc"
    assert "ts" in record


def test_logger_redacts_password_fields(capsys):
    setup_logging(level="INFO")
    logger = logging.getLogger("test")
    logger.info("login", extra={"password": "secret", "token": "tk"})
    captured = capsys.readouterr()
    record = json.loads(captured.err.strip().splitlines()[-1])
    assert record["password"] == "***"
    assert record["token"] == "***"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/test_logging.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement `app/logging.py`**

```python
import json
import logging
import sys
from datetime import datetime, timezone

REDACT_KEYS = {"password", "password_hash", "token", "session_token", "secret"}
_STANDARD_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "taskName",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        payload: dict[str, object] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.message,
        }
        for k, v in record.__dict__.items():
            if k in _STANDARD_ATTRS:
                continue
            payload[k] = "***" if k in REDACT_KEYS else v
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)
    # Quiet noisy libs
    for name in ("sqlalchemy.engine", "urllib3", "multipart"):
        logging.getLogger(name).setLevel(logging.WARNING)
```

- [ ] **Step 4: Wire into `app/main.py` lifespan**

Edit `app/main.py` — change the lifespan and import:

```python
from app.logging import setup_logging
```

Change `lifespan` to:
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging(level="INFO" if settings.app_env == "production" else "DEBUG")
    yield
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_logging.py tests/test_healthz.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add app/logging.py app/main.py tests/test_logging.py
git commit -m "feat(logging): structured JSON logger with secret redaction"
```

---

### Task 6: Application errors + exception handlers

**Files:**
- Create: `app/errors.py`
- Modify: `app/main.py` (register handlers)
- Create: `tests/test_errors.py`

- [ ] **Step 1: Write failing test `tests/test_errors.py`**

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors import AppError, Forbidden, NotFound, register_exception_handlers


def make_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise AppError("kaboom", code="generic", http_status=500)

    @app.get("/missing")
    def missing() -> None:
        raise NotFound("nope")

    @app.get("/forbidden")
    def forbidden() -> None:
        raise Forbidden()

    return app


def test_app_error_returns_json_with_code():
    client = TestClient(make_app(), raise_server_exceptions=False)
    r = client.get("/boom")
    assert r.status_code == 500
    body = r.json()
    assert body["error"]["code"] == "generic"
    assert body["error"]["message"] == "kaboom"


def test_not_found_returns_404():
    client = TestClient(make_app())
    r = client.get("/missing")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_forbidden_returns_403():
    client = TestClient(make_app())
    r = client.get("/forbidden")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/test_errors.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement `app/errors.py`**

```python
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
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        log.warning("app_error", extra={
            "code": exc.code, "path": request.url.path, "msg": exc.message,
        })
        return JSONResponse(
            status_code=exc.http_status,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
```

- [ ] **Step 4: Register in `app/main.py`**

Add to imports:
```python
from app.errors import register_exception_handlers
```

After `app = FastAPI(...)`, add:
```python
register_exception_handlers(app)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_errors.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add app/errors.py app/main.py tests/test_errors.py
git commit -m "feat(errors): typed AppError hierarchy and JSON exception handlers"
```

---

### Task 7: Test infrastructure (conftest, factories, isolated DB)

**Files:**
- Modify: `tests/conftest.py`
- Create: `tests/factories.py` (stub for now; tasks fill in per model)

- [ ] **Step 1: Implement `tests/conftest.py`**

```python
import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Force test env BEFORE importing app
os.environ.setdefault("APP_ENV", "test")

from app.config import get_settings  # noqa: E402
from app.db import Base  # noqa: E402

_settings = get_settings()
_test_url = _settings.database_test_url or _settings.database_url
assert "test" in _test_url, f"Refusing to run tests against non-test DB: {_test_url}"

test_engine = create_engine(_test_url, pool_pre_ping=True, future=True)
TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, future=True)


@pytest.fixture(scope="session", autouse=True)
def _create_schema() -> Iterator[None]:
    # Import all models so metadata is populated
    import app.modules  # noqa: F401
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db() -> Iterator[Session]:
    """Per-test session wrapped in a transaction that always rolls back."""
    connection = test_engine.connect()
    txn = connection.begin()
    session = Session(bind=connection, expire_on_commit=False)

    try:
        yield session
    finally:
        session.close()
        txn.rollback()
        connection.close()


@pytest.fixture()
def client(db: Session, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """TestClient with the per-test DB session injected."""
    from app.db import get_db
    from app.main import app

    def _override() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

- [ ] **Step 2: Create `tests/factories.py` placeholder**

```python
"""factory_boy factories. Each module's tests append factories here as needed."""
import factory
from factory.alchemy import SQLAlchemyModelFactory

from tests.conftest import TestSessionLocal


class BaseFactory(SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session = TestSessionLocal()
        sqlalchemy_session_persistence = "commit"
```

- [ ] **Step 3: Sanity test — existing tests still pass with the new fixtures available**

```bash
.venv/Scripts/python.exe -m pytest -v
```
Expected: all existing tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py tests/factories.py
git commit -m "test: add isolated per-test DB session fixture and factory base"
```

---

**End of Phase A.** Project compiles, has 1 endpoint, has logging, has typed errors, has test infrastructure.

---

## Phase B — Authentication (Users, Couples, Invite Tokens, Sessions, Login)

### Task 8: User model + initial migration

**Files:**
- Create: `app/modules/auth/__init__.py`
- Create: `app/modules/auth/models.py`
- Modify: `app/modules/__init__.py` (re-export)
- Create: `tests/test_auth/__init__.py`
- Create: `tests/test_auth/test_user_model.py`

- [ ] **Step 1: Create `tests/test_auth/__init__.py`** (empty file)

- [ ] **Step 2: Write failing test `tests/test_auth/test_user_model.py`**

```python
from datetime import datetime

from app.modules.auth.models import User, UserRole


def test_user_persistable(db):
    u = User(
        username="alice",
        display_name="Alice",
        password_hash="$argon2id$dummy",
        role=UserRole.SHE,
    )
    db.add(u)
    db.flush()
    assert u.id is not None
    assert isinstance(u.created_at, datetime)


def test_username_is_unique(db):
    db.add(User(username="bob", display_name="B", password_hash="x", role=UserRole.HE))
    db.flush()
    db.add(User(username="bob", display_name="B2", password_hash="y", role=UserRole.SHE))
    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        db.flush()
```

- [ ] **Step 3: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/test_auth/test_user_model.py -v
```
Expected: ImportError.

- [ ] **Step 4: Implement `app/modules/auth/__init__.py`**

```python
from app.modules.auth import models  # noqa: F401  -- expose to Alembic
```

- [ ] **Step 5: Implement `app/modules/auth/models.py`**

```python
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class UserRole(str, enum.Enum):
    HE = "he"
    SHE = "she"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False)
    avatar_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
```

- [ ] **Step 6: Update `app/modules/__init__.py`**

```python
from app.modules import auth  # noqa: F401
```

- [ ] **Step 7: Generate Alembic migration**

```bash
.venv/Scripts/python.exe -m alembic revision --autogenerate -m "users table"
```

- [ ] **Step 8: Review the generated migration** in `alembic/versions/<rev>_users_table.py`. It should `create_table("users", ...)` with the columns above. Edit if SAEnum was rendered without explicit name — set `name="user_role"`. Example expected snippet:

```python
def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("he", "she", name="user_role"), nullable=False),
        sa.Column("avatar_path", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )
```

- [ ] **Step 9: Apply migration to dev DB**

```bash
.venv/Scripts/python.exe -m alembic upgrade head
```

- [ ] **Step 10: Run test to verify it passes**

```bash
.venv/Scripts/python.exe -m pytest tests/test_auth/test_user_model.py -v
```
Expected: 2 passed.

- [ ] **Step 11: Commit**

```bash
git add app/modules/auth/ app/modules/__init__.py alembic/versions/ tests/test_auth/
git commit -m "feat(auth): User model with role enum and initial migration"
```

---

### Task 9: Couple + InviteToken models + migration

**Files:**
- Modify: `app/modules/auth/models.py`
- Create: `tests/test_auth/test_couple_model.py`
- Create: `alembic/versions/<rev>_couples_and_invites.py` (autogen)

- [ ] **Step 1: Write failing test `tests/test_auth/test_couple_model.py`**

```python
from datetime import datetime, timedelta, timezone

from app.modules.auth.models import Couple, InviteToken, User, UserRole


def _user(db, username: str, role: UserRole) -> User:
    u = User(username=username, display_name=username, password_hash="x", role=role)
    db.add(u)
    db.flush()
    return u


def test_couple_links_two_users(db):
    a = _user(db, "alice", UserRole.SHE)
    b = _user(db, "bob", UserRole.HE)
    c = Couple(user_a_id=a.id, user_b_id=b.id)
    db.add(c)
    db.flush()
    assert c.id is not None


def test_invite_token_unique_and_expirable(db):
    u = _user(db, "carol", UserRole.SHE)
    t = InviteToken(
        token="ABCDEF123456",
        intended_role=UserRole.SHE,
        intended_display_name="Carol",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(t)
    db.flush()
    assert t.used_at is None
    assert t.token == "ABCDEF123456"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/test_auth/test_couple_model.py -v
```
Expected: ImportError.

- [ ] **Step 3: Append to `app/modules/auth/models.py`**

```python
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship


class Couple(Base):
    __tablename__ = "couples"
    __table_args__ = (
        UniqueConstraint("user_a_id", "user_b_id", name="uq_couples_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_a_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    user_b_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    bonded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    user_a: Mapped["User"] = relationship(foreign_keys=[user_a_id])
    user_b: Mapped["User"] = relationship(foreign_keys=[user_b_id])


class InviteToken(Base):
    __tablename__ = "invite_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    intended_role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False)
    intended_display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    intended_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
```

- [ ] **Step 4: Autogenerate migration**

```bash
.venv/Scripts/python.exe -m alembic revision --autogenerate -m "couples and invite tokens"
.venv/Scripts/python.exe -m alembic upgrade head
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_auth/ -v
```
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add app/modules/auth/models.py alembic/versions/ tests/test_auth/test_couple_model.py
git commit -m "feat(auth): Couple and InviteToken models with migration"
```

---

### Task 10: Password hashing service (Argon2id)

**Files:**
- Create: `app/modules/auth/passwords.py`
- Create: `tests/test_auth/test_passwords.py`

- [ ] **Step 1: Write failing test `tests/test_auth/test_passwords.py`**

```python
import pytest

from app.modules.auth.passwords import hash_password, verify_password


def test_hash_then_verify_succeeds():
    h = hash_password("correcthorsebatterystaple")
    assert h.startswith("$argon2id$")
    assert verify_password("correcthorsebatterystaple", h) is True


def test_verify_wrong_password_fails():
    h = hash_password("right-password")
    assert verify_password("wrong-password", h) is False


def test_verify_malformed_hash_returns_false():
    assert verify_password("anything", "not-a-hash") is False


def test_password_min_length_enforced():
    with pytest.raises(ValueError):
        hash_password("short")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/test_auth/test_passwords.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement `app/modules/auth/passwords.py`**

```python
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

MIN_PASSWORD_LENGTH = 8

_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=64 * 1024,  # 64 MiB
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except (VerifyMismatchError, InvalidHashError, Exception):
        return False


def needs_rehash(hashed: str) -> bool:
    try:
        return _hasher.check_needs_rehash(hashed)
    except InvalidHashError:
        return True
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_auth/test_passwords.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/modules/auth/passwords.py tests/test_auth/test_passwords.py
git commit -m "feat(auth): Argon2id password hashing with min-length and rehash check"
```

---

### Task 11: Invite token generation + CLI command

**Files:**
- Create: `app/modules/auth/invite.py`
- Create: `app/cli.py`
- Create: `tests/test_auth/test_invite.py`

- [ ] **Step 1: Write failing test `tests/test_auth/test_invite.py`**

```python
from datetime import datetime, timezone

from app.modules.auth.invite import generate_token_string, init_couple_invites
from app.modules.auth.models import InviteToken, UserRole


def test_generate_token_string_returns_url_safe_chars():
    t = generate_token_string()
    assert len(t) >= 24
    assert all(c.isalnum() or c in "-_" for c in t)


def test_init_couple_invites_creates_two_tokens(db):
    he_token, she_token = init_couple_invites(
        db,
        he_display="Bob",
        she_display="Alice",
        ttl_days=7,
    )
    assert he_token.intended_role == UserRole.HE
    assert she_token.intended_role == UserRole.SHE
    assert he_token.token != she_token.token
    assert he_token.expires_at > datetime.now(timezone.utc)
    rows = db.query(InviteToken).all()
    assert len(rows) == 2


def test_init_couple_invites_refuses_when_users_exist(db):
    from app.modules.auth.models import User
    db.add(User(username="x", display_name="X",
                password_hash="$argon2id$x", role=UserRole.HE))
    db.flush()
    import pytest
    with pytest.raises(RuntimeError):
        init_couple_invites(db, he_display="B", she_display="A", ttl_days=7)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/test_auth/test_invite.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement `app/modules/auth/invite.py`**

```python
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.modules.auth.models import InviteToken, User, UserRole


def generate_token_string(num_bytes: int = 24) -> str:
    return secrets.token_urlsafe(num_bytes)


def init_couple_invites(
    db: Session, *, he_display: str, she_display: str, ttl_days: int = 7,
) -> tuple[InviteToken, InviteToken]:
    if db.query(User).first() is not None:
        raise RuntimeError("users already exist; init-couple is only for empty systems")

    expires = datetime.now(timezone.utc) + timedelta(days=ttl_days)
    he = InviteToken(
        token=generate_token_string(),
        intended_role=UserRole.HE,
        intended_display_name=he_display,
        expires_at=expires,
    )
    she = InviteToken(
        token=generate_token_string(),
        intended_role=UserRole.SHE,
        intended_display_name=she_display,
        expires_at=expires,
    )
    db.add_all([he, she])
    db.flush()
    return he, she
```

- [ ] **Step 4: Implement `app/cli.py`**

```python
import argparse
import sys

from app.db import SessionLocal
from app.modules.auth.invite import init_couple_invites


def _cmd_init_couple(args: argparse.Namespace) -> int:
    with SessionLocal() as db:
        try:
            he, she = init_couple_invites(
                db, he_display=args.he, she_display=args.she, ttl_days=args.ttl_days,
            )
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        db.commit()
        base = args.base_url.rstrip("/")
        print("Invite tokens generated:")
        print(f"  HE  ({args.he}):  {base}/bind?token={he.token}")
        print(f"  SHE ({args.she}): {base}/bind?token={she.token}")
        print(f"\nExpires: {he.expires_at.isoformat()}")
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="couple-diary")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init-couple", help="Generate the two initial invite tokens")
    init.add_argument("--he", required=True, help="Display name of the male partner")
    init.add_argument("--she", required=True, help="Display name of the female partner")
    init.add_argument("--ttl-days", type=int, default=7)
    init.add_argument("--base-url", default="https://localhost",
                      help="Base URL used in the printed bind links")
    init.set_defaults(func=_cmd_init_couple)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_auth/test_invite.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add app/modules/auth/invite.py app/cli.py tests/test_auth/test_invite.py
git commit -m "feat(auth): invite token generator and init-couple CLI command"
```

---

### Task 12: Bind endpoint (POST /bind?token=)

**Files:**
- Create: `app/modules/auth/schemas.py`
- Create: `app/modules/auth/service.py` (bind logic)
- Create: `app/modules/auth/router.py` (HTML form route)
- Modify: `app/main.py` (mount router)
- Create: `tests/test_auth/test_bind.py`

- [ ] **Step 1: Write failing test `tests/test_auth/test_bind.py`**

```python
from datetime import datetime, timedelta, timezone

from app.modules.auth.invite import init_couple_invites
from app.modules.auth.models import Couple, InviteToken, User
from app.modules.auth.passwords import verify_password


def test_bind_creates_user_and_marks_token_used(client, db):
    he, she = init_couple_invites(db, he_display="Bob", she_display="Alice", ttl_days=7)
    db.commit()

    r = client.post(
        f"/bind?token={he.token}",
        data={"username": "bob", "password": "strong-password-1"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    user = db.query(User).filter_by(username="bob").one()
    assert verify_password("strong-password-1", user.password_hash)
    refreshed_token = db.query(InviteToken).get(he.id)
    assert refreshed_token.used_at is not None
    assert refreshed_token.used_by_user_id == user.id


def test_bind_second_user_creates_couple(client, db):
    he, she = init_couple_invites(db, he_display="Bob", she_display="Alice", ttl_days=7)
    db.commit()

    client.post(f"/bind?token={he.token}",
                data={"username": "bob", "password": "strong-password-1"})
    client.post(f"/bind?token={she.token}",
                data={"username": "alice", "password": "strong-password-2"})

    couple = db.query(Couple).one()
    assert {couple.user_a_id, couple.user_b_id} == \
           {db.query(User).filter_by(username="bob").one().id,
            db.query(User).filter_by(username="alice").one().id}


def test_bind_rejects_used_token(client, db):
    he, _she = init_couple_invites(db, he_display="Bob", she_display="A", ttl_days=7)
    db.commit()
    client.post(f"/bind?token={he.token}",
                data={"username": "bob", "password": "pwd-12345"})
    r = client.post(f"/bind?token={he.token}",
                    data={"username": "carol", "password": "pwd-67890"})
    assert r.status_code == 400


def test_bind_rejects_expired_token(client, db):
    from app.modules.auth.models import InviteToken, UserRole
    t = InviteToken(
        token="EXPIRED-TOKEN-STRING-LONG",
        intended_role=UserRole.HE,
        intended_display_name="Z",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db.add(t); db.commit()
    r = client.post(f"/bind?token={t.token}",
                    data={"username": "z", "password": "pwd-12345"})
    assert r.status_code == 400


def test_bind_rejects_short_password(client, db):
    he, _ = init_couple_invites(db, he_display="B", she_display="A", ttl_days=7)
    db.commit()
    r = client.post(f"/bind?token={he.token}",
                    data={"username": "bob", "password": "short"})
    assert r.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/test_auth/test_bind.py -v
```
Expected: ImportError or 404 (router not mounted).

- [ ] **Step 3: Implement `app/modules/auth/schemas.py`**

```python
from pydantic import BaseModel, Field, field_validator


class BindRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
```

- [ ] **Step 4: Implement `app/modules/auth/service.py`**

```python
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.errors import AppError, ValidationFailed
from app.modules.auth.models import Couple, InviteToken, User
from app.modules.auth.passwords import hash_password


class BindError(AppError):
    http_status = 400
    code = "bind_failed"


def bind_user(db: Session, *, token_string: str, username: str, password: str) -> User:
    token = db.query(InviteToken).filter_by(token=token_string).one_or_none()
    if token is None:
        raise BindError("invalid token")
    if token.used_at is not None:
        raise BindError("token already used")
    if token.expires_at < datetime.now(timezone.utc):
        raise BindError("token expired")
    if db.query(User).filter_by(username=username).first() is not None:
        raise ValidationFailed("username already taken")

    user = User(
        username=username,
        display_name=token.intended_display_name,
        password_hash=hash_password(password),
        role=token.intended_role,
    )
    db.add(user)
    db.flush()

    token.used_at = datetime.now(timezone.utc)
    token.used_by_user_id = user.id

    # If both invite tokens are used, create the Couple record
    used_tokens = db.query(InviteToken).filter(InviteToken.used_at.isnot(None)).all()
    if len(used_tokens) == 2 and db.query(Couple).first() is None:
        a_id, b_id = sorted(t.used_by_user_id for t in used_tokens)
        db.add(Couple(user_a_id=a_id, user_b_id=b_id))

    db.flush()
    return user
```

- [ ] **Step 5: Implement `app/modules/auth/router.py`**

```python
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import ValidationFailed
from app.modules.auth.schemas import BindRequest
from app.modules.auth.service import bind_user

router = APIRouter(tags=["auth"])


@router.post("/bind")
def bind(
    token: str,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    try:
        data = BindRequest(username=username, password=password)
    except ValidationError as e:
        raise ValidationFailed(str(e)) from e
    bind_user(db, token_string=token, username=data.username, password=data.password)
    db.commit()
    return RedirectResponse(url="/login?bound=1", status_code=303)
```

- [ ] **Step 6: Mount router in `app/main.py`**

Add to imports:
```python
from app.modules.auth.router import router as auth_router
```

After `register_exception_handlers(app)`:
```python
app.include_router(auth_router)
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_auth/test_bind.py -v
```
Expected: 5 passed.

- [ ] **Step 8: Commit**

```bash
git add app/modules/auth/schemas.py app/modules/auth/service.py app/modules/auth/router.py app/main.py tests/test_auth/test_bind.py
git commit -m "feat(auth): /bind endpoint creates user and auto-creates couple when both bound"
```

---

### Task 13: Session model + service (server-side)

**Files:**
- Modify: `app/modules/auth/models.py` (add `Session` model — renamed to `UserSession` to avoid SQLAlchemy collision)
- Create: `app/modules/auth/sessions.py`
- Create: `tests/test_auth/test_sessions.py`
- Run: alembic autogen + upgrade

- [ ] **Step 1: Write failing test `tests/test_auth/test_sessions.py`**

```python
from datetime import datetime, timedelta, timezone

from app.modules.auth.models import User, UserRole, UserSession
from app.modules.auth.sessions import (
    create_session, get_active_session, destroy_session, touch_session,
)


def _make_user(db) -> User:
    u = User(username="u", display_name="U", password_hash="x", role=UserRole.HE)
    db.add(u); db.flush()
    return u


def test_create_session_returns_token_and_persists(db):
    u = _make_user(db)
    token, expires = create_session(db, user_id=u.id, ip="1.2.3.4", ua="pytest")
    assert len(token) >= 32
    assert expires > datetime.now(timezone.utc)
    s = db.query(UserSession).filter_by(token=token).one()
    assert s.user_id == u.id
    assert s.revoked_at is None


def test_get_active_session_returns_session_for_valid_token(db):
    u = _make_user(db)
    token, _ = create_session(db, user_id=u.id, ip="x", ua="x")
    s = get_active_session(db, token=token)
    assert s is not None and s.user_id == u.id


def test_get_active_session_none_for_expired(db):
    u = _make_user(db)
    s = UserSession(
        token="EXPIRED-TOKEN-VALUE-12345",
        user_id=u.id,
        ip="x", ua="x",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db.add(s); db.flush()
    assert get_active_session(db, token=s.token) is None


def test_destroy_session_revokes(db):
    u = _make_user(db)
    token, _ = create_session(db, user_id=u.id, ip="x", ua="x")
    destroy_session(db, token=token)
    assert get_active_session(db, token=token) is None


def test_touch_extends_expiry(db):
    u = _make_user(db)
    token, exp_before = create_session(db, user_id=u.id, ip="x", ua="x")
    s = db.query(UserSession).filter_by(token=token).one()
    s.expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.flush()
    touch_session(db, session=s)
    db.flush()
    assert s.expires_at > exp_before
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/Scripts/python.exe -m pytest tests/test_auth/test_sessions.py -v
```
Expected: ImportError.

- [ ] **Step 3: Append `UserSession` model to `app/modules/auth/models.py`**

```python
class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    ip: Mapped[str] = mapped_column(String(45), nullable=False)
    ua: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 4: Implement `app/modules/auth/sessions.py`**

```python
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.modules.auth.models import UserSession

_settings = get_settings()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_session(
    db: Session, *, user_id: int, ip: str, ua: str,
) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    expires = _now() + timedelta(days=_settings.session_max_age_days)
    s = UserSession(
        token=token, user_id=user_id, ip=ip, ua=ua[:512], expires_at=expires,
    )
    db.add(s)
    db.flush()
    return token, expires


def get_active_session(db: Session, *, token: str) -> UserSession | None:
    s = db.query(UserSession).filter_by(token=token).one_or_none()
    if s is None or s.revoked_at is not None or s.expires_at <= _now():
        return None
    return s


def destroy_session(db: Session, *, token: str) -> None:
    s = db.query(UserSession).filter_by(token=token).one_or_none()
    if s is not None:
        s.revoked_at = _now()
        db.flush()


def touch_session(db: Session, *, session: UserSession) -> None:
    """Sliding expiration: bump last_seen and extend expiry."""
    now = _now()
    session.last_seen_at = now
    session.expires_at = now + timedelta(days=_settings.session_max_age_days)
```

- [ ] **Step 5: Autogenerate + apply migration**

```bash
.venv/Scripts/python.exe -m alembic revision --autogenerate -m "user sessions"
.venv/Scripts/python.exe -m alembic upgrade head
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_auth/test_sessions.py -v
```
Expected: 5 passed.

- [ ] **Step 7: Commit**

```bash
git add app/modules/auth/models.py app/modules/auth/sessions.py alembic/versions/ tests/test_auth/test_sessions.py
git commit -m "feat(auth): server-side UserSession with sliding expiration"
```

---

### Task 14: Login / Logout endpoints + auth dependency

**Files:**
- Modify: `app/modules/auth/service.py` (add `authenticate`)
- Modify: `app/modules/auth/router.py` (add `/login`, `/logout`)
- Create: `app/deps.py` (current_user dependency)
- Create: `tests/test_auth/test_login.py`

- [ ] **Step 1: Write failing test `tests/test_auth/test_login.py`**

```python
from app.modules.auth.invite import init_couple_invites


def _bind_pair(client, db):
    he, she = init_couple_invites(db, he_display="Bob", she_display="Alice", ttl_days=7)
    db.commit()
    client.post(f"/bind?token={he.token}",
                data={"username": "bob", "password": "secret-pw-1"})
    client.post(f"/bind?token={she.token}",
                data={"username": "alice", "password": "secret-pw-2"})


def test_login_sets_session_cookie(client, db):
    _bind_pair(client, db)
    r = client.post("/login", data={"username": "bob", "password": "secret-pw-1"},
                    follow_redirects=False)
    assert r.status_code in (302, 303)
    assert "cdsid" in r.cookies


def test_login_wrong_password_returns_401(client, db):
    _bind_pair(client, db)
    r = client.post("/login", data={"username": "bob", "password": "wrong"})
    assert r.status_code == 401


def test_logout_clears_cookie(client, db):
    _bind_pair(client, db)
    client.post("/login", data={"username": "bob", "password": "secret-pw-1"})
    r = client.post("/logout", follow_redirects=False)
    assert r.status_code in (302, 303)


def test_unauthenticated_request_to_protected_route_redirects(client, db):
    # /me will exist later; meanwhile use a probe added below
    r = client.get("/_probe/me", follow_redirects=False)
    assert r.status_code in (302, 303)
```

- [ ] **Step 2: Add `authenticate` to `app/modules/auth/service.py`**

```python
from app.modules.auth.passwords import verify_password
from app.modules.auth.models import User


def authenticate(db: Session, *, username: str, password: str) -> User | None:
    user = db.query(User).filter_by(username=username).one_or_none()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
```

- [ ] **Step 3: Extend `app/modules/auth/router.py`** — append:

```python
from fastapi import Request, Response
from app.config import get_settings
from app.modules.auth.service import authenticate
from app.modules.auth.sessions import create_session, destroy_session

_cfg = get_settings()


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    user = authenticate(db, username=username, password=password)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid credentials")
    token, expires = create_session(
        db,
        user_id=user.id,
        ip=request.client.host if request.client else "",
        ua=request.headers.get("user-agent", "")[:512],
    )
    db.commit()
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key=_cfg.session_cookie_name,
        value=token,
        httponly=True,
        secure=_cfg.cookie_secure,
        samesite="lax",
        max_age=_cfg.session_max_age_days * 86400,
        path="/",
    )
    return response


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    token = request.cookies.get(_cfg.session_cookie_name)
    if token:
        destroy_session(db, token=token)
        db.commit()
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(_cfg.session_cookie_name, path="/")
    return response
```

- [ ] **Step 4: Implement `app/deps.py`**

```python
from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.modules.auth.models import Couple, User
from app.modules.auth.sessions import get_active_session, touch_session

_cfg = get_settings()


class AuthRequired(HTTPException):
    """Raised when an unauthenticated user hits a protected route.
    Converted to a 303 redirect by middleware/handler below.
    """
    def __init__(self) -> None:
        super().__init__(status_code=401, detail="auth required")


def current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    token = request.cookies.get(_cfg.session_cookie_name)
    if not token:
        raise AuthRequired()
    s = get_active_session(db, token=token)
    if s is None:
        raise AuthRequired()
    user = db.query(User).get(s.user_id)
    if user is None:
        raise AuthRequired()
    touch_session(db, session=s)
    return user


def current_partner(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> User | None:
    couple = db.query(Couple).first()
    if couple is None:
        return None
    other_id = couple.user_b_id if couple.user_a_id == user.id else couple.user_a_id
    return db.query(User).get(other_id)
```

- [ ] **Step 5: Add probe route + AuthRequired handler in `app/main.py`**

After `register_exception_handlers(app)`, add:

```python
from app.deps import AuthRequired, current_user
from app.modules.auth.models import User
from fastapi import Depends
from fastapi.responses import RedirectResponse


@app.exception_handler(AuthRequired)
async def auth_required_handler(request, exc):  # type: ignore[no-untyped-def]
    return RedirectResponse(url="/login", status_code=303)


@app.get("/_probe/me")
def probe_me(user: User = Depends(current_user)) -> dict[str, object]:
    return {"id": user.id, "username": user.username, "role": user.role.value}
```

(The `_probe/me` route exists only to test the auth dependency. It stays for now; will be deleted when the real `/me` page lands in T48.)

- [ ] **Step 6: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_auth/test_login.py -v
```
Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add app/modules/auth/service.py app/modules/auth/router.py app/deps.py app/main.py tests/test_auth/test_login.py
git commit -m "feat(auth): /login and /logout with session cookies and current_user dep"
```

---

### Task 15: Login rate limiting (slowapi)

**Files:**
- Modify: `app/main.py` (initialize Limiter)
- Modify: `app/modules/auth/router.py` (apply `@limiter.limit` to `/login`)
- Create: `tests/test_auth/test_login_rate_limit.py`

- [ ] **Step 1: Write failing test `tests/test_auth/test_login_rate_limit.py`**

```python
def test_login_rate_limit_per_ip(client, db):
    from app.modules.auth.invite import init_couple_invites
    he, _ = init_couple_invites(db, he_display="B", she_display="A", ttl_days=7)
    db.commit()
    client.post(f"/bind?token={he.token}",
                data={"username": "bob", "password": "secret-pw-1"})

    # 20 failed attempts in quick succession from same IP
    statuses = []
    for _ in range(25):
        r = client.post("/login", data={"username": "bob", "password": "wrong"})
        statuses.append(r.status_code)
    # First batch returns 401; eventually rate-limit returns 429
    assert 429 in statuses, f"expected 429 in {statuses}"
```

- [ ] **Step 2: Initialize Limiter in `app/main.py`**

Add to imports:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
```

Before `app = FastAPI(...)`, add:
```python
limiter = Limiter(key_func=get_remote_address)
```

After `app = FastAPI(...)`, add:
```python
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

- [ ] **Step 3: Decorate `/login` in `app/modules/auth/router.py`**

Add to imports:
```python
from app.main import limiter
```

(Circular import — to avoid this, instead pass limiter via dependency or move to a separate module. Use the safer pattern: import inside the router using lazy import OR define limiter in `app/rate_limit.py`.)

**Better approach**: create `app/rate_limit.py`:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])
```

Then in `app/main.py`:
```python
from app.rate_limit import limiter
# ... use limiter as before
```

In `app/modules/auth/router.py`, add:
```python
from app.rate_limit import limiter
```

And decorate `/login`:
```python
@router.post("/login")
@limiter.limit("20/5minutes")
def login(request: Request, ...):
    ...
```

(Note: slowapi requires the route handler to accept `request: Request` as the first arg, which `/login` already does.)

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/Scripts/python.exe -m pytest tests/test_auth/test_login_rate_limit.py -v
```
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add app/rate_limit.py app/main.py app/modules/auth/router.py tests/test_auth/test_login_rate_limit.py
git commit -m "feat(auth): per-IP rate limit on /login (20 per 5 minutes)"
```

---

**End of Phase B.** A user can SSH in, run `couple-diary init-couple --he Bob --she Alice`, both partners bind via `/bind?token=`, login at `/login`, get a session cookie, and the auth dependency protects routes. Login is rate-limited.

---

## Phase C — UI Foundation (Templates, Theme, Static Assets, Error Pages)

### Task 16: Jinja base layout + Flo pink theme CSS

**Files:**
- Create: `app/templates/base.html`
- Create: `app/static/css/theme.css`
- Create: `app/static/manifest.webmanifest`
- Modify: `app/main.py` (mount static + Jinja env)

- [ ] **Step 1: Create `app/static/css/theme.css`**

```css
:root {
  --bg: #fce7e9;
  --surface: #ffffff;
  --surface-2: #fff5f7;
  --text: #1a1a2e;
  --text-muted: #888;
  --accent: #ff7a9c;
  --accent-2: #d63673;
  --accent-soft: #ffe4ec;
  --danger: #e74c3c;
  --ok: #2ecc71;
  --radius: 16px;
  --radius-pill: 999px;
  --shadow-card: 0 4px 16px rgba(255, 150, 180, 0.15);
  --font: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
          "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; font-family: var(--font); color: var(--text);
             background: var(--bg); -webkit-font-smoothing: antialiased; }
a { color: var(--accent-2); text-decoration: none; }
button { font: inherit; cursor: pointer; }
.container { max-width: 720px; margin: 0 auto; padding: 16px; padding-bottom: 88px; }
.card { background: var(--surface); border-radius: var(--radius);
        box-shadow: var(--shadow-card); padding: 16px; margin-bottom: 16px; }
.card-title { font-weight: 700; margin: 0 0 8px; font-size: 16px; }
.pill { display: inline-flex; align-items: center; gap: 6px;
        padding: 6px 14px; border-radius: var(--radius-pill);
        background: var(--accent-soft); color: var(--accent-2);
        font-size: 13px; font-weight: 500; border: none; transition: transform .1s; }
.pill[aria-pressed="true"] { background: var(--accent); color: white; }
.pill:active { transform: scale(0.96); }
.btn { padding: 10px 18px; border-radius: var(--radius-pill);
       background: var(--accent); color: white; border: none; font-weight: 600; }
.btn-ghost { background: transparent; color: var(--accent-2); border: 1px solid var(--accent); }
.input { width: 100%; padding: 12px 16px; border-radius: var(--radius);
         border: 1px solid #f0d4dc; background: white; font: inherit; }
.input:focus { outline: 2px solid var(--accent); outline-offset: -1px; }
.error { color: var(--danger); font-size: 13px; margin-top: 4px; }
.subtitle { color: var(--text-muted); font-size: 13px; margin: 0; }

/* Bottom nav (mobile) */
.bottom-nav { position: fixed; bottom: 0; left: 0; right: 0; background: white;
              border-top: 1px solid var(--accent-soft); display: flex;
              justify-content: space-around; padding: 8px 0;
              padding-bottom: max(8px, env(safe-area-inset-bottom)); z-index: 100; }
.bottom-nav a { color: var(--text-muted); font-size: 11px; display: flex;
                flex-direction: column; align-items: center; gap: 2px; padding: 4px 12px; }
.bottom-nav a.active { color: var(--accent-2); }
.bottom-nav .icon { font-size: 22px; }
.bottom-nav .central { background: var(--accent); color: white;
                       border-radius: 50%; width: 56px; height: 56px;
                       margin-top: -20px; box-shadow: var(--shadow-card);
                       display: flex; align-items: center; justify-content: center; }

/* Desktop sidebar */
@media (min-width: 900px) {
  .bottom-nav { left: 0; right: auto; top: 0; bottom: 0; width: 220px;
                flex-direction: column; justify-content: flex-start;
                border-top: none; border-right: 1px solid var(--accent-soft);
                padding: 24px 12px; gap: 4px; }
  .bottom-nav a { flex-direction: row; gap: 12px; font-size: 14px;
                  width: 100%; padding: 12px 16px; border-radius: var(--radius); }
  .bottom-nav .central { margin: 8px 0; }
  .container { margin-left: 240px; padding: 24px; padding-bottom: 24px; }
}
```

- [ ] **Step 2: Create `app/static/manifest.webmanifest`**

```json
{
  "name": "Couple Diary",
  "short_name": "Couple",
  "description": "Private two-person diary",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#fce7e9",
  "theme_color": "#ff7a9c",
  "icons": [
    { "src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

- [ ] **Step 3: Create placeholder icons directory**

```bash
mkdir -p app/static/icons
```

(Real PNG icons can be generated later via any tool — leave directory ready.)

- [ ] **Step 4: Create `app/templates/base.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{% block title %}Couple Diary{% endblock %}</title>
  <link rel="manifest" href="/static/manifest.webmanifest">
  <meta name="theme-color" content="#ff7a9c">
  <link rel="stylesheet" href="/static/css/theme.css">
  <script src="/static/js/htmx.min.js" defer></script>
  <script src="/static/js/alpine.min.js" defer></script>
  <script src="/static/js/app.js" defer></script>
  {% block head %}{% endblock %}
</head>
<body>
  <div class="container">
    {% block content %}{% endblock %}
  </div>
  {% if request.scope.get("user") %}
    {% include "components/nav.html" %}
  {% endif %}
</body>
</html>
```

- [ ] **Step 5: Mount static files and templates in `app/main.py`**

Add to imports:
```python
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
```

After `app = FastAPI(...)`:
```python
_static_dir = Path(__file__).parent / "static"
_templates_dir = Path(__file__).parent / "templates"
app.mount("/static", StaticFiles(directory=_static_dir), name="static")
templates = Jinja2Templates(directory=_templates_dir)
```

- [ ] **Step 6: Manual smoke check**

```bash
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8001
```
Visit `http://127.0.0.1:8001/static/css/theme.css` → should return CSS.
Visit `http://127.0.0.1:8001/static/manifest.webmanifest` → should return JSON.
Ctrl+C.

- [ ] **Step 7: Commit**

```bash
git add app/templates/ app/static/ app/main.py
git commit -m "feat(ui): base Jinja layout with Flo pink theme and PWA manifest"
```

---

### Task 17: Vendor HTMX + Alpine + CSRF interceptor

**Files:**
- Create: `app/static/js/htmx.min.js` (download)
- Create: `app/static/js/alpine.min.js` (download)
- Create: `app/static/js/app.js`

- [ ] **Step 1: Download HTMX 1.9.x**

```bash
mkdir -p app/static/js
curl -fsSL https://unpkg.com/htmx.org@1.9.12/dist/htmx.min.js -o app/static/js/htmx.min.js
```

Expected: `app/static/js/htmx.min.js` ~50 KB.

- [ ] **Step 2: Download Alpine.js 3.14.x**

```bash
curl -fsSL https://unpkg.com/alpinejs@3.14.1/dist/cdn.min.js -o app/static/js/alpine.min.js
```

Expected: `app/static/js/alpine.min.js` ~40 KB.

- [ ] **Step 3: Create `app/static/js/app.js`**

```javascript
// Inject CSRF token from meta tag into all HTMX POST/PUT/DELETE requests
document.addEventListener("DOMContentLoaded", () => {
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (!meta) return;
  const token = meta.getAttribute("content");
  document.body.addEventListener("htmx:configRequest", (e) => {
    if (["POST", "PUT", "DELETE", "PATCH"].includes(e.detail.verb.toUpperCase())) {
      e.detail.headers["X-CSRF-Token"] = token;
    }
  });
});

// Show subtle visual error toast on htmx errors
document.body.addEventListener("htmx:responseError", (e) => {
  const t = document.createElement("div");
  t.textContent = "操作失败，请重试";
  t.style.cssText = "position:fixed;bottom:80px;left:50%;transform:translateX(-50%);" +
    "background:#e74c3c;color:white;padding:10px 18px;border-radius:999px;z-index:200;";
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2500);
});
```

- [ ] **Step 4: Manual check**

Restart `uvicorn app.main:app --port 8001`, open `http://127.0.0.1:8001/static/js/htmx.min.js` → returns JS. Same for `alpine.min.js`, `app.js`.

- [ ] **Step 5: Commit**

```bash
git add app/static/js/
git commit -m "chore(ui): vendor HTMX 1.9 and Alpine 3.14, add CSRF interceptor"
```

---

### Task 18: Login + Bind page templates

**Files:**
- Create: `app/templates/pages/login.html`
- Create: `app/templates/pages/bind.html`
- Modify: `app/modules/auth/router.py` (add GET `/login` and GET `/bind` that render HTML)
- Modify: `app/modules/auth/router.py` (POST `/login` returns redirect, on error renders login.html with banner)
- Create: `tests/test_auth/test_login_html.py`

- [ ] **Step 1: Write failing test `tests/test_auth/test_login_html.py`**

```python
def test_get_login_renders_form(client):
    r = client.get("/login")
    assert r.status_code == 200
    assert "登录" in r.text or "Login" in r.text
    assert '<input' in r.text and 'name="username"' in r.text


def test_get_bind_with_valid_token_renders_form(client, db):
    from app.modules.auth.invite import init_couple_invites
    he, _ = init_couple_invites(db, he_display="Bob", she_display="A", ttl_days=7)
    db.commit()
    r = client.get(f"/bind?token={he.token}")
    assert r.status_code == 200
    assert "Bob" in r.text  # display name preview


def test_get_bind_with_invalid_token_shows_error(client):
    r = client.get("/bind?token=NOPE-NONE")
    assert r.status_code == 400
```

- [ ] **Step 2: Create `app/templates/pages/login.html`**

```html
{% extends "base.html" %}
{% block title %}登录 · Couple Diary{% endblock %}
{% block content %}
<div style="min-height:80vh;display:flex;flex-direction:column;justify-content:center">
  <h1 style="text-align:center;margin-bottom:8px">Couple Diary</h1>
  <p class="subtitle" style="text-align:center;margin-bottom:32px">登录</p>

  {% if error %}
    <div class="card" style="border:1px solid var(--danger);color:var(--danger)">
      {{ error }}
    </div>
  {% elif request.query_params.get("bound") %}
    <div class="card" style="border:1px solid var(--ok);color:var(--ok)">
      绑定成功，请用刚设置的账号登录
    </div>
  {% endif %}

  <form method="post" action="/login" class="card">
    <label class="subtitle">用户名</label>
    <input class="input" name="username" autocomplete="username" required autofocus>
    <div style="height:12px"></div>
    <label class="subtitle">密码</label>
    <input class="input" name="password" type="password"
           autocomplete="current-password" required>
    <div style="height:16px"></div>
    <button class="btn" type="submit" style="width:100%">登录</button>
  </form>
</div>
{% endblock %}
```

- [ ] **Step 3: Create `app/templates/pages/bind.html`**

```html
{% extends "base.html" %}
{% block title %}绑定账号 · Couple Diary{% endblock %}
{% block content %}
<div style="min-height:80vh;display:flex;flex-direction:column;justify-content:center">
  <h1 style="text-align:center;margin-bottom:8px">设置你的账号</h1>
  <p class="subtitle" style="text-align:center;margin-bottom:32px">
    你将以 <strong>{{ token.intended_display_name }}</strong>
    （{{ "她" if token.intended_role.value == "she" else "他" }}）的身份加入
  </p>

  {% if error %}
    <div class="card" style="border:1px solid var(--danger);color:var(--danger)">
      {{ error }}
    </div>
  {% endif %}

  <form method="post" action="/bind?token={{ token.token }}" class="card">
    <label class="subtitle">用户名（仅你登录用，2-64 字母数字）</label>
    <input class="input" name="username" pattern="[A-Za-z0-9_-]{2,64}" required autofocus>
    <div style="height:12px"></div>
    <label class="subtitle">密码（至少 8 位）</label>
    <input class="input" name="password" type="password" minlength="8" required>
    <div style="height:16px"></div>
    <button class="btn" type="submit" style="width:100%">设置密码并登录</button>
  </form>
</div>
{% endblock %}
```

- [ ] **Step 4: Add GET routes to `app/modules/auth/router.py`**

Add to imports at top:
```python
from fastapi import Request
from app.main import templates  # will cause circular import — use lazy import inside fn
```

To avoid circular imports, instead extract `templates` into its own module. Create `app/templates_env.py`:

```python
from pathlib import Path
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
```

Update `app/main.py` to import from there:
```python
from app.templates_env import templates  # noqa: F401  - re-exported for tests
```
(Delete the previous `templates = Jinja2Templates(...)` line in main.py.)

Then in `app/modules/auth/router.py` add:
```python
from app.templates_env import templates
from datetime import datetime, timezone
from app.modules.auth.models import InviteToken
from fastapi.responses import HTMLResponse


@router.get("/login")
def login_page(request: Request, error: str | None = None) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "pages/login.html", {"error": error},
    )


@router.get("/bind")
def bind_page(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    t = db.query(InviteToken).filter_by(token=token).one_or_none()
    if t is None or t.used_at is not None or t.expires_at < datetime.now(timezone.utc):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="invalid or expired token")
    return templates.TemplateResponse(
        request, "pages/bind.html", {"token": t},
    )
```

Also update the existing `POST /login` to catch `HTTPException 401` and re-render the login page with an inline error instead of bare JSON. Modify the POST `/login` body:

```python
@router.post("/login")
@limiter.limit("20/5minutes")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = authenticate(db, username=username, password=password)
    if user is None:
        return templates.TemplateResponse(
            request, "pages/login.html",
            {"error": "用户名或密码错误"},
            status_code=401,
        )
    token, _ = create_session(
        db,
        user_id=user.id,
        ip=request.client.host if request.client else "",
        ua=request.headers.get("user-agent", "")[:512],
    )
    db.commit()
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key=_cfg.session_cookie_name, value=token,
        httponly=True, secure=_cfg.cookie_secure, samesite="lax",
        max_age=_cfg.session_max_age_days * 86400, path="/",
    )
    return response
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_auth/ -v
```
Expected: all auth tests still pass plus the 3 new ones.

- [ ] **Step 6: Commit**

```bash
git add app/templates_env.py app/templates/pages/ app/modules/auth/router.py app/main.py tests/test_auth/test_login_html.py
git commit -m "feat(ui): login and bind page templates with inline error rendering"
```

---

### Task 19: Bottom nav / sidebar component

**Files:**
- Create: `app/templates/components/nav.html`
- Modify: `app/deps.py` (attach user to request.scope so base.html can detect)

- [ ] **Step 1: Create `app/templates/components/nav.html`**

```html
<nav class="bottom-nav">
  <a href="/" class="{% if request.url.path == '/' %}active{% endif %}">
    <span class="icon">🏠</span><span>今天</span>
  </a>
  <a href="/calendar"
     class="{% if request.url.path.startswith('/calendar') %}active{% endif %}">
    <span class="icon">📅</span><span>日历</span>
  </a>
  <a href="/log/today" class="central"
     aria-label="记录今天">
    <span class="icon">＋</span>
  </a>
  <a href="/diary"
     class="{% if request.url.path.startswith('/diary') %}active{% endif %}">
    <span class="icon">📓</span><span>日记</span>
  </a>
  <a href="/me"
     class="{% if request.url.path.startswith('/me') %}active{% endif %}">
    <span class="icon">👥</span><span>我们</span>
  </a>
</nav>
```

(Trip nav added in M2.)

- [ ] **Step 2: Make `current_user` attach to request.scope when present**

In `app/deps.py`, modify `current_user` to set `request.scope["user"] = user` before returning:

```python
def current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    ...
    request.scope["user"] = user
    return user
```

- [ ] **Step 3: No test required for nav rendering at this point** (will be exercised by today.html test in Phase H).

- [ ] **Step 4: Commit**

```bash
git add app/templates/components/nav.html app/deps.py
git commit -m "feat(ui): bottom nav / sidebar component (responsive)"
```

---

### Task 20: Custom 404 / 403 / 500 templates

**Files:**
- Create: `app/templates/pages/404.html`
- Create: `app/templates/pages/403.html`
- Create: `app/templates/pages/500.html`
- Modify: `app/main.py` (custom handlers for 404 / 500; map Forbidden → 403 template via AppError handler enhancement)
- Create: `tests/test_error_pages.py`

- [ ] **Step 1: Write failing test `tests/test_error_pages.py`**

```python
def test_404_for_missing_route_returns_html_for_browser(client):
    r = client.get("/this-route-does-not-exist",
                   headers={"Accept": "text/html"})
    assert r.status_code == 404
    assert "找不到" in r.text or "404" in r.text


def test_404_for_missing_route_returns_json_for_api(client):
    r = client.get("/this-route-does-not-exist",
                   headers={"Accept": "application/json"})
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")
```

- [ ] **Step 2: Create `app/templates/pages/404.html`**

```html
{% extends "base.html" %}
{% block title %}找不到 · Couple Diary{% endblock %}
{% block content %}
<div style="text-align:center;padding:80px 0">
  <h1 style="font-size:48px;margin:0">404</h1>
  <p class="subtitle" style="margin-top:8px">这个页面不存在</p>
  <p style="margin-top:24px"><a class="btn" href="/">回首页</a></p>
</div>
{% endblock %}
```

- [ ] **Step 3: Create `app/templates/pages/403.html`**

```html
{% extends "base.html" %}
{% block title %}没权限 · Couple Diary{% endblock %}
{% block content %}
<div style="text-align:center;padding:80px 0">
  <h1 style="font-size:48px;margin:0">403</h1>
  <p class="subtitle" style="margin-top:8px">没有权限查看</p>
  <p style="margin-top:24px"><a class="btn" href="/">回首页</a></p>
</div>
{% endblock %}
```

- [ ] **Step 4: Create `app/templates/pages/500.html`**

```html
{% extends "base.html" %}
{% block title %}出错了 · Couple Diary{% endblock %}
{% block content %}
<div style="text-align:center;padding:80px 0">
  <h1 style="font-size:48px;margin:0">500</h1>
  <p class="subtitle" style="margin-top:8px">服务器出错了，已记录</p>
  <p style="margin-top:24px"><a class="btn" href="/">回首页</a></p>
</div>
{% endblock %}
```

- [ ] **Step 5: Modify `app/errors.py`** — render HTML when client wants HTML:

Replace `register_exception_handlers` body with:

```python
def register_exception_handlers(app: FastAPI) -> None:
    from fastapi.responses import HTMLResponse
    from starlette.exceptions import HTTPException as StarletteHTTPException
    from app.templates_env import templates

    def _wants_html(request: Request) -> bool:
        accept = request.headers.get("accept", "")
        return "text/html" in accept and "application/json" not in accept

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):  # type: ignore[no-untyped-def]
        log.warning("app_error", extra={"code": exc.code, "path": request.url.path})
        if _wants_html(request) and exc.http_status in (403, 404, 500):
            tpl = {403: "pages/403.html", 404: "pages/404.html",
                   500: "pages/500.html"}[exc.http_status]
            return templates.TemplateResponse(request, tpl, {}, status_code=exc.http_status)
        return JSONResponse(
            status_code=exc.http_status,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404 and _wants_html(request):
            return templates.TemplateResponse(request, "pages/404.html", {}, status_code=404)
        if exc.status_code == 403 and _wants_html(request):
            return templates.TemplateResponse(request, "pages/403.html", {}, status_code=403)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": "http_error", "message": str(exc.detail)}},
        )

    @app.exception_handler(Exception)
    async def fallback_500(request: Request, exc: Exception):
        log.exception("unhandled_exception", extra={"path": request.url.path})
        if _wants_html(request):
            return templates.TemplateResponse(request, "pages/500.html", {}, status_code=500)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "internal error"}},
        )
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_error_pages.py tests/test_errors.py -v
```
Expected: all 5 pass.

- [ ] **Step 7: Commit**

```bash
git add app/templates/pages/ app/errors.py tests/test_error_pages.py
git commit -m "feat(ui): custom 404/403/500 pages with Accept-aware HTML/JSON rendering"
```

---

**End of Phase C.** UI scaffolding is in place: theme, layout, vendored JS, login/bind pages, nav component, error pages.

---

## Phase D — Cycle Domain (Periods, BBT, Predictor)

### Task 21: Period + CycleSettings models

**Files:**
- Create: `app/modules/cycle/__init__.py`
- Create: `app/modules/cycle/models.py`
- Modify: `app/modules/__init__.py` (re-export `cycle`)
- Create: `tests/test_cycle/__init__.py`
- Create: `tests/test_cycle/test_models.py`
- Migration

- [ ] **Step 1: Create `tests/test_cycle/__init__.py`** (empty)

- [ ] **Step 2: Write failing test `tests/test_cycle/test_models.py`**

```python
from datetime import date

from app.modules.auth.models import User, UserRole
from app.modules.cycle.models import CycleSettings, Period


def _user(db) -> User:
    u = User(username="alice", display_name="Alice", password_hash="x", role=UserRole.SHE)
    db.add(u); db.flush()
    return u


def test_period_persistable(db):
    u = _user(db)
    p = Period(user_id=u.id, start_date=date(2026, 5, 1), end_date=date(2026, 5, 5))
    db.add(p); db.flush()
    assert p.id is not None


def test_period_user_start_unique(db):
    u = _user(db)
    db.add(Period(user_id=u.id, start_date=date(2026, 5, 1)))
    db.flush()
    db.add(Period(user_id=u.id, start_date=date(2026, 5, 1)))
    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        db.flush()


def test_cycle_settings_defaults(db):
    u = _user(db)
    s = CycleSettings(user_id=u.id)
    db.add(s); db.flush()
    assert s.avg_cycle_length == 28
    assert s.avg_period_length == 5
    assert s.mode == "auto"
```

- [ ] **Step 3: Implement `app/modules/cycle/__init__.py`**

```python
from app.modules.cycle import models  # noqa: F401
```

- [ ] **Step 4: Implement `app/modules/cycle/models.py`**

```python
from datetime import date, datetime

from sqlalchemy import (
    Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Period(Base):
    __tablename__ = "periods"
    __table_args__ = (
        UniqueConstraint("user_id", "start_date", name="uq_periods_user_start"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )


class CycleSettings(Base):
    __tablename__ = "cycle_settings"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), primary_key=True,
    )
    avg_cycle_length: Mapped[int] = mapped_column(default=28, nullable=False)
    avg_period_length: Mapped[int] = mapped_column(default=5, nullable=False)
    mode: Mapped[str] = mapped_column(String(16), default="auto", nullable=False)
    # "auto" = recompute from history; "manual" = use stored avgs as-is
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )
```

- [ ] **Step 5: Update `app/modules/__init__.py`**

```python
from app.modules import auth, cycle  # noqa: F401
```

- [ ] **Step 6: Generate + apply migration**

```bash
.venv/Scripts/python.exe -m alembic revision --autogenerate -m "periods and cycle settings"
.venv/Scripts/python.exe -m alembic upgrade head
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_cycle/test_models.py -v
```
Expected: 3 passed.

- [ ] **Step 8: Commit**

```bash
git add app/modules/cycle/ app/modules/__init__.py alembic/versions/ tests/test_cycle/
git commit -m "feat(cycle): Period and CycleSettings models with migration"
```

---

### Task 22: BbtReading model (under `health/` module)

**Files:**
- Create: `app/modules/health/__init__.py`
- Create: `app/modules/health/models.py`
- Modify: `app/modules/__init__.py`
- Create: `tests/test_health/__init__.py`
- Create: `tests/test_health/test_bbt_model.py`
- Migration

- [ ] **Step 1: Create `tests/test_health/__init__.py`** (empty)

- [ ] **Step 2: Write failing test `tests/test_health/test_bbt_model.py`**

```python
from datetime import date, time
from decimal import Decimal

from app.modules.auth.models import User, UserRole
from app.modules.health.models import BbtMethod, BbtReading


def _user(db) -> User:
    u = User(username="alice", display_name="A", password_hash="x", role=UserRole.SHE)
    db.add(u); db.flush()
    return u


def test_bbt_persistable(db):
    u = _user(db)
    r = BbtReading(
        user_id=u.id, date=date(2026, 5, 22),
        temp_c=Decimal("36.55"), measure_time=time(6, 30),
        method=BbtMethod.ORAL,
    )
    db.add(r); db.flush()
    assert r.id is not None


def test_bbt_unique_per_user_per_day(db):
    u = _user(db)
    db.add(BbtReading(user_id=u.id, date=date(2026, 5, 22),
                      temp_c=Decimal("36.5"), method=BbtMethod.ORAL))
    db.flush()
    db.add(BbtReading(user_id=u.id, date=date(2026, 5, 22),
                      temp_c=Decimal("36.6"), method=BbtMethod.ORAL))
    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        db.flush()
```

- [ ] **Step 3: Implement `app/modules/health/__init__.py`**

```python
from app.modules.health import models  # noqa: F401
```

- [ ] **Step 4: Implement `app/modules/health/models.py`**

```python
import enum
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Date, DateTime, Enum as SAEnum, ForeignKey, Numeric, Time, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class BbtMethod(str, enum.Enum):
    ORAL = "oral"
    VAGINAL = "vaginal"
    AXILLARY = "axillary"
    WRIST = "wrist"
    OTHER = "other"


class BbtReading(Base):
    __tablename__ = "bbt_readings"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_bbt_user_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    temp_c: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    measure_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    method: Mapped[BbtMethod] = mapped_column(
        SAEnum(BbtMethod, name="bbt_method"), nullable=False, default=BbtMethod.ORAL,
    )
    notes: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
```

- [ ] **Step 5: Update `app/modules/__init__.py`**

```python
from app.modules import auth, cycle, health  # noqa: F401
```

- [ ] **Step 6: Generate + apply migration**

```bash
.venv/Scripts/python.exe -m alembic revision --autogenerate -m "bbt readings"
.venv/Scripts/python.exe -m alembic upgrade head
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_health/test_bbt_model.py -v
```
Expected: 2 passed.

- [ ] **Step 8: Commit**

```bash
git add app/modules/health/ app/modules/__init__.py alembic/versions/ tests/test_health/
git commit -m "feat(health): BbtReading model with method enum and per-day uniqueness"
```

---

### Task 22b: HealthMetric model (table only, M3 will populate via Apple Health import)

Spec §11 M1 lists `health_metrics` as part of the M1 core tables (created early so the M3 importer doesn't need a separate migration). M1 doesn't write to or read from it — model + migration only.

**Files:**
- Modify: `app/modules/health/models.py` (append `HealthMetric`)
- Create: `tests/test_health/test_health_metric_model.py`
- Migration

- [ ] **Step 1: Write failing test `tests/test_health/test_health_metric_model.py`**

```python
from datetime import date
from decimal import Decimal

from app.modules.auth.models import User, UserRole
from app.modules.health.models import HealthMetric, HealthSource


def _user(db):
    u = User(username="a", display_name="A", password_hash="x", role=UserRole.SHE)
    db.add(u); db.flush()
    return u


def test_health_metric_persistable(db):
    u = _user(db)
    m = HealthMetric(
        user_id=u.id, date=date(2026, 5, 22),
        rhr_bpm=62, hrv_sdnn_ms=Decimal("48.0"),
        sleep_total_min=420, source=HealthSource.MANUAL,
    )
    db.add(m); db.flush()
    assert m.id is not None


def test_health_metric_unique_per_user_date_source(db):
    u = _user(db)
    db.add(HealthMetric(user_id=u.id, date=date(2026, 5, 22),
                        rhr_bpm=60, source=HealthSource.MANUAL))
    db.flush()
    db.add(HealthMetric(user_id=u.id, date=date(2026, 5, 22),
                        rhr_bpm=61, source=HealthSource.MANUAL))
    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        db.flush()


def test_same_date_different_source_ok(db):
    """Manual + Apple Health on same day = two rows."""
    u = _user(db)
    db.add(HealthMetric(user_id=u.id, date=date(2026, 5, 22),
                        rhr_bpm=60, source=HealthSource.MANUAL))
    db.add(HealthMetric(user_id=u.id, date=date(2026, 5, 22),
                        rhr_bpm=61, source=HealthSource.APPLE_HEALTH))
    db.flush()
    assert db.query(HealthMetric).count() == 2
```

- [ ] **Step 2: Append to `app/modules/health/models.py`**

```python
class HealthSource(str, enum.Enum):
    MANUAL = "manual"
    APPLE_HEALTH = "apple_health"
    FLO = "flo"
    OTHER = "other"


class HealthMetric(Base):
    __tablename__ = "health_metrics"
    __table_args__ = (
        UniqueConstraint("user_id", "date", "source",
                         name="uq_health_metrics_user_date_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    rhr_bpm: Mapped[int | None] = mapped_column(nullable=True)
    hrv_sdnn_ms: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    sleep_total_min: Mapped[int | None] = mapped_column(nullable=True)
    sleep_deep_min: Mapped[int | None] = mapped_column(nullable=True)
    sleep_rem_min: Mapped[int | None] = mapped_column(nullable=True)
    source: Mapped[HealthSource] = mapped_column(
        SAEnum(HealthSource, name="health_source"), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
```

(Imports already present in T22: `Numeric`, `UniqueConstraint`, `Date`, `DateTime`, `ForeignKey`, `func`, `enum`, `Decimal`, `Mapped`, `mapped_column`.)

- [ ] **Step 3: Generate + apply migration**

```bash
.venv/Scripts/python.exe -m alembic revision --autogenerate -m "health metrics table"
.venv/Scripts/python.exe -m alembic upgrade head
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_health/test_health_metric_model.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/modules/health/models.py alembic/versions/ tests/test_health/test_health_metric_model.py
git commit -m "feat(health): HealthMetric model + source enum (M3 will populate)"
```

---

### Task 23: Period CRUD service

**Files:**
- Create: `app/modules/cycle/service.py`
- Create: `tests/test_cycle/test_service.py`

- [ ] **Step 1: Write failing test `tests/test_cycle/test_service.py`**

```python
from datetime import date

from app.modules.auth.models import User, UserRole
from app.modules.cycle.models import Period
from app.modules.cycle.service import (
    list_periods, log_period_start, log_period_end, delete_period,
)


def _user(db) -> User:
    u = User(username="a", display_name="A", password_hash="x", role=UserRole.SHE)
    db.add(u); db.flush()
    return u


def test_log_period_start_creates_row(db):
    u = _user(db)
    p = log_period_start(db, user_id=u.id, start_date=date(2026, 5, 1))
    assert p.id is not None
    assert p.end_date is None


def test_log_period_start_idempotent_on_same_date(db):
    u = _user(db)
    a = log_period_start(db, user_id=u.id, start_date=date(2026, 5, 1))
    b = log_period_start(db, user_id=u.id, start_date=date(2026, 5, 1))
    assert a.id == b.id


def test_log_period_end_sets_end_date(db):
    u = _user(db)
    p = log_period_start(db, user_id=u.id, start_date=date(2026, 5, 1))
    log_period_end(db, period_id=p.id, end_date=date(2026, 5, 5))
    refreshed = db.query(Period).get(p.id)
    assert refreshed.end_date == date(2026, 5, 5)


def test_log_period_end_rejects_before_start(db):
    u = _user(db)
    p = log_period_start(db, user_id=u.id, start_date=date(2026, 5, 5))
    import pytest
    with pytest.raises(ValueError):
        log_period_end(db, period_id=p.id, end_date=date(2026, 5, 1))


def test_list_periods_ordered_descending(db):
    u = _user(db)
    log_period_start(db, user_id=u.id, start_date=date(2026, 3, 1))
    log_period_start(db, user_id=u.id, start_date=date(2026, 5, 1))
    log_period_start(db, user_id=u.id, start_date=date(2026, 4, 1))
    rows = list_periods(db, user_id=u.id)
    assert [p.start_date for p in rows] == [
        date(2026, 5, 1), date(2026, 4, 1), date(2026, 3, 1),
    ]


def test_delete_period_removes_row(db):
    u = _user(db)
    p = log_period_start(db, user_id=u.id, start_date=date(2026, 5, 1))
    delete_period(db, period_id=p.id)
    assert db.query(Period).get(p.id) is None
```

- [ ] **Step 2: Implement `app/modules/cycle/service.py`**

```python
from datetime import date
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.errors import NotFound
from app.modules.cycle.models import Period


def log_period_start(db: Session, *, user_id: int, start_date: date) -> Period:
    existing = db.query(Period).filter_by(user_id=user_id, start_date=start_date).one_or_none()
    if existing is not None:
        return existing
    p = Period(user_id=user_id, start_date=start_date)
    db.add(p); db.flush()
    return p


def log_period_end(db: Session, *, period_id: int, end_date: date) -> Period:
    p = db.query(Period).get(period_id)
    if p is None:
        raise NotFound(f"period {period_id} not found")
    if end_date < p.start_date:
        raise ValueError("end_date must be on or after start_date")
    p.end_date = end_date
    db.flush()
    return p


def delete_period(db: Session, *, period_id: int) -> None:
    p = db.query(Period).get(period_id)
    if p is None:
        return
    db.delete(p); db.flush()


def list_periods(
    db: Session, *, user_id: int, limit: int | None = None,
) -> Sequence[Period]:
    q = (db.query(Period)
           .filter_by(user_id=user_id)
           .order_by(Period.start_date.desc()))
    if limit is not None:
        q = q.limit(limit)
    return q.all()
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_cycle/test_service.py -v
```
Expected: 6 passed.

- [ ] **Step 4: Commit**

```bash
git add app/modules/cycle/service.py tests/test_cycle/test_service.py
git commit -m "feat(cycle): period CRUD service with idempotent start logging"
```

---

### Task 24: BBT CRUD service

**Files:**
- Create: `app/modules/health/service.py`
- Create: `tests/test_health/test_bbt_service.py`

- [ ] **Step 1: Write failing test `tests/test_health/test_bbt_service.py`**

```python
from datetime import date, time
from decimal import Decimal

from app.modules.auth.models import User, UserRole
from app.modules.health.models import BbtMethod, BbtReading
from app.modules.health.service import log_bbt, list_bbt_recent, delete_bbt


def _user(db):
    u = User(username="a", display_name="A", password_hash="x", role=UserRole.SHE)
    db.add(u); db.flush()
    return u


def test_log_bbt_creates_or_updates_same_day(db):
    u = _user(db)
    a = log_bbt(db, user_id=u.id, on=date(2026, 5, 22),
                temp_c=Decimal("36.5"), method=BbtMethod.ORAL)
    b = log_bbt(db, user_id=u.id, on=date(2026, 5, 22),
                temp_c=Decimal("36.7"), method=BbtMethod.ORAL)
    assert a.id == b.id
    refreshed = db.query(BbtReading).get(a.id)
    assert refreshed.temp_c == Decimal("36.70")


def test_log_bbt_rejects_out_of_range(db):
    u = _user(db)
    import pytest
    with pytest.raises(ValueError):
        log_bbt(db, user_id=u.id, on=date(2026, 5, 22),
                temp_c=Decimal("42.0"), method=BbtMethod.ORAL)
    with pytest.raises(ValueError):
        log_bbt(db, user_id=u.id, on=date(2026, 5, 22),
                temp_c=Decimal("33.0"), method=BbtMethod.ORAL)


def test_list_bbt_recent_returns_desc(db):
    u = _user(db)
    log_bbt(db, user_id=u.id, on=date(2026, 5, 20),
            temp_c=Decimal("36.4"), method=BbtMethod.ORAL)
    log_bbt(db, user_id=u.id, on=date(2026, 5, 22),
            temp_c=Decimal("36.6"), method=BbtMethod.ORAL)
    log_bbt(db, user_id=u.id, on=date(2026, 5, 21),
            temp_c=Decimal("36.5"), method=BbtMethod.ORAL)
    rows = list_bbt_recent(db, user_id=u.id, days=10)
    assert [r.date for r in rows] == [
        date(2026, 5, 22), date(2026, 5, 21), date(2026, 5, 20),
    ]


def test_delete_bbt_removes_row(db):
    u = _user(db)
    r = log_bbt(db, user_id=u.id, on=date(2026, 5, 22),
                temp_c=Decimal("36.5"), method=BbtMethod.ORAL)
    delete_bbt(db, reading_id=r.id)
    assert db.query(BbtReading).get(r.id) is None
```

- [ ] **Step 2: Implement `app/modules/health/service.py`**

```python
from datetime import date, time, timedelta
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.health.models import BbtMethod, BbtReading

TEMP_MIN = Decimal("35.0")
TEMP_MAX = Decimal("39.0")


def log_bbt(
    db: Session, *, user_id: int, on: date, temp_c: Decimal,
    method: BbtMethod, measure_time: time | None = None,
    notes: str | None = None,
) -> BbtReading:
    if not (TEMP_MIN <= temp_c <= TEMP_MAX):
        raise ValueError(f"temp_c {temp_c} outside plausible range ({TEMP_MIN}-{TEMP_MAX})")
    existing = db.query(BbtReading).filter_by(user_id=user_id, date=on).one_or_none()
    if existing is not None:
        existing.temp_c = temp_c
        existing.measure_time = measure_time
        existing.method = method
        existing.notes = notes
        db.flush()
        return existing
    r = BbtReading(
        user_id=user_id, date=on, temp_c=temp_c, measure_time=measure_time,
        method=method, notes=notes,
    )
    db.add(r); db.flush()
    return r


def list_bbt_recent(
    db: Session, *, user_id: int, days: int = 30,
) -> Sequence[BbtReading]:
    cutoff = date.today() - timedelta(days=days)
    return (db.query(BbtReading)
              .filter(BbtReading.user_id == user_id, BbtReading.date >= cutoff)
              .order_by(BbtReading.date.desc())
              .all())


def delete_bbt(db: Session, *, reading_id: int) -> None:
    r = db.query(BbtReading).get(reading_id)
    if r is None:
        return
    db.delete(r); db.flush()
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_health/test_bbt_service.py -v
```
Expected: 4 passed.

- [ ] **Step 4: Commit**

```bash
git add app/modules/health/service.py tests/test_health/test_bbt_service.py
git commit -m "feat(health): BBT log service with upsert and plausibility range"
```

---

### Task 25: Predictor base + CalendarSignal

**Files:**
- Create: `app/modules/cycle/predictor/__init__.py`
- Create: `app/modules/cycle/predictor/base.py`
- Create: `app/modules/cycle/predictor/calendar.py`
- Create: `tests/test_cycle/test_predictor_calendar.py`

- [ ] **Step 1: Write failing test `tests/test_cycle/test_predictor_calendar.py`**

```python
from datetime import date

from app.modules.auth.models import User, UserRole
from app.modules.cycle.predictor.calendar import CalendarSignal
from app.modules.cycle.service import log_period_start


def _user(db) -> User:
    u = User(username="a", display_name="A", password_hash="x", role=UserRole.SHE)
    db.add(u); db.flush()
    return u


def test_calendar_signal_no_history_low_confidence(db):
    u = _user(db)
    sig = CalendarSignal()
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 5, 22))
    assert r is not None
    assert r.confidence < 0.3
    assert r.predicted_ovulation is None  # cannot predict without history


def test_calendar_signal_with_three_cycles_predicts(db):
    u = _user(db)
    for d in [date(2026, 2, 1), date(2026, 3, 1), date(2026, 4, 1)]:
        log_period_start(db, user_id=u.id, start_date=d)
    sig = CalendarSignal()
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 4, 20))
    assert r.predicted_ovulation is not None
    # cycle ~28-29 days, ovulation = next_start - 14
    expected_next_start = date(2026, 5, 1) + (date(2026, 4, 1) - date(2026, 3, 1))
    assert abs((r.predicted_ovulation - (expected_next_start - __import__("datetime").timedelta(days=14))).days) <= 1
    assert 0.3 <= r.confidence <= 0.65


def test_calendar_signal_six_cycles_higher_confidence(db):
    u = _user(db)
    for d in [date(2025, 12, 1), date(2026, 1, 1), date(2026, 2, 1),
              date(2026, 3, 1), date(2026, 4, 1), date(2026, 5, 1)]:
        log_period_start(db, user_id=u.id, start_date=d)
    sig = CalendarSignal()
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 5, 20))
    assert r.confidence >= 0.5
```

- [ ] **Step 2: Implement `app/modules/cycle/predictor/__init__.py`** (empty for now)

- [ ] **Step 3: Implement `app/modules/cycle/predictor/base.py`**

```python
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class SignalResult:
    source: str
    predicted_ovulation: date | None
    confidence: float  # 0..1
    evidence: str
    extra: dict = field(default_factory=dict)


class Signal(Protocol):
    name: str

    def evaluate(
        self, db: Session, *, user_id: int, target_date: date,
    ) -> SignalResult | None: ...
```

- [ ] **Step 4: Implement `app/modules/cycle/predictor/calendar.py`**

```python
import statistics
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.modules.cycle.models import Period
from app.modules.cycle.predictor.base import Signal, SignalResult

LUTEAL_PHASE_DAYS = 14


class CalendarSignal:
    name = "calendar"

    def evaluate(
        self, db: Session, *, user_id: int, target_date: date,
    ) -> SignalResult | None:
        starts: list[date] = [
            p.start_date
            for p in (
                db.query(Period)
                  .filter(Period.user_id == user_id, Period.start_date <= target_date)
                  .order_by(Period.start_date.asc())
                  .all()
            )
        ]
        if not starts:
            return SignalResult(
                source=self.name,
                predicted_ovulation=None,
                confidence=0.0,
                evidence="无经期记录",
            )

        if len(starts) < 2:
            return SignalResult(
                source=self.name,
                predicted_ovulation=None,
                confidence=0.1,
                evidence="数据不足（<2 次经期）",
            )

        recent = starts[-6:]
        diffs = [(recent[i + 1] - recent[i]).days for i in range(len(recent) - 1)]
        avg_cycle = round(statistics.mean(diffs))
        std = statistics.pstdev(diffs) if len(diffs) > 1 else 0.0
        next_start = recent[-1] + timedelta(days=avg_cycle)
        ovulation = next_start - timedelta(days=LUTEAL_PHASE_DAYS)

        n = len(diffs)
        if n < 2:
            confidence = 0.2
        elif n < 5:
            confidence = 0.45
        else:
            confidence = 0.6
        return SignalResult(
            source=self.name,
            predicted_ovulation=ovulation,
            confidence=confidence,
            evidence=f"基于 {n+1} 次经期，平均 {avg_cycle} 天 (±{std:.1f})",
            extra={"avg_cycle": avg_cycle, "next_start": next_start, "std": std},
        )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_cycle/test_predictor_calendar.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add app/modules/cycle/predictor/ tests/test_cycle/test_predictor_calendar.py
git commit -m "feat(cycle): CalendarSignal predictor with confidence based on history length"
```

---

### Task 26: BBTSignal (three-step shift method)

**Files:**
- Create: `app/modules/cycle/predictor/bbt.py`
- Create: `tests/test_cycle/test_predictor_bbt.py`

- [ ] **Step 1: Write failing test `tests/test_cycle/test_predictor_bbt.py`**

```python
from datetime import date, timedelta
from decimal import Decimal

from app.modules.auth.models import User, UserRole
from app.modules.cycle.predictor.bbt import BBTSignal
from app.modules.health.models import BbtMethod
from app.modules.health.service import log_bbt


def _user(db):
    u = User(username="a", display_name="A", password_hash="x", role=UserRole.SHE)
    db.add(u); db.flush()
    return u


def _log_temps(db, user_id, start: date, temps: list[float]) -> None:
    for i, t in enumerate(temps):
        log_bbt(db, user_id=user_id, on=start + timedelta(days=i),
                temp_c=Decimal(str(t)), method=BbtMethod.ORAL)


def test_bbt_three_step_shift_detected(db):
    u = _user(db)
    # 6 baseline days then 3-day sustained shift
    _log_temps(db, u.id, date(2026, 5, 1),
               [36.3, 36.35, 36.32, 36.28, 36.34, 36.30,  # baseline
                36.65, 36.60, 36.68])  # 3-day shift
    sig = BBTSignal()
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 5, 10))
    assert r is not None
    # T1 is day index 6 -> 2026-05-07; ovulation = T1 - 1 = 2026-05-06
    assert r.predicted_ovulation == date(2026, 5, 6)
    assert r.confidence >= 0.7


def test_bbt_insufficient_baseline_returns_none(db):
    u = _user(db)
    _log_temps(db, u.id, date(2026, 5, 1), [36.3, 36.4])
    sig = BBTSignal()
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 5, 5))
    assert r is None or r.predicted_ovulation is None


def test_bbt_no_shift_returns_no_ovulation(db):
    u = _user(db)
    _log_temps(db, u.id, date(2026, 5, 1),
               [36.3, 36.35, 36.32, 36.28, 36.34, 36.30, 36.32, 36.30, 36.33])
    sig = BBTSignal()
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 5, 10))
    assert r is None or r.predicted_ovulation is None
```

- [ ] **Step 2: Implement `app/modules/cycle/predictor/bbt.py`**

```python
import statistics
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.cycle.predictor.base import SignalResult
from app.modules.health.models import BbtReading

BASELINE_DAYS = 6
SHIFT_THRESHOLD = Decimal("0.20")  # degrees C
SUSTAIN_DAYS = 3


class BBTSignal:
    name = "bbt"

    def evaluate(
        self, db: Session, *, user_id: int, target_date: date,
    ) -> SignalResult | None:
        readings = (db.query(BbtReading)
                      .filter(BbtReading.user_id == user_id,
                              BbtReading.date <= target_date)
                      .order_by(BbtReading.date.asc())
                      .all())
        if len(readings) < BASELINE_DAYS + SUSTAIN_DAYS:
            return None

        # Slide a window: index i is T1 candidate; require BASELINE_DAYS prior
        # and (SUSTAIN_DAYS - 1) more readings after it
        for i in range(BASELINE_DAYS, len(readings) - SUSTAIN_DAYS + 1):
            baseline = readings[i - BASELINE_DAYS:i]
            cover = statistics.mean(float(b.temp_c) for b in baseline)
            t1 = readings[i]
            t_window = readings[i:i + SUSTAIN_DAYS]
            if t1.temp_c < Decimal(str(cover)) + SHIFT_THRESHOLD:
                continue
            if not all(t.temp_c > Decimal(str(cover)) for t in t_window):
                continue
            # All three above cover, with at least one ≥ +0.2
            if not any(t.temp_c >= Decimal(str(cover)) + SHIFT_THRESHOLD
                       for t in t_window):
                continue
            ovulation = t1.date.fromordinal(t1.date.toordinal() - 1)
            return SignalResult(
                source=self.name,
                predicted_ovulation=ovulation,
                confidence=0.85,
                evidence=f"BBT 三步法：T1={t1.date}, 基线 {cover:.2f}°C, "
                         f"T1={float(t1.temp_c):.2f}°C",
                extra={"cover": cover, "t1_date": t1.date.isoformat()},
            )
        return None
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_cycle/test_predictor_bbt.py -v
```
Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add app/modules/cycle/predictor/bbt.py tests/test_cycle/test_predictor_bbt.py
git commit -m "feat(cycle): BBTSignal predictor using FAM three-step shift method"
```

---

### Task 27: LHSignal (ovulation test pos within 36h)

**Files:**
- Create: `app/modules/cycle/predictor/lh.py`
- Create: `tests/test_cycle/test_predictor_lh.py`

(LH test results are stored as `daily_tags` — we read them from there. To keep this task self-contained we add a minimal LH-only query helper now and integrate with the full tag system in Phase E.)

- [ ] **Step 1: Write failing test `tests/test_cycle/test_predictor_lh.py`**

```python
from datetime import date, datetime, timedelta, timezone

from app.modules.auth.models import User, UserRole
from app.modules.cycle.predictor.lh import LHSignal, record_lh_test


def _user(db):
    u = User(username="a", display_name="A", password_hash="x", role=UserRole.SHE)
    db.add(u); db.flush()
    return u


def test_lh_positive_within_36h_predicts_ovulation(db):
    u = _user(db)
    today = date(2026, 5, 22)
    record_lh_test(db, user_id=u.id, on=today, result="positive")
    sig = LHSignal()
    r = sig.evaluate(db, user_id=u.id, target_date=today)
    assert r is not None
    assert r.predicted_ovulation is not None
    # Ovulation expected within 24-36h → 1-2 days after positive
    assert r.predicted_ovulation - today in (timedelta(days=1), timedelta(days=2))
    assert r.confidence >= 0.9


def test_lh_negative_returns_low_confidence(db):
    u = _user(db)
    record_lh_test(db, user_id=u.id, on=date(2026, 5, 22), result="negative")
    sig = LHSignal()
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 5, 22))
    assert r is None or r.confidence < 0.3


def test_lh_old_positive_ignored(db):
    u = _user(db)
    record_lh_test(db, user_id=u.id, on=date(2026, 5, 10), result="positive")
    sig = LHSignal()
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 5, 22))
    # 12 days old → no longer relevant
    assert r is None or r.confidence < 0.3
```

- [ ] **Step 2: Implement `app/modules/cycle/predictor/lh.py`**

```python
"""LH ovulation test signal.

LH results are stored in `daily_tags` (category='ovulation_test', tag_key='positive'/'negative'/'faint').
For M1 we use a minimal stand-in helper that writes directly to the table.
Phase E replaces these helpers with the full daily_log service.
"""
from datetime import date, timedelta

from sqlalchemy import Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Session

from app.db import Base
from app.modules.cycle.predictor.base import SignalResult

POSITIVE_HORIZON_HOURS = 36  # ~1.5 days


# Minimal interim table — replaced by full daily_tags in Phase E
class _LHTestStub(Base):
    """TEMPORARY M1 model — superseded by daily_tags in Task 31.
    Migration is destructive at T31: this table dropped, data migrated to daily_tags."""
    __tablename__ = "lh_tests_stub"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    result = Column(String(16), nullable=False)  # positive|negative|faint


def record_lh_test(db: Session, *, user_id: int, on: date, result: str) -> None:
    assert result in {"positive", "negative", "faint"}
    db.add(_LHTestStub(user_id=user_id, date=on, result=result))
    db.flush()


def latest_positive(db: Session, *, user_id: int, on_or_before: date) -> date | None:
    row = (db.query(_LHTestStub)
             .filter(_LHTestStub.user_id == user_id,
                     _LHTestStub.result == "positive",
                     _LHTestStub.date <= on_or_before)
             .order_by(_LHTestStub.date.desc())
             .first())
    return row.date if row else None


class LHSignal:
    name = "lh"

    def evaluate(
        self, db: Session, *, user_id: int, target_date: date,
    ) -> SignalResult | None:
        pos_date = latest_positive(db, user_id=user_id, on_or_before=target_date)
        if pos_date is None:
            return None
        age_days = (target_date - pos_date).days
        if age_days > 2:  # > ~48h, beyond the horizon
            return None
        # Predict ovulation 1-2 days after positive
        ovulation = pos_date + timedelta(days=1 if age_days == 0 else 2)
        return SignalResult(
            source=self.name,
            predicted_ovulation=ovulation,
            confidence=0.95,
            evidence=f"LH 阳性 {age_days} 天前 ({pos_date})",
            extra={"positive_date": pos_date.isoformat()},
        )
```

⚠️ **Note for T31:** the `lh_tests_stub` table is temporary scaffolding. T31's migration must (a) read all rows out, (b) insert equivalent `daily_tags` rows, (c) drop the stub table. Task 31 includes the destructive migration explicitly.

- [ ] **Step 3: Generate + apply stub migration**

```bash
.venv/Scripts/python.exe -m alembic revision --autogenerate -m "lh tests stub (temporary, dropped in T31)"
.venv/Scripts/python.exe -m alembic upgrade head
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_cycle/test_predictor_lh.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/modules/cycle/predictor/lh.py alembic/versions/ tests/test_cycle/test_predictor_lh.py
git commit -m "feat(cycle): LHSignal predictor (stub table, migrated to daily_tags in T31)"
```

---

### Task 28: CombinedPredictor (priority fusion)

**Files:**
- Create: `app/modules/cycle/predictor/combined.py`
- Create: `tests/test_cycle/test_predictor_combined.py`

- [ ] **Step 1: Write failing test `tests/test_cycle/test_predictor_combined.py`**

```python
from datetime import date, timedelta
from decimal import Decimal

from app.modules.auth.models import User, UserRole
from app.modules.cycle.predictor.combined import CombinedPredictor
from app.modules.cycle.predictor.lh import record_lh_test
from app.modules.cycle.service import log_period_start
from app.modules.health.models import BbtMethod
from app.modules.health.service import log_bbt


def _user(db):
    u = User(username="a", display_name="A", password_hash="x", role=UserRole.SHE)
    db.add(u); db.flush()
    return u


def test_lh_positive_beats_calendar(db):
    u = _user(db)
    log_period_start(db, user_id=u.id, start_date=date(2026, 2, 1))
    log_period_start(db, user_id=u.id, start_date=date(2026, 3, 1))
    log_period_start(db, user_id=u.id, start_date=date(2026, 4, 1))
    today = date(2026, 4, 14)
    record_lh_test(db, user_id=u.id, on=today, result="positive")
    p = CombinedPredictor()
    result = p.predict(db, user_id=u.id, target_date=today)
    assert result.primary.source == "lh"
    assert result.primary.predicted_ovulation == today + timedelta(days=1)


def test_bbt_beats_calendar_when_no_lh(db):
    u = _user(db)
    log_period_start(db, user_id=u.id, start_date=date(2026, 4, 1))
    log_period_start(db, user_id=u.id, start_date=date(2026, 5, 1))
    # baseline + shift
    base = date(2026, 5, 10)
    temps = [36.3, 36.35, 36.30, 36.32, 36.28, 36.34,
             36.65, 36.60, 36.68]
    for i, t in enumerate(temps):
        log_bbt(db, user_id=u.id, on=base + timedelta(days=i),
                temp_c=Decimal(str(t)), method=BbtMethod.ORAL)
    p = CombinedPredictor()
    result = p.predict(db, user_id=u.id, target_date=base + timedelta(days=9))
    assert result.primary.source == "bbt"


def test_fallback_to_calendar_when_no_signals(db):
    u = _user(db)
    log_period_start(db, user_id=u.id, start_date=date(2026, 3, 1))
    log_period_start(db, user_id=u.id, start_date=date(2026, 4, 1))
    p = CombinedPredictor()
    result = p.predict(db, user_id=u.id, target_date=date(2026, 4, 20))
    assert result.primary.source == "calendar"


def test_evidence_list_contains_all_signals(db):
    u = _user(db)
    log_period_start(db, user_id=u.id, start_date=date(2026, 3, 1))
    log_period_start(db, user_id=u.id, start_date=date(2026, 4, 1))
    today = date(2026, 4, 14)
    record_lh_test(db, user_id=u.id, on=today, result="positive")
    p = CombinedPredictor()
    result = p.predict(db, user_id=u.id, target_date=today)
    sources = {e.source for e in result.evidence}
    assert "lh" in sources
    assert "calendar" in sources
```

- [ ] **Step 2: Implement `app/modules/cycle/predictor/combined.py`**

```python
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.modules.cycle.predictor.base import SignalResult
from app.modules.cycle.predictor.bbt import BBTSignal
from app.modules.cycle.predictor.calendar import CalendarSignal
from app.modules.cycle.predictor.lh import LHSignal

# Order = priority: first signal with valid prediction wins as primary
SIGNAL_PRIORITY = [LHSignal(), BBTSignal(), CalendarSignal()]


@dataclass(frozen=True)
class Prediction:
    primary: SignalResult
    evidence: list[SignalResult]


class CombinedPredictor:
    def predict(
        self, db: Session, *, user_id: int, target_date: date,
    ) -> Prediction:
        evidence: list[SignalResult] = []
        primary: SignalResult | None = None
        for sig in SIGNAL_PRIORITY:
            r = sig.evaluate(db, user_id=user_id, target_date=target_date)
            if r is None:
                continue
            evidence.append(r)
            if primary is None and r.predicted_ovulation is not None and r.confidence >= 0.4:
                primary = r
        if primary is None:
            # Fallback: low-confidence calendar even with empty history
            primary = CalendarSignal().evaluate(
                db, user_id=user_id, target_date=target_date,
            ) or SignalResult(
                source="calendar", predicted_ovulation=None,
                confidence=0.0, evidence="无数据",
            )
            if primary not in evidence:
                evidence.append(primary)
        return Prediction(primary=primary, evidence=evidence)
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_cycle/test_predictor_combined.py -v
```
Expected: 4 passed.

- [ ] **Step 4: Commit**

```bash
git add app/modules/cycle/predictor/combined.py tests/test_cycle/test_predictor_combined.py
git commit -m "feat(cycle): CombinedPredictor with LH > BBT > Calendar priority fusion"
```

---

### Task 29: /cycle/log and /bbt/log endpoints (HTML forms + HTMX)

**Files:**
- Create: `app/modules/cycle/router.py`
- Create: `app/modules/health/router.py`
- Modify: `app/main.py` (mount routers)
- Create: `app/templates/pages/cycle_log.html`
- Create: `app/templates/pages/bbt_log.html`
- Create: `tests/test_cycle/test_log_endpoint.py`
- Create: `tests/test_health/test_bbt_endpoint.py`

- [ ] **Step 1: Write failing test `tests/test_cycle/test_log_endpoint.py`**

```python
from datetime import date

from app.modules.auth.invite import init_couple_invites
from app.modules.cycle.models import Period


def _login_alice(client, db):
    he, she = init_couple_invites(db, he_display="B", she_display="A", ttl_days=7)
    db.commit()
    client.post(f"/bind?token={he.token}", data={"username": "bob", "password": "pw-12345678"})
    client.post(f"/bind?token={she.token}", data={"username": "alice", "password": "pw-12345678"})
    client.post("/login", data={"username": "alice", "password": "pw-12345678"})


def test_post_cycle_log_creates_period(client, db):
    _login_alice(client, db)
    r = client.post("/cycle/log", data={"action": "start", "date": "2026-05-22"})
    assert r.status_code in (200, 303)
    p = db.query(Period).first()
    assert p is not None and p.start_date == date(2026, 5, 22)


def test_post_cycle_log_end_sets_end_date(client, db):
    _login_alice(client, db)
    client.post("/cycle/log", data={"action": "start", "date": "2026-05-01"})
    p = db.query(Period).first()
    r = client.post("/cycle/log",
                    data={"action": "end", "period_id": str(p.id), "date": "2026-05-05"})
    assert r.status_code in (200, 303)
    refreshed = db.query(Period).get(p.id)
    assert refreshed.end_date == date(2026, 5, 5)


def test_post_cycle_log_unauthenticated_redirects(client):
    r = client.post("/cycle/log", data={"action": "start", "date": "2026-05-22"},
                    follow_redirects=False)
    assert r.status_code in (302, 303)
```

- [ ] **Step 2: Implement `app/modules/cycle/router.py`**

```python
from datetime import date

from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user
from app.modules.auth.models import User
from app.modules.cycle.service import log_period_end, log_period_start, list_periods
from app.templates_env import templates

router = APIRouter(tags=["cycle"])


@router.get("/cycle/log")
def cycle_log_page(
    request,  # type: ignore[no-untyped-def]
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    periods = list_periods(db, user_id=user.id, limit=12)
    return templates.TemplateResponse(
        request, "pages/cycle_log.html",
        {"user": user, "periods": periods, "today": date.today().isoformat()},
    )


@router.post("/cycle/log")
def cycle_log(
    action: str = Form(...),
    date_str: str = Form(..., alias="date"),
    period_id: int | None = Form(default=None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    d = date.fromisoformat(date_str)
    if action == "start":
        log_period_start(db, user_id=user.id, start_date=d)
    elif action == "end":
        if period_id is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail="period_id required for end")
        log_period_end(db, period_id=period_id, end_date=d)
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=f"unknown action {action}")
    db.commit()
    return RedirectResponse(url="/cycle/log", status_code=303)
```

- [ ] **Step 3: Create `app/templates/pages/cycle_log.html`**

```html
{% extends "base.html" %}
{% block title %}经期记录 · Couple Diary{% endblock %}
{% block content %}
<h2 style="margin-top:0">经期记录</h2>

<form method="post" action="/cycle/log" class="card">
  <p class="card-title">记录今天开始经期</p>
  <input type="hidden" name="action" value="start">
  <input class="input" name="date" type="date" value="{{ today }}" required>
  <div style="height:12px"></div>
  <button class="btn" type="submit" style="width:100%">开始</button>
</form>

<div class="card">
  <p class="card-title">最近 12 次</p>
  {% if periods %}
    {% for p in periods %}
      <div style="display:flex;justify-content:space-between;align-items:center;
                  padding:10px 0;border-bottom:1px solid #f5d4dc">
        <span>
          <strong>{{ p.start_date }}</strong>
          {% if p.end_date %} → {{ p.end_date }}
            <span class="subtitle">({{ (p.end_date - p.start_date).days + 1 }} 天)</span>
          {% else %}
            <span class="subtitle">进行中</span>
          {% endif %}
        </span>
        {% if not p.end_date %}
          <form method="post" action="/cycle/log" style="display:inline">
            <input type="hidden" name="action" value="end">
            <input type="hidden" name="period_id" value="{{ p.id }}">
            <input type="hidden" name="date" value="{{ today }}">
            <button class="pill" type="submit">今天结束</button>
          </form>
        {% endif %}
      </div>
    {% endfor %}
  {% else %}
    <p class="subtitle">尚无记录</p>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 4: Implement `app/modules/health/router.py`** (similar form for BBT)

```python
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user
from app.modules.auth.models import User
from app.modules.health.models import BbtMethod
from app.modules.health.service import list_bbt_recent, log_bbt
from app.templates_env import templates

router = APIRouter(tags=["health"])


@router.get("/bbt/log")
def bbt_log_page(
    request,  # type: ignore[no-untyped-def]
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    rows = list_bbt_recent(db, user_id=user.id, days=14)
    return templates.TemplateResponse(
        request, "pages/bbt_log.html",
        {"user": user, "rows": rows, "today": date.today().isoformat()},
    )


@router.post("/bbt/log")
def bbt_log(
    on: str = Form(..., alias="date"),
    temp_c_str: str = Form(..., alias="temp_c"),
    method: str = Form(default="oral"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    try:
        temp = Decimal(temp_c_str)
    except InvalidOperation as e:
        raise HTTPException(status_code=422, detail="invalid temperature") from e
    log_bbt(
        db, user_id=user.id, on=date.fromisoformat(on),
        temp_c=temp, method=BbtMethod(method),
    )
    db.commit()
    return RedirectResponse(url="/bbt/log", status_code=303)
```

- [ ] **Step 5: Create `app/templates/pages/bbt_log.html`**

```html
{% extends "base.html" %}
{% block title %}基础体温 · Couple Diary{% endblock %}
{% block content %}
<h2 style="margin-top:0">基础体温</h2>

<form method="post" action="/bbt/log" class="card">
  <p class="card-title">记录今天</p>
  <input class="input" name="date" type="date" value="{{ today }}" required>
  <div style="height:8px"></div>
  <input class="input" name="temp_c" type="number" step="0.01" min="35" max="39"
         placeholder="例如 36.55" required>
  <div style="height:8px"></div>
  <select class="input" name="method">
    <option value="oral">口腔</option>
    <option value="vaginal">阴道</option>
    <option value="axillary">腋下</option>
    <option value="wrist">腕表</option>
    <option value="other">其他</option>
  </select>
  <div style="height:12px"></div>
  <button class="btn" type="submit" style="width:100%">保存</button>
</form>

<div class="card">
  <p class="card-title">最近 14 天</p>
  {% if rows %}
    {% for r in rows %}
      <div style="display:flex;justify-content:space-between;padding:8px 0;
                  border-bottom:1px solid #f5d4dc">
        <span>{{ r.date }}</span>
        <strong>{{ r.temp_c }} °C</strong>
      </div>
    {% endfor %}
  {% else %}
    <p class="subtitle">尚无记录</p>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 6: Mount routers in `app/main.py`**

Add to imports:
```python
from app.modules.cycle.router import router as cycle_router
from app.modules.health.router import router as health_router
```

After existing `app.include_router(auth_router)`:
```python
app.include_router(cycle_router)
app.include_router(health_router)
```

- [ ] **Step 7: Write `tests/test_health/test_bbt_endpoint.py`**

```python
from app.modules.auth.invite import init_couple_invites
from app.modules.health.models import BbtReading


def _login_alice(client, db):
    he, she = init_couple_invites(db, he_display="B", she_display="A", ttl_days=7)
    db.commit()
    client.post(f"/bind?token={he.token}", data={"username": "bob", "password": "pw-12345678"})
    client.post(f"/bind?token={she.token}", data={"username": "alice", "password": "pw-12345678"})
    client.post("/login", data={"username": "alice", "password": "pw-12345678"})


def test_post_bbt_log_creates_row(client, db):
    _login_alice(client, db)
    r = client.post("/bbt/log", data={"date": "2026-05-22", "temp_c": "36.55"})
    assert r.status_code in (200, 303)
    assert db.query(BbtReading).count() == 1


def test_post_bbt_log_rejects_bad_temp(client, db):
    _login_alice(client, db)
    r = client.post("/bbt/log", data={"date": "2026-05-22", "temp_c": "99"},
                    follow_redirects=False)
    assert r.status_code in (422, 500)
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_cycle/test_log_endpoint.py tests/test_health/test_bbt_endpoint.py -v
```
Expected: 5 passed.

- [ ] **Step 9: Commit**

```bash
git add app/modules/cycle/router.py app/modules/health/router.py app/templates/pages/cycle_log.html app/templates/pages/bbt_log.html app/main.py tests/test_cycle/test_log_endpoint.py tests/test_health/test_bbt_endpoint.py
git commit -m "feat(cycle,health): /cycle/log and /bbt/log endpoints with form pages"
```

---

**End of Phase D.** Cycle domain has Period, BBT, three predictor signals (Calendar/BBT/LH), the combined predictor with priority fusion, and authenticated form-based logging endpoints with HTML pages.

---

## Phase E — Daily Log (Flo-style tags)

### Task 30: Tag catalog (Flo full set as Python constants)

**Files:**
- Create: `app/modules/daily_log/__init__.py`
- Create: `app/modules/daily_log/catalog.py`
- Create: `tests/test_daily_log/__init__.py`
- Create: `tests/test_daily_log/test_catalog.py`

- [ ] **Step 1: Create `tests/test_daily_log/__init__.py`** (empty)

- [ ] **Step 2: Write failing test `tests/test_daily_log/test_catalog.py`**

```python
from app.modules.daily_log.catalog import CATEGORIES, all_tags, find_tag, is_valid_tag


def test_categories_have_required_fields():
    for c in CATEGORIES:
        assert c.key
        assert c.label_zh
        assert isinstance(c.tags, list)
        assert len(c.tags) > 0


def test_unique_tag_keys_across_categories():
    keys = [t.key for c in CATEGORIES for t in c.tags]
    assert len(keys) == len(set(keys)), "tag keys must be globally unique"


def test_critical_tags_present():
    # These are referenced by the predictor; if renamed, predictor breaks
    must = {
        "sex_protected", "sex_unprotected", "oral", "anal", "masturbation",
        "ovulation_positive", "ovulation_negative", "ovulation_faint",
        "discharge_egg_white",
        "mood_happy", "mood_sad", "mood_anxious", "mood_calm",
        "symptom_cramps", "symptom_headache", "symptom_fatigue",
    }
    keys = {t.key for c in CATEGORIES for t in c.tags}
    missing = must - keys
    assert not missing, f"missing critical tag keys: {missing}"


def test_find_tag_returns_tag_or_none():
    assert find_tag("mood_happy") is not None
    assert find_tag("nope_does_not_exist") is None


def test_is_valid_tag():
    assert is_valid_tag("mood_happy")
    assert not is_valid_tag("nope")
```

- [ ] **Step 3: Implement `app/modules/daily_log/__init__.py`**

```python
from app.modules.daily_log import models  # noqa: F401
```

(Models added in T31; create the import target now as empty.)

Create empty `app/modules/daily_log/models.py`:
```python
# Filled in Task 31
```

- [ ] **Step 4: Implement `app/modules/daily_log/catalog.py`**

```python
"""Flo-style tag catalog.

Editing this file:
  - Add a new tag: append to the relevant Category.tags. No migration needed
    (tags are stored as keys in daily_tags).
  - Remove a tag: add an Alembic migration that DELETEs daily_tags rows with
    that key BEFORE removing here, otherwise users will see orphan tag keys
    they can no longer turn off.
  - Rename: deprecate old key + add new + write data migration mapping old→new.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Tag:
    key: str
    label_zh: str
    emoji: str


@dataclass(frozen=True)
class Category:
    key: str
    label_zh: str
    tags: list[Tag]


CATEGORIES: list[Category] = [
    Category("sex", "性行为和性欲", [
        Tag("sex_none", "没有性行为", "🚫"),
        Tag("sex_protected", "有保护的性行为", "🛡️"),
        Tag("sex_unprotected", "无保护的性行为", "💑"),
        Tag("oral", "口交", "👄"),
        Tag("anal", "肛交", "🍑"),
        Tag("masturbation", "自慰", "🌸"),
        Tag("foreplay", "爱抚", "💗"),
        Tag("sex_toys", "情趣用品", "🎀"),
        Tag("orgasm", "性高潮", "✨"),
        Tag("libido_high", "性欲旺盛", "🔥"),
        Tag("libido_normal", "性欲一般", "🌷"),
        Tag("libido_low", "性欲低下", "💤"),
    ]),
    Category("mood", "心情", [
        Tag("mood_calm", "平静", "😌"),
        Tag("mood_happy", "快乐", "😊"),
        Tag("mood_energetic", "有活力", "🤩"),
        Tag("mood_playful", "欢悦", "😋"),
        Tag("mood_swings", "情绪波动", "😢"),
        Tag("mood_angry", "恼怒", "😠"),
        Tag("mood_sad", "伤心", "😞"),
        Tag("mood_anxious", "焦虑", "😟"),
        Tag("mood_depressed", "抑郁", "😔"),
        Tag("mood_guilty", "内疚", "😣"),
    ]),
    Category("symptoms", "症状", [
        Tag("symptom_normal", "一切正常", "👍"),
        Tag("symptom_cramps", "绞痛", "💢"),
        Tag("symptom_breast_tender", "乳房压痛", "🥲"),
        Tag("symptom_headache", "头痛", "🤕"),
        Tag("symptom_acne", "粉刺", "🌋"),
        Tag("symptom_backache", "背痛", "💢"),
        Tag("symptom_fatigue", "疲倦", "🪫"),
        Tag("symptom_cravings", "渴望", "🍔"),
        Tag("symptom_insomnia", "失眠", "🌙"),
        Tag("symptom_abdominal_pain", "腹痛", "💢"),
        Tag("symptom_vaginal_itching", "阴道瘙痒", "🥲"),
        Tag("symptom_vaginal_dryness", "阴道干涩", "🥲"),
    ]),
    Category("discharge", "阴道分泌物", [
        Tag("discharge_none", "无分泌物", "⚪"),
        Tag("discharge_creamy", "乳液状", "🥛"),
        Tag("discharge_watery", "水状", "💧"),
        Tag("discharge_sticky", "粘稠", "🟣"),
        Tag("discharge_egg_white", "蛋清状", "🥚"),
        Tag("discharge_spotting", "点滴出血", "🩸"),
        Tag("discharge_abnormal", "异常", "⚠️"),
        Tag("discharge_white_chunky", "白色块状", "🟠"),
        Tag("discharge_grey", "灰色", "⚫"),
    ]),
    Category("ovulation_test", "排卵测试", [
        Tag("ovulation_none", "没有进行测试", "🚫"),
        Tag("ovulation_positive", "阳性", "✅"),
        Tag("ovulation_negative", "阴性", "❎"),
        Tag("ovulation_faint", "晕线", "🟡"),
    ]),
    Category("digestion", "消化和排便", [
        Tag("digestion_nausea", "恶心", "🤢"),
        Tag("digestion_bloating", "腹胀", "🎈"),
        Tag("digestion_constipation", "便秘", "🚧"),
        Tag("digestion_diarrhea", "腹泻", "💩"),
    ]),
    Category("other", "其他", [
        Tag("travel", "旅行", "✈️"),
        Tag("stress", "压力", "⚡"),
        Tag("meditation", "冥想", "🧘"),
        Tag("journal", "写日记", "📓"),
        Tag("kegel", "凯格尔训练", "🌸"),
        Tag("breathing", "呼吸练习", "💨"),
        Tag("illness", "疾病或损伤", "🤕"),
        Tag("alcohol", "酒精", "🍷"),
    ]),
]


_TAG_INDEX: dict[str, Tag] = {
    t.key: t for c in CATEGORIES for t in c.tags
}


def all_tags() -> list[Tag]:
    return list(_TAG_INDEX.values())


def find_tag(key: str) -> Tag | None:
    return _TAG_INDEX.get(key)


def is_valid_tag(key: str) -> bool:
    return key in _TAG_INDEX


def find_category_of(tag_key: str) -> str | None:
    for c in CATEGORIES:
        if any(t.key == tag_key for t in c.tags):
            return c.key
    return None
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_daily_log/test_catalog.py -v
```
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add app/modules/daily_log/ tests/test_daily_log/
git commit -m "feat(daily_log): Flo-style tag catalog with ~70 tags across 7 categories"
```

---

### Task 31: DailyEntry + DailyTag models + migrate LH stub data

**Files:**
- Modify: `app/modules/daily_log/models.py`
- Modify: `app/modules/cycle/predictor/lh.py` (now reads from daily_tags)
- Modify: `app/modules/__init__.py`
- Create: `tests/test_daily_log/test_models.py`
- Migration with data move

- [ ] **Step 1: Write failing test `tests/test_daily_log/test_models.py`**

```python
from datetime import date

from app.modules.auth.models import User, UserRole
from app.modules.daily_log.models import DailyEntry, DailyTag


def _user(db):
    u = User(username="a", display_name="A", password_hash="x", role=UserRole.SHE)
    db.add(u); db.flush()
    return u


def test_daily_entry_persistable(db):
    u = _user(db)
    e = DailyEntry(user_id=u.id, date=date(2026, 5, 22), notes="hi")
    db.add(e); db.flush()
    assert e.id is not None


def test_daily_entry_unique_per_user_day(db):
    u = _user(db)
    db.add(DailyEntry(user_id=u.id, date=date(2026, 5, 22)))
    db.flush()
    db.add(DailyEntry(user_id=u.id, date=date(2026, 5, 22)))
    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        db.flush()


def test_daily_tag_unique_per_entry_key(db):
    u = _user(db)
    e = DailyEntry(user_id=u.id, date=date(2026, 5, 22))
    db.add(e); db.flush()
    db.add(DailyTag(entry_id=e.id, category="mood", tag_key="mood_happy"))
    db.flush()
    db.add(DailyTag(entry_id=e.id, category="mood", tag_key="mood_happy"))
    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        db.flush()
```

- [ ] **Step 2: Replace `app/modules/daily_log/models.py`**

```python
from datetime import date, datetime

from sqlalchemy import (
    Date, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class DailyEntry(Base):
    __tablename__ = "daily_entries"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_daily_entries_user_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    tags: Mapped[list["DailyTag"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan",
    )


class DailyTag(Base):
    __tablename__ = "daily_tags"
    __table_args__ = (
        UniqueConstraint("entry_id", "tag_key", name="uq_daily_tags_entry_key"),
        Index("ix_daily_tags_category", "category"),
        Index("ix_daily_tags_tag_key", "tag_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("daily_entries.id", ondelete="CASCADE"), nullable=False,
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    tag_key: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    entry: Mapped[DailyEntry] = relationship(back_populates="tags")
```

- [ ] **Step 3: Generate migration**

```bash
.venv/Scripts/python.exe -m alembic revision --autogenerate -m "daily entries and tags; drop lh stub after migration"
```

- [ ] **Step 4: Edit the generated migration to migrate LH stub data and drop the stub table**

Open `alembic/versions/<rev>_daily_entries_and_tags...py` and replace `upgrade()` with the manual flow:

```python
def upgrade() -> None:
    op.create_table(
        "daily_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "date", name="uq_daily_entries_user_date"),
    )
    op.create_table(
        "daily_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entry_id", sa.Integer(),
                  sa.ForeignKey("daily_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("tag_key", sa.String(64), nullable=False),
        sa.Column("value", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("entry_id", "tag_key", name="uq_daily_tags_entry_key"),
    )
    op.create_index("ix_daily_tags_category", "daily_tags", ["category"])
    op.create_index("ix_daily_tags_tag_key", "daily_tags", ["tag_key"])

    # Data migration: move lh_tests_stub rows → daily_entries + daily_tags
    conn = op.get_bind()
    stub = conn.execute(sa.text("SELECT user_id, date, result FROM lh_tests_stub")).fetchall()
    for row in stub:
        # Ensure DailyEntry exists for (user, date)
        existing = conn.execute(
            sa.text("SELECT id FROM daily_entries WHERE user_id=:u AND date=:d"),
            {"u": row.user_id, "d": row.date},
        ).fetchone()
        if existing is None:
            r = conn.execute(
                sa.text("INSERT INTO daily_entries (user_id, date) VALUES (:u, :d)"),
                {"u": row.user_id, "d": row.date},
            )
            entry_id = r.lastrowid
        else:
            entry_id = existing.id
        tag_key = {
            "positive": "ovulation_positive",
            "negative": "ovulation_negative",
            "faint": "ovulation_faint",
        }[row.result]
        # Insert ignore in case of duplicate
        try:
            conn.execute(
                sa.text(
                    "INSERT INTO daily_tags (entry_id, category, tag_key) "
                    "VALUES (:e, 'ovulation_test', :k)"
                ),
                {"e": entry_id, "k": tag_key},
            )
        except Exception:
            pass

    op.drop_table("lh_tests_stub")


def downgrade() -> None:
    op.create_table(
        "lh_tests_stub",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("result", sa.String(16), nullable=False),
    )
    op.drop_index("ix_daily_tags_tag_key", table_name="daily_tags")
    op.drop_index("ix_daily_tags_category", table_name="daily_tags")
    op.drop_table("daily_tags")
    op.drop_table("daily_entries")
```

- [ ] **Step 5: Update `app/modules/cycle/predictor/lh.py`** — replace stub helpers with daily_tags queries

```python
"""LH ovulation test signal — reads from daily_tags."""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cycle.predictor.base import SignalResult
from app.modules.daily_log.models import DailyEntry, DailyTag


def latest_positive(db: Session, *, user_id: int, on_or_before: date) -> date | None:
    stmt = (
        select(DailyEntry.date)
        .join(DailyTag, DailyTag.entry_id == DailyEntry.id)
        .where(
            DailyEntry.user_id == user_id,
            DailyEntry.date <= on_or_before,
            DailyTag.tag_key == "ovulation_positive",
        )
        .order_by(DailyEntry.date.desc())
        .limit(1)
    )
    row = db.execute(stmt).scalar_one_or_none()
    return row


def record_lh_test(db: Session, *, user_id: int, on: date, result: str) -> None:
    """Helper used by tests/import jobs — writes via DailyTag, not the old stub."""
    assert result in {"positive", "negative", "faint"}
    tag_key = f"ovulation_{result}"
    entry = (db.query(DailyEntry)
               .filter_by(user_id=user_id, date=on)
               .one_or_none())
    if entry is None:
        entry = DailyEntry(user_id=user_id, date=on)
        db.add(entry); db.flush()
    if not db.query(DailyTag).filter_by(entry_id=entry.id, tag_key=tag_key).first():
        db.add(DailyTag(entry_id=entry.id, category="ovulation_test", tag_key=tag_key))
        db.flush()


class LHSignal:
    name = "lh"

    def evaluate(
        self, db: Session, *, user_id: int, target_date: date,
    ) -> SignalResult | None:
        pos_date = latest_positive(db, user_id=user_id, on_or_before=target_date)
        if pos_date is None:
            return None
        age_days = (target_date - pos_date).days
        if age_days > 2:
            return None
        ovulation = pos_date + timedelta(days=1 if age_days == 0 else 2)
        return SignalResult(
            source=self.name,
            predicted_ovulation=ovulation,
            confidence=0.95,
            evidence=f"LH 阳性 {age_days} 天前 ({pos_date})",
            extra={"positive_date": pos_date.isoformat()},
        )
```

- [ ] **Step 6: Apply migration**

```bash
.venv/Scripts/python.exe -m alembic upgrade head
```

Expected: `lh_tests_stub` is gone; `daily_entries`, `daily_tags` exist; any prior stub rows migrated.

- [ ] **Step 7: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_daily_log/test_models.py tests/test_cycle/ -v
```
Expected: all pass including previous LH/Combined predictor tests (now using daily_tags).

- [ ] **Step 8: Commit**

```bash
git add app/modules/daily_log/models.py app/modules/cycle/predictor/lh.py alembic/versions/ tests/test_daily_log/test_models.py
git commit -m "feat(daily_log): DailyEntry/DailyTag models; migrate LH stub into daily_tags"
```

---

### Task 32: Tag toggle service (idempotent upsert)

**Files:**
- Create: `app/modules/daily_log/service.py`
- Create: `tests/test_daily_log/test_toggle_service.py`

- [ ] **Step 1: Write failing test `tests/test_daily_log/test_toggle_service.py`**

```python
from datetime import date

from app.errors import ValidationFailed
from app.modules.auth.models import User, UserRole
from app.modules.daily_log.models import DailyEntry, DailyTag
from app.modules.daily_log.service import (
    get_or_create_entry, toggle_tag, list_tags_for_day,
)


def _user(db):
    u = User(username="a", display_name="A", password_hash="x", role=UserRole.SHE)
    db.add(u); db.flush()
    return u


def test_get_or_create_entry_idempotent(db):
    u = _user(db)
    a = get_or_create_entry(db, user_id=u.id, on=date(2026, 5, 22))
    b = get_or_create_entry(db, user_id=u.id, on=date(2026, 5, 22))
    assert a.id == b.id
    assert db.query(DailyEntry).count() == 1


def test_toggle_tag_on_then_off(db):
    u = _user(db)
    e = get_or_create_entry(db, user_id=u.id, on=date(2026, 5, 22))
    state1 = toggle_tag(db, entry_id=e.id, tag_key="mood_happy")
    assert state1 is True
    assert db.query(DailyTag).count() == 1
    state2 = toggle_tag(db, entry_id=e.id, tag_key="mood_happy")
    assert state2 is False
    assert db.query(DailyTag).count() == 0


def test_toggle_invalid_tag_raises(db):
    u = _user(db)
    e = get_or_create_entry(db, user_id=u.id, on=date(2026, 5, 22))
    import pytest
    with pytest.raises(ValidationFailed):
        toggle_tag(db, entry_id=e.id, tag_key="not_a_real_tag")


def test_list_tags_for_day(db):
    u = _user(db)
    e = get_or_create_entry(db, user_id=u.id, on=date(2026, 5, 22))
    toggle_tag(db, entry_id=e.id, tag_key="mood_happy")
    toggle_tag(db, entry_id=e.id, tag_key="symptom_cramps")
    tags = list_tags_for_day(db, user_id=u.id, on=date(2026, 5, 22))
    assert {t.tag_key for t in tags} == {"mood_happy", "symptom_cramps"}
```

- [ ] **Step 2: Implement `app/modules/daily_log/service.py`**

```python
from datetime import date
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.errors import ValidationFailed
from app.modules.daily_log.catalog import find_category_of, is_valid_tag
from app.modules.daily_log.models import DailyEntry, DailyTag


def get_or_create_entry(db: Session, *, user_id: int, on: date) -> DailyEntry:
    e = db.query(DailyEntry).filter_by(user_id=user_id, date=on).one_or_none()
    if e is None:
        e = DailyEntry(user_id=user_id, date=on)
        db.add(e); db.flush()
    return e


def toggle_tag(db: Session, *, entry_id: int, tag_key: str) -> bool:
    """Returns True if tag is now SET, False if it was REMOVED."""
    if not is_valid_tag(tag_key):
        raise ValidationFailed(f"unknown tag: {tag_key}")
    existing = (db.query(DailyTag)
                  .filter_by(entry_id=entry_id, tag_key=tag_key)
                  .one_or_none())
    if existing is not None:
        db.delete(existing); db.flush()
        return False
    category = find_category_of(tag_key) or "other"
    db.add(DailyTag(entry_id=entry_id, category=category, tag_key=tag_key))
    db.flush()
    return True


def list_tags_for_day(
    db: Session, *, user_id: int, on: date,
) -> Sequence[DailyTag]:
    entry = db.query(DailyEntry).filter_by(user_id=user_id, date=on).one_or_none()
    if entry is None:
        return []
    return list(entry.tags)
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_daily_log/test_toggle_service.py -v
```
Expected: 4 passed.

- [ ] **Step 4: Commit**

```bash
git add app/modules/daily_log/service.py tests/test_daily_log/test_toggle_service.py
git commit -m "feat(daily_log): toggle service with catalog validation and per-day entry upsert"
```

---

### Task 33: /log/today + /log/{date} sheet pages (GET)

**Files:**
- Create: `app/modules/daily_log/router.py`
- Create: `app/templates/pages/daily_sheet.html`
- Create: `app/templates/fragments/tag_pill.html`
- Modify: `app/main.py` (mount router)
- Create: `tests/test_daily_log/test_sheet_page.py`

- [ ] **Step 1: Write failing test `tests/test_daily_log/test_sheet_page.py`**

```python
from app.modules.auth.invite import init_couple_invites


def _login(client, db):
    he, she = init_couple_invites(db, he_display="B", she_display="A", ttl_days=7)
    db.commit()
    client.post(f"/bind?token={he.token}", data={"username": "bob", "password": "pw-12345678"})
    client.post(f"/bind?token={she.token}", data={"username": "alice", "password": "pw-12345678"})
    client.post("/login", data={"username": "alice", "password": "pw-12345678"})


def test_get_log_today_renders_categories(client, db):
    _login(client, db)
    r = client.get("/log/today")
    assert r.status_code == 200
    assert "心情" in r.text
    assert "症状" in r.text
    assert "性行为和性欲" in r.text
    assert "mood_happy" in r.text


def test_get_log_specific_date(client, db):
    _login(client, db)
    r = client.get("/log/2026-05-01")
    assert r.status_code == 200
    assert "2026-05-01" in r.text or "5 月 1 日" in r.text


def test_get_log_invalid_date_returns_404(client, db):
    _login(client, db)
    r = client.get("/log/not-a-date", follow_redirects=False,
                   headers={"Accept": "application/json"})
    assert r.status_code in (404, 422)
```

- [ ] **Step 2: Create `app/templates/fragments/tag_pill.html`**

```html
{# Reusable tag pill — pressed state via aria-pressed. HTMX endpoint toggles. #}
<button class="pill" type="button"
        aria-pressed="{{ 'true' if selected else 'false' }}"
        hx-post="/log/{{ on.isoformat() }}/tag/{{ tag.key }}/toggle"
        hx-target="this"
        hx-swap="outerHTML">
  <span>{{ tag.emoji }}</span><span>{{ tag.label_zh }}</span>
</button>
```

- [ ] **Step 3: Create `app/templates/pages/daily_sheet.html`**

```html
{% extends "base.html" %}
{% block title %}记录 {{ on }} · Couple Diary{% endblock %}
{% block content %}
<h2 style="margin-top:0">记录 · {{ on }}</h2>
<p class="subtitle">点标签即时保存，再点取消</p>

{% for category in categories %}
  <div class="card">
    <p class="card-title">{{ category.label_zh }}</p>
    <div style="display:flex;flex-wrap:wrap;gap:8px">
      {% for tag in category.tags %}
        {% include "fragments/tag_pill.html" with context %}
      {% endfor %}
    </div>
  </div>
{% endfor %}
{% endblock %}
```

- [ ] **Step 4: Implement `app/modules/daily_log/router.py`**

```python
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user
from app.modules.auth.models import User
from app.modules.daily_log.catalog import CATEGORIES, find_tag
from app.modules.daily_log.service import (
    get_or_create_entry, list_tags_for_day, toggle_tag,
)
from app.templates_env import templates

router = APIRouter(tags=["daily_log"])


def _render_sheet(request: Request, db: Session, user: User, on: date) -> HTMLResponse:
    selected = {t.tag_key for t in list_tags_for_day(db, user_id=user.id, on=on)}

    # Inject 'selected' into context for each tag — done in template via lookup map
    return templates.TemplateResponse(
        request, "pages/daily_sheet.html",
        {
            "on": on,
            "categories": CATEGORIES,
            "selected_keys": selected,
            # Used by tag_pill.html — template will pull `selected` per tag using
            # Jinja's `is_selected` filter registered below
        },
    )


@router.get("/log/today", response_class=HTMLResponse)
def log_today(
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    return _render_sheet(request, db, user, date.today())


@router.get("/log/{on}", response_class=HTMLResponse)
def log_day(
    request: Request,
    on: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    try:
        parsed = date.fromisoformat(on)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="invalid date") from e
    return _render_sheet(request, db, user, parsed)
```

- [ ] **Step 5: Register `selected_keys` lookup in templates**

The `tag_pill.html` include uses `selected` from the surrounding context. Update `daily_sheet.html` to set per-tag selected:

Replace `{% include "fragments/tag_pill.html" with context %}` with:
```jinja
{% set selected = tag.key in selected_keys %}
{% include "fragments/tag_pill.html" %}
```

And update `tag_pill.html` to require `selected` and `on` to be passed (they come from outer context via `with context`). The pattern above with `{% set %}` works because Jinja includes inherit the rendering scope.

- [ ] **Step 6: Mount router in `app/main.py`**

Add import:
```python
from app.modules.daily_log.router import router as daily_log_router
```
After other `include_router`:
```python
app.include_router(daily_log_router)
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_daily_log/test_sheet_page.py -v
```
Expected: 3 passed.

- [ ] **Step 8: Commit**

```bash
git add app/modules/daily_log/router.py app/templates/pages/daily_sheet.html app/templates/fragments/tag_pill.html app/main.py tests/test_daily_log/test_sheet_page.py
git commit -m "feat(daily_log): GET /log/today and /log/{date} sheet pages"
```

---

### Task 34: Tag toggle HTMX endpoint (POST)

**Files:**
- Modify: `app/modules/daily_log/router.py` (add toggle endpoint returning fragment)
- Create: `tests/test_daily_log/test_toggle_endpoint.py`

- [ ] **Step 1: Write failing test `tests/test_daily_log/test_toggle_endpoint.py`**

```python
from datetime import date

from app.modules.auth.invite import init_couple_invites
from app.modules.daily_log.models import DailyEntry, DailyTag


def _login(client, db):
    he, she = init_couple_invites(db, he_display="B", she_display="A", ttl_days=7)
    db.commit()
    client.post(f"/bind?token={he.token}", data={"username": "bob", "password": "pw-12345678"})
    client.post(f"/bind?token={she.token}", data={"username": "alice", "password": "pw-12345678"})
    client.post("/login", data={"username": "alice", "password": "pw-12345678"})


def test_toggle_creates_tag(client, db):
    _login(client, db)
    r = client.post("/log/2026-05-22/tag/mood_happy/toggle")
    assert r.status_code == 200
    assert 'aria-pressed="true"' in r.text
    assert db.query(DailyTag).filter_by(tag_key="mood_happy").count() == 1


def test_toggle_twice_removes_tag(client, db):
    _login(client, db)
    client.post("/log/2026-05-22/tag/mood_happy/toggle")
    r = client.post("/log/2026-05-22/tag/mood_happy/toggle")
    assert r.status_code == 200
    assert 'aria-pressed="false"' in r.text
    assert db.query(DailyTag).filter_by(tag_key="mood_happy").count() == 0


def test_toggle_invalid_tag_returns_422(client, db):
    _login(client, db)
    r = client.post("/log/2026-05-22/tag/nonsense_xyz/toggle",
                    headers={"Accept": "application/json"})
    assert r.status_code == 422


def test_toggle_creates_entry_on_demand(client, db):
    _login(client, db)
    assert db.query(DailyEntry).count() == 0
    client.post("/log/2026-05-22/tag/mood_happy/toggle")
    assert db.query(DailyEntry).count() == 1
```

- [ ] **Step 2: Add toggle endpoint to `app/modules/daily_log/router.py`**

```python
@router.post("/log/{on}/tag/{tag_key}/toggle", response_class=HTMLResponse)
def toggle_endpoint(
    request: Request,
    on: str,
    tag_key: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    tag = find_tag(tag_key)
    if tag is None:
        from app.errors import ValidationFailed
        raise ValidationFailed(f"unknown tag: {tag_key}")
    try:
        parsed = date.fromisoformat(on)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="invalid date") from e
    entry = get_or_create_entry(db, user_id=user.id, on=parsed)
    selected = toggle_tag(db, entry_id=entry.id, tag_key=tag_key)
    db.commit()
    return templates.TemplateResponse(
        request, "fragments/tag_pill.html",
        {"tag": tag, "selected": selected, "on": parsed},
    )
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_daily_log/test_toggle_endpoint.py -v
```
Expected: 4 passed.

- [ ] **Step 4: Commit**

```bash
git add app/modules/daily_log/router.py tests/test_daily_log/test_toggle_endpoint.py
git commit -m "feat(daily_log): HTMX tag toggle endpoint returning fragment"
```

---

**End of Phase E.** Daily log is fully functional: catalog, entry model, idempotent toggle service, sheet page, HTMX toggle endpoint.

---

## Phase F — Visibility & Settings Foundation

### Task 35: UserSettings model with visibility map

**Files:**
- Create: `app/modules/settings/__init__.py`
- Create: `app/modules/settings/models.py`
- Modify: `app/modules/__init__.py`
- Create: `tests/test_settings/__init__.py`
- Create: `tests/test_settings/test_models.py`
- Migration

- [ ] **Step 1: Create `tests/test_settings/__init__.py`** (empty)

- [ ] **Step 2: Write failing test `tests/test_settings/test_models.py`**

```python
from app.modules.auth.models import User, UserRole
from app.modules.settings.models import (
    DEFAULT_VISIBILITY, UserSettings, ensure_settings,
)


def _user(db):
    u = User(username="a", display_name="A", password_hash="x", role=UserRole.SHE)
    db.add(u); db.flush()
    return u


def test_default_visibility_keys_present():
    must = {"cycle", "bbt", "daily_log", "diary", "trip", "media", "health_metrics"}
    assert must <= set(DEFAULT_VISIBILITY.keys())


def test_ensure_settings_creates_if_missing(db):
    u = _user(db)
    s = ensure_settings(db, user_id=u.id)
    assert s.visibility["cycle"] == "shared"
    assert s.visibility["diary"] == "private"


def test_ensure_settings_idempotent(db):
    u = _user(db)
    s1 = ensure_settings(db, user_id=u.id)
    s2 = ensure_settings(db, user_id=u.id)
    assert s1.user_id == s2.user_id
    assert db.query(UserSettings).count() == 1
```

- [ ] **Step 3: Implement `app/modules/settings/__init__.py`**

```python
from app.modules.settings import models  # noqa: F401
```

- [ ] **Step 4: Implement `app/modules/settings/models.py`**

```python
from datetime import datetime
from typing import Literal

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, Session

from app.db import Base


Visibility = Literal["private", "shared"]


DEFAULT_VISIBILITY: dict[str, Visibility] = {
    "cycle": "shared",
    "bbt": "shared",
    "daily_log": "shared",
    "diary": "private",
    "trip": "shared",
    "media": "shared",  # media inherits from host; this is the catch-all
    "health_metrics": "shared",
}


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), primary_key=True,
    )
    visibility: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=lambda: dict(DEFAULT_VISIBILITY),
    )
    theme: Mapped[str] = mapped_column(String(32), default="pink", nullable=False)
    notifications_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )


def ensure_settings(db: Session, *, user_id: int) -> UserSettings:
    s = db.query(UserSettings).filter_by(user_id=user_id).one_or_none()
    if s is None:
        s = UserSettings(user_id=user_id, visibility=dict(DEFAULT_VISIBILITY))
        db.add(s); db.flush()
    return s
```

- [ ] **Step 5: Update `app/modules/__init__.py`**

```python
from app.modules import auth, cycle, daily_log, health, settings  # noqa: F401
```

- [ ] **Step 6: Generate + apply migration**

```bash
.venv/Scripts/python.exe -m alembic revision --autogenerate -m "user settings"
.venv/Scripts/python.exe -m alembic upgrade head
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_settings/test_models.py -v
```
Expected: 3 passed.

- [ ] **Step 8: Commit**

```bash
git add app/modules/settings/ app/modules/__init__.py alembic/versions/ tests/test_settings/
git commit -m "feat(settings): UserSettings with default visibility map"
```

---

### Task 36: Visibility dependency + service-layer guard

**Files:**
- Create: `app/modules/settings/visibility.py`
- Modify: `app/deps.py` (add `require_partner_visible` factory)
- Create: `tests/test_visibility/__init__.py`
- Create: `tests/test_visibility/test_matrix.py`

- [ ] **Step 1: Create `tests/test_visibility/__init__.py`** (empty)

- [ ] **Step 2: Write failing test `tests/test_visibility/test_matrix.py`**

```python
"""Visibility matrix: data_type × owner × viewer × visibility_setting → allow/deny."""
import pytest

from app.modules.auth.models import User, UserRole
from app.modules.settings.models import ensure_settings
from app.modules.settings.visibility import (
    can_view, set_visibility, get_visibility, NotVisible,
)


def _user(db, username, role) -> User:
    u = User(username=username, display_name=username, password_hash="x", role=role)
    db.add(u); db.flush()
    return u


@pytest.mark.parametrize("data_type,default_shared", [
    ("cycle", True),
    ("bbt", True),
    ("daily_log", True),
    ("diary", False),
    ("trip", True),
    ("health_metrics", True),
])
def test_default_visibility_per_data_type(db, data_type, default_shared):
    alice = _user(db, "alice", UserRole.SHE)
    bob = _user(db, "bob", UserRole.HE)
    ensure_settings(db, user_id=alice.id)
    assert can_view(db, owner_id=alice.id, viewer_id=bob.id, data_type=data_type) \
        is default_shared


def test_owner_can_always_view_own(db):
    alice = _user(db, "alice", UserRole.SHE)
    ensure_settings(db, user_id=alice.id)
    set_visibility(db, owner_id=alice.id, data_type="diary", visibility="private")
    assert can_view(db, owner_id=alice.id, viewer_id=alice.id, data_type="diary")


def test_set_visibility_changes_partner_access(db):
    alice = _user(db, "alice", UserRole.SHE)
    bob = _user(db, "bob", UserRole.HE)
    ensure_settings(db, user_id=alice.id)
    set_visibility(db, owner_id=alice.id, data_type="cycle", visibility="private")
    assert not can_view(db, owner_id=alice.id, viewer_id=bob.id, data_type="cycle")


def test_get_visibility_returns_default_when_missing(db):
    alice = _user(db, "alice", UserRole.SHE)
    # No ensure_settings called
    assert get_visibility(db, owner_id=alice.id, data_type="cycle") == "shared"


def test_unknown_data_type_defaults_private(db):
    alice = _user(db, "alice", UserRole.SHE)
    ensure_settings(db, user_id=alice.id)
    assert get_visibility(db, owner_id=alice.id, data_type="some_unknown") == "private"
```

- [ ] **Step 3: Implement `app/modules/settings/visibility.py`**

```python
from sqlalchemy.orm import Session

from app.errors import Forbidden
from app.modules.settings.models import DEFAULT_VISIBILITY, UserSettings, Visibility


class NotVisible(Forbidden):
    code = "not_visible"


def get_visibility(
    db: Session, *, owner_id: int, data_type: str,
) -> Visibility:
    s = db.query(UserSettings).filter_by(user_id=owner_id).one_or_none()
    if s is None:
        return DEFAULT_VISIBILITY.get(data_type, "private")
    if not isinstance(s.visibility, dict):
        return DEFAULT_VISIBILITY.get(data_type, "private")
    return s.visibility.get(data_type, DEFAULT_VISIBILITY.get(data_type, "private"))


def set_visibility(
    db: Session, *, owner_id: int, data_type: str, visibility: Visibility,
) -> None:
    s = db.query(UserSettings).filter_by(user_id=owner_id).one_or_none()
    if s is None:
        from app.modules.settings.models import ensure_settings
        s = ensure_settings(db, user_id=owner_id)
    if not isinstance(s.visibility, dict):
        s.visibility = dict(DEFAULT_VISIBILITY)
    s.visibility[data_type] = visibility
    # SQLAlchemy needs explicit modification flag for JSON columns
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(s, "visibility")
    db.flush()


def can_view(
    db: Session, *, owner_id: int, viewer_id: int, data_type: str,
) -> bool:
    if owner_id == viewer_id:
        return True
    return get_visibility(db, owner_id=owner_id, data_type=data_type) == "shared"


def assert_can_view(
    db: Session, *, owner_id: int, viewer_id: int, data_type: str,
) -> None:
    if not can_view(db, owner_id=owner_id, viewer_id=viewer_id, data_type=data_type):
        raise NotVisible(f"cannot view {data_type} of user {owner_id}")
```

- [ ] **Step 4: Add `require_partner_visible` factory to `app/deps.py`**

Append to file:

```python
from typing import Callable

from app.modules.settings.visibility import assert_can_view


def require_partner_visible(data_type: str) -> Callable:
    """Dependency factory. Raises Forbidden if viewer can't see owner's data_type.
    Pass owner_id via path/query — this dep just constructs the checker.
    Use inline at handler: assert_can_view(db, owner_id=..., viewer_id=user.id, data_type=...)
    """
    return assert_can_view  # exposed for direct calls; factory kept for symmetry
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_visibility/test_matrix.py -v
```
Expected: 9 passed (6 from parametrized + 3 individual).

- [ ] **Step 6: Commit**

```bash
git add app/modules/settings/visibility.py app/deps.py tests/test_visibility/
git commit -m "feat(settings): visibility checks with default map and per-type override"
```

---

**End of Phase F.** Visibility model + matrix tests in place; later phases will call `assert_can_view` in service layers and routes that serve cross-partner data.

---

## Phase G — Media Domain (Upload Pipeline + Authenticated Serve)

### Task 37: Media model + cycle_attachments link table

**Files:**
- Create: `app/modules/media/__init__.py`
- Create: `app/modules/media/models.py`
- Modify: `app/modules/__init__.py`
- Create: `tests/test_media/__init__.py`
- Create: `tests/test_media/test_models.py`
- Migration

- [ ] **Step 1: Create `tests/test_media/__init__.py`** (empty)

- [ ] **Step 2: Write failing test `tests/test_media/test_models.py`**

```python
from datetime import datetime, timezone

from app.modules.auth.models import User, UserRole
from app.modules.cycle.models import Period
from app.modules.cycle.service import log_period_start
from app.modules.media.models import (
    CycleAttachment, Media, MediaKind,
)


def _user(db):
    u = User(username="a", display_name="A", password_hash="x", role=UserRole.SHE)
    db.add(u); db.flush()
    return u


def test_media_persistable(db):
    u = _user(db)
    m = Media(
        owner_id=u.id, kind=MediaKind.IMAGE,
        original_path="/data/uploads/1/2026/05/aa/aabb.webp",
        thumb_path="/data/uploads/1/2026/05/aa/aabb.thumb.webp",
        size=12345, mime="image/webp",
        sha256="aabb" + "0" * 60,
    )
    db.add(m); db.flush()
    assert m.id is not None
    assert isinstance(m.created_at, datetime)


def test_media_sha256_unique_per_owner(db):
    u = _user(db)
    h = "a" * 64
    db.add(Media(owner_id=u.id, kind=MediaKind.IMAGE,
                 original_path="x", thumb_path="x", size=1, mime="image/webp", sha256=h))
    db.flush()
    db.add(Media(owner_id=u.id, kind=MediaKind.IMAGE,
                 original_path="y", thumb_path="y", size=1, mime="image/webp", sha256=h))
    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        db.flush()


def test_cycle_attachment_links_media_to_period(db):
    u = _user(db)
    from datetime import date
    p = log_period_start(db, user_id=u.id, start_date=date(2026, 5, 1))
    m = Media(owner_id=u.id, kind=MediaKind.IMAGE,
              original_path="x", thumb_path="x", size=1, mime="image/webp",
              sha256="b" * 64)
    db.add(m); db.flush()
    db.add(CycleAttachment(period_id=p.id, media_id=m.id, kind="ovulation_strip"))
    db.flush()
```

- [ ] **Step 3: Implement `app/modules/media/__init__.py`**

```python
from app.modules.media import models  # noqa: F401
```

- [ ] **Step 4: Implement `app/modules/media/models.py`**

```python
import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String,
    UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class MediaKind(str, enum.Enum):
    IMAGE = "image"
    PDF = "pdf"  # M2 enables PDF; model accepts it now


class Media(Base):
    __tablename__ = "media"
    __table_args__ = (
        UniqueConstraint("owner_id", "sha256", name="uq_media_owner_sha"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    kind: Mapped[MediaKind] = mapped_column(SAEnum(MediaKind, name="media_kind"),
                                            nullable=False)
    original_path: Mapped[str] = mapped_column(String(512), nullable=False)
    thumb_path: Mapped[str] = mapped_column(String(512), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime: Mapped[str] = mapped_column(String(64), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exif_taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exif_lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    exif_lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )


class CycleAttachment(Base):
    __tablename__ = "cycle_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    period_id: Mapped[int] = mapped_column(
        ForeignKey("periods.id", ondelete="CASCADE"), nullable=False,
    )
    media_id: Mapped[int] = mapped_column(
        ForeignKey("media.id", ondelete="CASCADE"), nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # ovulation_strip|report|other
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )


class DailyAttachment(Base):
    __tablename__ = "daily_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("daily_entries.id", ondelete="CASCADE"), nullable=False,
    )
    media_id: Mapped[int] = mapped_column(
        ForeignKey("media.id", ondelete="CASCADE"), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
```

- [ ] **Step 5: Update `app/modules/__init__.py`**

```python
from app.modules import auth, cycle, daily_log, health, media, settings  # noqa: F401
```

- [ ] **Step 6: Generate + apply migration**

```bash
.venv/Scripts/python.exe -m alembic revision --autogenerate -m "media, cycle_attachments, daily_attachments"
.venv/Scripts/python.exe -m alembic upgrade head
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_media/test_models.py -v
```
Expected: 3 passed.

- [ ] **Step 8: Commit**

```bash
git add app/modules/media/ app/modules/__init__.py alembic/versions/ tests/test_media/
git commit -m "feat(media): Media table + cycle/daily attachment link tables"
```

---

### Task 38: Upload pipeline (MIME + magic + sha256 + EXIF + thumbnail)

**Files:**
- Create: `app/modules/media/pipeline.py`
- Create: `tests/test_media/test_pipeline.py`
- Create: `tests/test_media/fixtures/` (empty for now; tests use Pillow-generated images)

- [ ] **Step 1: Write failing test `tests/test_media/test_pipeline.py`**

```python
import io
from pathlib import Path

import pytest
from PIL import Image

from app.errors import FileTooLarge, ValidationFailed
from app.modules.auth.models import User, UserRole
from app.modules.media.models import Media
from app.modules.media.pipeline import ingest_image


def _png_bytes(w: int = 100, h: int = 100) -> bytes:
    img = Image.new("RGB", (w, h), color=(255, 100, 150))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _user(db):
    u = User(username="a", display_name="A", password_hash="x", role=UserRole.SHE)
    db.add(u); db.flush()
    return u


def test_ingest_image_creates_media_row_and_files(db, tmp_path):
    u = _user(db)
    data = _png_bytes()
    m = ingest_image(
        db, owner_id=u.id, filename="cat.png", content=data, mime="image/png",
        upload_root=tmp_path, strip_gps=True,
    )
    db.commit()
    assert m.id is not None
    assert Path(m.original_path).exists()
    assert Path(m.thumb_path).exists()
    assert m.mime == "image/webp"  # converted to webp on save
    assert m.size > 0


def test_ingest_image_dedupes_by_sha256(db, tmp_path):
    u = _user(db)
    data = _png_bytes()
    a = ingest_image(db, owner_id=u.id, filename="a.png", content=data,
                     mime="image/png", upload_root=tmp_path, strip_gps=True)
    b = ingest_image(db, owner_id=u.id, filename="b.png", content=data,
                     mime="image/png", upload_root=tmp_path, strip_gps=True)
    assert a.id == b.id
    assert db.query(Media).count() == 1


def test_ingest_image_rejects_too_large(db, tmp_path):
    u = _user(db)
    big = b"\x00" * (51 * 1024 * 1024)
    with pytest.raises(FileTooLarge):
        ingest_image(db, owner_id=u.id, filename="big.png", content=big,
                     mime="image/png", upload_root=tmp_path, strip_gps=True)


def test_ingest_image_rejects_fake_mime(db, tmp_path):
    u = _user(db)
    fake = b"this is not an image"
    with pytest.raises(ValidationFailed):
        ingest_image(db, owner_id=u.id, filename="hack.png", content=fake,
                     mime="image/png", upload_root=tmp_path, strip_gps=True)


def test_ingest_image_rejects_disallowed_mime(db, tmp_path):
    u = _user(db)
    with pytest.raises(ValidationFailed):
        ingest_image(db, owner_id=u.id, filename="evil.exe", content=b"MZ",
                     mime="application/x-msdownload",
                     upload_root=tmp_path, strip_gps=True)
```

- [ ] **Step 2: Implement `app/modules/media/pipeline.py`**

```python
import hashlib
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import IO

from PIL import ExifTags, Image
from sqlalchemy.orm import Session

from app.errors import FileTooLarge, ValidationFailed
from app.modules.media.models import Media, MediaKind

MAX_BYTES = 50 * 1024 * 1024  # 50 MB
ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/heic"}
THUMB_SIZE = (400, 400)
PREVIEW_LONG_EDGE = 1200

# Image magic byte signatures
_MAGIC: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"RIFF", "image/webp"),     # RIFF....WEBP — verify "WEBP" at offset 8
    (b"\x00\x00\x00 ftypheic", "image/heic"),  # very loose; HEIC detection is best-effort
    (b"\x00\x00\x00\x18ftypheic", "image/heic"),
    (b"\x00\x00\x00\x18ftypheix", "image/heic"),
    (b"\x00\x00\x00\x18ftypmif1", "image/heic"),
]


def detect_image_mime(content: bytes) -> str | None:
    if len(content) < 12:
        return None
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    if content[4:12] in (b"ftypheic", b"ftypheix", b"ftypmif1", b"ftypmsf1"):
        return "image/heic"
    return None


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _extract_exif(img: Image.Image) -> tuple[datetime | None, float | None, float | None]:
    try:
        exif = img._getexif() or {}
    except Exception:
        return None, None, None
    if not exif:
        return None, None, None

    tag_name = {v: k for k, v in ExifTags.TAGS.items()}
    gps_tag = tag_name.get("GPSInfo")

    taken_at = None
    raw_dt = exif.get(tag_name.get("DateTimeOriginal", -1)) \
             or exif.get(tag_name.get("DateTime", -1))
    if isinstance(raw_dt, str):
        try:
            taken_at = datetime.strptime(raw_dt, "%Y:%m:%d %H:%M:%S").replace(
                tzinfo=timezone.utc)
        except ValueError:
            pass

    lat = lng = None
    if gps_tag and gps_tag in exif and exif[gps_tag]:
        gps = exif[gps_tag]
        try:
            def _deg(v):
                d, m, s = v
                return float(d) + float(m) / 60 + float(s) / 3600

            lat_v = gps.get(2)
            lat_ref = gps.get(1)
            lng_v = gps.get(4)
            lng_ref = gps.get(3)
            if lat_v and lat_ref and lng_v and lng_ref:
                lat = _deg(lat_v) * (-1 if lat_ref == "S" else 1)
                lng = _deg(lng_v) * (-1 if lng_ref == "W" else 1)
        except Exception:
            pass

    return taken_at, lat, lng


def ingest_image(
    db: Session, *, owner_id: int, filename: str, content: bytes,
    mime: str, upload_root: Path, strip_gps: bool,
) -> Media:
    if len(content) > MAX_BYTES:
        raise FileTooLarge(f"file size {len(content)} > {MAX_BYTES}")
    if mime not in ALLOWED_IMAGE_MIMES:
        raise ValidationFailed(f"disallowed mime: {mime}")
    detected = detect_image_mime(content)
    if detected is None:
        raise ValidationFailed("content does not look like a valid image")
    if detected != mime:
        raise ValidationFailed(f"mime mismatch: header says {mime}, content is {detected}")

    sha = _sha256_hex(content)

    existing = db.query(Media).filter_by(owner_id=owner_id, sha256=sha).one_or_none()
    if existing is not None:
        return existing

    # Decode + normalize
    try:
        img = Image.open(io.BytesIO(content))
        img.load()
    except Exception as e:
        raise ValidationFailed("cannot decode image") from e

    taken_at, lat, lng = _extract_exif(img)
    if strip_gps:
        lat = lng = None

    # Compute storage path
    now = datetime.now(timezone.utc)
    rel = Path(str(owner_id)) / f"{now.year:04d}" / f"{now.month:02d}" / sha[:2]
    target_dir = upload_root / rel
    target_dir.mkdir(parents=True, exist_ok=True)

    # Preview (long edge 1200) as WebP
    img_rgb = img.convert("RGB") if img.mode in ("RGBA", "LA", "P") else img
    preview = img_rgb.copy()
    preview.thumbnail((PREVIEW_LONG_EDGE, PREVIEW_LONG_EDGE), Image.LANCZOS)
    preview_path = target_dir / f"{sha}.webp"
    preview.save(preview_path, "WEBP", quality=82, method=4)

    # Thumbnail 400x400 cover
    thumb = img_rgb.copy()
    thumb.thumbnail(THUMB_SIZE, Image.LANCZOS)
    thumb_path = target_dir / f"{sha}.thumb.webp"
    thumb.save(thumb_path, "WEBP", quality=80, method=4)

    m = Media(
        owner_id=owner_id, kind=MediaKind.IMAGE,
        original_path=str(preview_path),
        thumb_path=str(thumb_path),
        size=preview_path.stat().st_size,
        mime="image/webp",
        sha256=sha,
        width=preview.width, height=preview.height,
        exif_taken_at=taken_at, exif_lat=lat, exif_lng=lng,
    )
    db.add(m); db.flush()
    return m
```

- [ ] **Step 3: Add `tmp_path` upload_root to tests — already handled by pytest's `tmp_path` fixture.**

Run tests:

```bash
.venv/Scripts/python.exe -m pytest tests/test_media/test_pipeline.py -v
```
Expected: 5 passed.

- [ ] **Step 4: Commit**

```bash
git add app/modules/media/pipeline.py tests/test_media/test_pipeline.py
git commit -m "feat(media): upload pipeline with sha256 dedup, EXIF, GPS strip, WebP thumbs"
```

---

### Task 39: Upload endpoint (POST /media/upload)

**Files:**
- Create: `app/modules/media/router.py`
- Create: `app/modules/media/schemas.py`
- Modify: `app/main.py`
- Create: `tests/test_media/test_upload_endpoint.py`

- [ ] **Step 1: Write failing test `tests/test_media/test_upload_endpoint.py`**

```python
import io

from PIL import Image

from app.modules.auth.invite import init_couple_invites
from app.modules.media.models import Media


def _png() -> bytes:
    img = Image.new("RGB", (50, 50), color=(255, 0, 0))
    buf = io.BytesIO(); img.save(buf, format="PNG")
    return buf.getvalue()


def _login(client, db):
    he, she = init_couple_invites(db, he_display="B", she_display="A", ttl_days=7)
    db.commit()
    client.post(f"/bind?token={he.token}", data={"username": "bob", "password": "pw-12345678"})
    client.post(f"/bind?token={she.token}", data={"username": "alice", "password": "pw-12345678"})
    client.post("/login", data={"username": "alice", "password": "pw-12345678"})


def test_upload_creates_media_row(client, db, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    _login(client, db)
    files = {"file": ("photo.png", _png(), "image/png")}
    r = client.post("/media/upload", files=files)
    assert r.status_code == 201
    body = r.json()
    assert "id" in body and body["mime"] == "image/webp"
    assert db.query(Media).count() == 1


def test_upload_unauthenticated_redirects(client, tmp_path):
    files = {"file": ("photo.png", _png(), "image/png")}
    r = client.post("/media/upload", files=files, follow_redirects=False)
    assert r.status_code in (302, 303)


def test_upload_dedup_returns_same_id(client, db, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    _login(client, db)
    files = {"file": ("photo.png", _png(), "image/png")}
    r1 = client.post("/media/upload", files=files)
    r2 = client.post("/media/upload", files=files)
    assert r1.json()["id"] == r2.json()["id"]
```

- [ ] **Step 2: Implement `app/modules/media/schemas.py`**

```python
from pydantic import BaseModel


class MediaOut(BaseModel):
    id: int
    kind: str
    mime: str
    size: int
    width: int | None = None
    height: int | None = None

    class Config:
        from_attributes = True
```

- [ ] **Step 3: Implement `app/modules/media/router.py`**

```python
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import current_user
from app.errors import ValidationFailed
from app.modules.auth.models import User
from app.modules.media.pipeline import ingest_image
from app.modules.media.schemas import MediaOut

router = APIRouter(prefix="/media", tags=["media"])
_cfg = get_settings()


@router.post("/upload", status_code=201, response_model=MediaOut)
async def upload(
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> MediaOut:
    content = await file.read()
    if not file.content_type:
        raise ValidationFailed("missing content-type")
    m = ingest_image(
        db,
        owner_id=user.id,
        filename=file.filename or "upload",
        content=content,
        mime=file.content_type,
        upload_root=Path(str(_cfg.upload_dir)),
        strip_gps=True,
    )
    db.commit()
    return MediaOut.model_validate(m)
```

- [ ] **Step 4: Mount router in `app/main.py`**

Add import:
```python
from app.modules.media.router import router as media_router
```
Add after other routers:
```python
app.include_router(media_router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_media/test_upload_endpoint.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add app/modules/media/router.py app/modules/media/schemas.py app/main.py tests/test_media/test_upload_endpoint.py
git commit -m "feat(media): POST /media/upload with auth and dedup"
```

---

### Task 40: Authenticated serve endpoint (GET /media/{id} + /thumb)

**Files:**
- Modify: `app/modules/media/router.py`
- Create: `app/modules/media/service.py` (visibility check helper)
- Create: `tests/test_media/test_serve_endpoint.py`

- [ ] **Step 1: Write failing test `tests/test_media/test_serve_endpoint.py`**

```python
import io

from PIL import Image

from app.modules.auth.invite import init_couple_invites
from app.modules.settings.models import ensure_settings
from app.modules.settings.visibility import set_visibility


def _png() -> bytes:
    img = Image.new("RGB", (50, 50), color=(0, 255, 0))
    buf = io.BytesIO(); img.save(buf, format="PNG")
    return buf.getvalue()


def _bind_pair(client, db):
    he, she = init_couple_invites(db, he_display="B", she_display="A", ttl_days=7)
    db.commit()
    client.post(f"/bind?token={he.token}", data={"username": "bob", "password": "pw-12345678"})
    client.post(f"/bind?token={she.token}", data={"username": "alice", "password": "pw-12345678"})


def test_serve_returns_image_to_owner(client, db, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    _bind_pair(client, db)
    client.post("/login", data={"username": "alice", "password": "pw-12345678"})
    upload = client.post("/media/upload",
                         files={"file": ("a.png", _png(), "image/png")})
    media_id = upload.json()["id"]
    r = client.get(f"/media/{media_id}")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/webp"
    assert len(r.content) > 0


def test_serve_partner_can_view_shared_media(client, db, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    _bind_pair(client, db)
    # Alice uploads
    client.post("/login", data={"username": "alice", "password": "pw-12345678"})
    upload = client.post("/media/upload",
                         files={"file": ("a.png", _png(), "image/png")})
    mid = upload.json()["id"]
    client.post("/logout")
    # Bob logs in (media default = shared)
    client.post("/login", data={"username": "bob", "password": "pw-12345678"})
    r = client.get(f"/media/{mid}")
    assert r.status_code == 200


def test_serve_partner_denied_when_private(client, db, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    _bind_pair(client, db)
    client.post("/login", data={"username": "alice", "password": "pw-12345678"})
    upload = client.post("/media/upload",
                         files={"file": ("a.png", _png(), "image/png")})
    mid = upload.json()["id"]
    # Alice marks media private
    from app.modules.auth.models import User
    alice = db.query(User).filter_by(username="alice").one()
    ensure_settings(db, user_id=alice.id)
    set_visibility(db, owner_id=alice.id, data_type="media", visibility="private")
    db.commit()
    client.post("/logout")
    client.post("/login", data={"username": "bob", "password": "pw-12345678"})
    r = client.get(f"/media/{mid}")
    assert r.status_code == 403


def test_serve_404_for_missing(client, db, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    _bind_pair(client, db)
    client.post("/login", data={"username": "alice", "password": "pw-12345678"})
    r = client.get("/media/99999")
    assert r.status_code == 404
```

- [ ] **Step 2: Implement `app/modules/media/service.py`**

```python
from sqlalchemy.orm import Session

from app.errors import NotFound
from app.modules.media.models import Media
from app.modules.settings.visibility import assert_can_view


def get_media_for_viewer(
    db: Session, *, media_id: int, viewer_id: int,
) -> Media:
    m = db.query(Media).get(media_id)
    if m is None:
        raise NotFound("media not found")
    assert_can_view(db, owner_id=m.owner_id, viewer_id=viewer_id, data_type="media")
    return m
```

- [ ] **Step 3: Append serve endpoints to `app/modules/media/router.py`**

```python
from pathlib import Path
from fastapi.responses import FileResponse
from app.modules.media.service import get_media_for_viewer


@router.get("/{media_id}")
def serve_original(
    media_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    m = get_media_for_viewer(db, media_id=media_id, viewer_id=user.id)
    path = Path(m.original_path)
    if not path.exists():
        from app.errors import NotFound
        raise NotFound("file missing on disk")
    return FileResponse(
        path, media_type=m.mime,
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.get("/{media_id}/thumb")
def serve_thumb(
    media_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    m = get_media_for_viewer(db, media_id=media_id, viewer_id=user.id)
    path = Path(m.thumb_path)
    if not path.exists():
        from app.errors import NotFound
        raise NotFound("thumb missing on disk")
    return FileResponse(
        path, media_type="image/webp",
        headers={"Cache-Control": "private, max-age=86400"},
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_media/test_serve_endpoint.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/modules/media/router.py app/modules/media/service.py tests/test_media/test_serve_endpoint.py
git commit -m "feat(media): GET /media/{id} and /thumb with visibility-checked serve"
```

---

### Task 41: HMAC-signed cache URLs (optional cache opt-in)

**Files:**
- Create: `app/modules/media/signing.py`
- Create: `tests/test_media/test_signing.py`

(URL signing lets us emit `Cache-Control: public` for browser/CDN caching while still requiring a valid signature in the URL — useful later. M1 ships it as a utility; consuming routes adopted in M2.)

- [ ] **Step 1: Write failing test `tests/test_media/test_signing.py`**

```python
import time

import pytest

from app.modules.media.signing import sign_media_url, verify_media_url, SignatureInvalid


def test_sign_then_verify_succeeds():
    qs = sign_media_url(media_id=42, viewer_id=7, ttl_seconds=60)
    assert "sig=" in qs and "exp=" in qs
    verify_media_url(media_id=42, viewer_id=7, query=qs)


def test_verify_fails_on_tamper():
    qs = sign_media_url(media_id=42, viewer_id=7, ttl_seconds=60)
    tampered = qs.replace("media_id=42", "")  # remove field
    with pytest.raises(SignatureInvalid):
        verify_media_url(media_id=99, viewer_id=7, query=qs)


def test_verify_fails_on_expiry():
    qs = sign_media_url(media_id=42, viewer_id=7, ttl_seconds=1)
    time.sleep(1.1)
    with pytest.raises(SignatureInvalid):
        verify_media_url(media_id=42, viewer_id=7, query=qs)


def test_verify_fails_on_different_viewer():
    qs = sign_media_url(media_id=42, viewer_id=7, ttl_seconds=60)
    with pytest.raises(SignatureInvalid):
        verify_media_url(media_id=42, viewer_id=8, query=qs)
```

- [ ] **Step 2: Implement `app/modules/media/signing.py`**

```python
import hmac
import time
from hashlib import sha256
from urllib.parse import parse_qs, urlencode

from app.config import get_settings

_cfg = get_settings()


class SignatureInvalid(Exception):
    pass


def _payload(media_id: int, viewer_id: int, exp: int) -> bytes:
    return f"{media_id}|{viewer_id}|{exp}".encode()


def _hmac(payload: bytes) -> str:
    return hmac.new(_cfg.secret_key.encode(), payload, sha256).hexdigest()


def sign_media_url(*, media_id: int, viewer_id: int, ttl_seconds: int = 86400) -> str:
    exp = int(time.time()) + ttl_seconds
    sig = _hmac(_payload(media_id, viewer_id, exp))
    return urlencode({"media_id": media_id, "viewer_id": viewer_id, "exp": exp, "sig": sig})


def verify_media_url(*, media_id: int, viewer_id: int, query: str) -> None:
    qs = parse_qs(query.lstrip("?"))

    def _one(key: str) -> str:
        val = qs.get(key)
        if not val:
            raise SignatureInvalid(f"missing {key}")
        return val[0]

    try:
        q_media = int(_one("media_id"))
        q_viewer = int(_one("viewer_id"))
        q_exp = int(_one("exp"))
        q_sig = _one("sig")
    except (ValueError, SignatureInvalid) as e:
        raise SignatureInvalid("bad params") from e

    if q_media != media_id or q_viewer != viewer_id:
        raise SignatureInvalid("media or viewer mismatch")
    if q_exp < int(time.time()):
        raise SignatureInvalid("expired")

    expected = _hmac(_payload(media_id, viewer_id, q_exp))
    if not hmac.compare_digest(expected, q_sig):
        raise SignatureInvalid("signature mismatch")
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_media/test_signing.py -v
```
Expected: 4 passed.

- [ ] **Step 4: Commit**

```bash
git add app/modules/media/signing.py tests/test_media/test_signing.py
git commit -m "feat(media): HMAC-signed URL helpers for opt-in browser/CDN caching"
```

---

**End of Phase G.** Media subsystem complete: model, upload pipeline (MIME validation, magic bytes, sha256 dedup, EXIF, GPS strip, WebP thumbs), upload endpoint, authenticated serve, HMAC signing utility.

---

## Phase H — Today Aggregator & Calendar

### Task 42: TimelineService — assemble "today" data

**Files:**
- Create: `app/modules/timeline/__init__.py`
- Create: `app/modules/timeline/service.py`
- Create: `tests/test_timeline/__init__.py`
- Create: `tests/test_timeline/test_today_data.py`

(`timeline` is a read-only aggregator — no models, no migrations.)

- [ ] **Step 1: Create `app/modules/timeline/__init__.py`** (empty)

- [ ] **Step 2: Create `tests/test_timeline/__init__.py`** (empty)

- [ ] **Step 3: Write failing test `tests/test_timeline/test_today_data.py`**

```python
from datetime import date, timedelta

from app.modules.auth.models import User, UserRole
from app.modules.cycle.service import log_period_start
from app.modules.daily_log.service import get_or_create_entry, toggle_tag
from app.modules.settings.models import ensure_settings
from app.modules.timeline.service import build_today_view


def _user(db, username, role):
    u = User(username=username, display_name=username, password_hash="x", role=role)
    db.add(u); db.flush()
    return u


def test_today_view_no_data_renders_empty_safely(db):
    alice = _user(db, "alice", UserRole.SHE)
    ensure_settings(db, user_id=alice.id)
    v = build_today_view(db, user=alice, partner=None, on=date(2026, 5, 22))
    assert v.on == date(2026, 5, 22)
    assert v.cycle_day is None
    assert v.phase is None
    assert v.my_tags == []
    assert v.partner is None


def test_today_view_with_cycle_history(db):
    alice = _user(db, "alice", UserRole.SHE)
    ensure_settings(db, user_id=alice.id)
    log_period_start(db, user_id=alice.id, start_date=date(2026, 5, 3))
    log_period_start(db, user_id=alice.id, start_date=date(2026, 4, 5))
    log_period_start(db, user_id=alice.id, start_date=date(2026, 3, 10))
    v = build_today_view(db, user=alice, partner=None, on=date(2026, 5, 22))
    assert v.cycle_day == 20  # days since last start +1
    assert v.phase is not None


def test_today_view_my_tags(db):
    alice = _user(db, "alice", UserRole.SHE)
    ensure_settings(db, user_id=alice.id)
    e = get_or_create_entry(db, user_id=alice.id, on=date(2026, 5, 22))
    toggle_tag(db, entry_id=e.id, tag_key="mood_happy")
    toggle_tag(db, entry_id=e.id, tag_key="foreplay")
    v = build_today_view(db, user=alice, partner=None, on=date(2026, 5, 22))
    assert {t.key for t in v.my_tags} == {"mood_happy", "foreplay"}


def test_today_view_partner_tags_when_shared(db):
    alice = _user(db, "alice", UserRole.SHE)
    bob = _user(db, "bob", UserRole.HE)
    ensure_settings(db, user_id=alice.id)
    ensure_settings(db, user_id=bob.id)
    e = get_or_create_entry(db, user_id=alice.id, on=date(2026, 5, 22))
    toggle_tag(db, entry_id=e.id, tag_key="mood_calm")
    v = build_today_view(db, user=bob, partner=alice, on=date(2026, 5, 22))
    assert v.partner is not None
    assert {t.key for t in v.partner.tags} == {"mood_calm"}
```

- [ ] **Step 4: Implement `app/modules/timeline/service.py`**

```python
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.cycle.models import Period
from app.modules.cycle.predictor.combined import CombinedPredictor, Prediction
from app.modules.daily_log.catalog import Tag, find_tag
from app.modules.daily_log.service import list_tags_for_day
from app.modules.settings.visibility import can_view


@dataclass(frozen=True)
class PartnerView:
    display_name: str
    cycle_day: int | None
    phase: str | None
    tags: list[Tag]


@dataclass(frozen=True)
class TodayView:
    on: date
    cycle_day: int | None
    phase: str | None
    my_tags: list[Tag]
    partner: PartnerView | None
    prediction: Prediction | None


def _phase_for(cycle_day: int | None, period_length: int = 5) -> str | None:
    if cycle_day is None:
        return None
    if cycle_day <= period_length:
        return "月经期"
    if cycle_day < 12:
        return "卵泡期"
    if cycle_day <= 16:
        return "排卵期"
    return "黄体期"


def _cycle_day_for(db: Session, *, user_id: int, on: date) -> int | None:
    last = (db.query(Period)
              .filter(Period.user_id == user_id, Period.start_date <= on)
              .order_by(Period.start_date.desc())
              .first())
    if last is None:
        return None
    return (on - last.start_date).days + 1


def _tags_for_day(db: Session, *, user_id: int, on: date) -> list[Tag]:
    rows = list_tags_for_day(db, user_id=user_id, on=on)
    return [t for t in (find_tag(r.tag_key) for r in rows) if t is not None]


def build_today_view(
    db: Session, *, user: User, partner: User | None, on: date,
) -> TodayView:
    cycle_day = _cycle_day_for(db, user_id=user.id, on=on)
    my_tags = _tags_for_day(db, user_id=user.id, on=on)

    partner_view: PartnerView | None = None
    if partner is not None:
        pv_cycle = pv_phase = None
        pv_tags: list[Tag] = []
        if can_view(db, owner_id=partner.id, viewer_id=user.id, data_type="cycle"):
            pv_cycle = _cycle_day_for(db, user_id=partner.id, on=on)
            pv_phase = _phase_for(pv_cycle)
        if can_view(db, owner_id=partner.id, viewer_id=user.id, data_type="daily_log"):
            pv_tags = _tags_for_day(db, user_id=partner.id, on=on)
        partner_view = PartnerView(
            display_name=partner.display_name,
            cycle_day=pv_cycle, phase=pv_phase, tags=pv_tags,
        )

    prediction = None
    if cycle_day is not None:
        prediction = CombinedPredictor().predict(
            db, user_id=user.id, target_date=on,
        )

    return TodayView(
        on=on,
        cycle_day=cycle_day,
        phase=_phase_for(cycle_day),
        my_tags=my_tags,
        partner=partner_view,
        prediction=prediction,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_timeline/test_today_data.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add app/modules/timeline/ tests/test_timeline/
git commit -m "feat(timeline): TodayView aggregator with cycle, tags, predictor, partner view"
```

---

### Task 43: / endpoint (today page) + template

**Files:**
- Create: `app/modules/timeline/router.py`
- Create: `app/templates/pages/today.html`
- Modify: `app/main.py` (mount router; remove `_probe/me`)
- Create: `tests/test_timeline/test_today_page.py`

- [ ] **Step 1: Write failing test `tests/test_timeline/test_today_page.py`**

```python
from app.modules.auth.invite import init_couple_invites


def _login_alice(client, db):
    he, she = init_couple_invites(db, he_display="Bob", she_display="Alice", ttl_days=7)
    db.commit()
    client.post(f"/bind?token={he.token}", data={"username": "bob", "password": "pw-12345678"})
    client.post(f"/bind?token={she.token}", data={"username": "alice", "password": "pw-12345678"})
    client.post("/login", data={"username": "alice", "password": "pw-12345678"})


def test_get_root_renders_today_for_logged_in(client, db):
    _login_alice(client, db)
    r = client.get("/")
    assert r.status_code == 200
    assert "今天" in r.text


def test_get_root_redirects_to_login_when_logged_out(client, db):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.headers["location"].startswith("/login")
```

- [ ] **Step 2: Implement `app/modules/timeline/router.py`**

```python
from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_partner, current_user
from app.modules.auth.models import User
from app.modules.settings.models import ensure_settings
from app.modules.timeline.service import build_today_view
from app.templates_env import templates

router = APIRouter(tags=["timeline"])


@router.get("/", response_class=HTMLResponse)
def today(
    request: Request,
    user: User = Depends(current_user),
    partner: User | None = Depends(current_partner),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    ensure_settings(db, user_id=user.id)
    view = build_today_view(db, user=user, partner=partner, on=date.today())
    db.commit()
    return templates.TemplateResponse(
        request, "pages/today.html",
        {"user": user, "view": view},
    )
```

- [ ] **Step 3: Create `app/templates/pages/today.html`**

```html
{% extends "base.html" %}
{% block title %}今天 · Couple Diary{% endblock %}
{% block content %}
<div style="text-align:center;padding:12px 0">
  <h2 style="margin:0">今天 · {{ view.on }}</h2>
  {% if view.cycle_day %}
    <p class="subtitle">月经周期第 {{ view.cycle_day }} 天</p>
  {% else %}
    <p class="subtitle">尚未记录经期</p>
  {% endif %}
</div>

{% if view.cycle_day %}
<div class="card" style="text-align:center;padding:24px">
  <div style="width:140px;height:140px;margin:0 auto;border-radius:50%;
              background:conic-gradient(var(--accent) 0% {{ (view.cycle_day / 28 * 100)|int }}%,
                                        var(--accent-soft) {{ (view.cycle_day / 28 * 100)|int }}% 100%);
              display:flex;align-items:center;justify-content:center">
    <div style="width:110px;height:110px;border-radius:50%;background:white;
                display:flex;flex-direction:column;align-items:center;justify-content:center">
      <div style="font-size:28px;font-weight:700">D{{ view.cycle_day }}</div>
      <div class="subtitle">{{ view.phase or "" }}</div>
    </div>
  </div>
</div>
{% endif %}

{% if view.prediction and view.prediction.primary.predicted_ovulation %}
<div class="card" hx-get="/today/predictor-card"
     hx-trigger="every 5m [document.visibilityState==='visible']"
     hx-swap="outerHTML">
  <p class="card-title">🎯 排卵预测</p>
  <p>预计排卵：<strong>{{ view.prediction.primary.predicted_ovulation }}</strong>
     <span class="subtitle">(置信度 {{ "%.0f"|format(view.prediction.primary.confidence * 100) }}%)</span></p>
  <p class="subtitle">依据：{{ view.prediction.primary.evidence }}</p>
</div>
{% endif %}

<div class="card">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <p class="card-title" style="margin:0">今天的标签</p>
    <a class="pill" href="/log/today">＋ 记录</a>
  </div>
  {% if view.my_tags %}
    <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:12px">
      {% for t in view.my_tags %}
        <span class="pill" aria-pressed="true">{{ t.emoji }} {{ t.label_zh }}</span>
      {% endfor %}
    </div>
  {% else %}
    <p class="subtitle" style="margin-top:8px">还没记录，点 ＋ 添加</p>
  {% endif %}
</div>

{% if view.partner %}
<div class="card" hx-get="/today/partner-card"
     hx-trigger="every 30s [document.visibilityState==='visible']"
     hx-swap="outerHTML">
  <p class="card-title">{{ view.partner.display_name }} 的今天</p>
  {% if view.partner.cycle_day %}
    <p>D{{ view.partner.cycle_day }} · {{ view.partner.phase or "" }}</p>
  {% endif %}
  {% if view.partner.tags %}
    <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px">
      {% for t in view.partner.tags %}
        <span class="pill">{{ t.emoji }} {{ t.label_zh }}</span>
      {% endfor %}
    </div>
  {% else %}
    <p class="subtitle">TA 今天还没记录</p>
  {% endif %}
</div>
{% endif %}

<div class="card">
  <p class="card-title">快捷入口</p>
  <a class="pill" href="/cycle/log">经期记录</a>
  <a class="pill" href="/bbt/log">体温记录</a>
  <a class="pill" href="/calendar">日历</a>
</div>
{% endblock %}
```

- [ ] **Step 4: Mount router + remove probe in `app/main.py`**

Add import:
```python
from app.modules.timeline.router import router as timeline_router
```
After other includes:
```python
app.include_router(timeline_router)
```
Delete the `/_probe/me` endpoint added in T14 — its purpose is served by `/` now.

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_timeline/test_today_page.py -v
```
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add app/modules/timeline/router.py app/templates/pages/today.html app/main.py tests/test_timeline/test_today_page.py
git commit -m "feat(timeline): GET / today page with cycle ring, tags, partner view"
```

---

### Task 44: HTMX fragments — partner-card and predictor-card

**Files:**
- Modify: `app/modules/timeline/router.py`
- Create: `app/templates/fragments/partner_card.html`
- Create: `app/templates/fragments/predictor_card.html`
- Create: `tests/test_timeline/test_fragments.py`

- [ ] **Step 1: Write failing test `tests/test_timeline/test_fragments.py`**

```python
from app.modules.auth.invite import init_couple_invites


def _login_alice(client, db):
    he, she = init_couple_invites(db, he_display="Bob", she_display="Alice", ttl_days=7)
    db.commit()
    client.post(f"/bind?token={he.token}", data={"username": "bob", "password": "pw-12345678"})
    client.post(f"/bind?token={she.token}", data={"username": "alice", "password": "pw-12345678"})
    client.post("/login", data={"username": "alice", "password": "pw-12345678"})


def test_partner_card_fragment_returns_html_only(client, db):
    _login_alice(client, db)
    r = client.get("/today/partner-card")
    assert r.status_code == 200
    assert "<html" not in r.text  # fragment, no full doc
    assert "card" in r.text


def test_predictor_card_fragment(client, db):
    _login_alice(client, db)
    from datetime import date
    from app.modules.cycle.service import log_period_start
    from app.modules.auth.models import User
    alice = db.query(User).filter_by(username="alice").one()
    log_period_start(db, user_id=alice.id, start_date=date(2026, 5, 1))
    log_period_start(db, user_id=alice.id, start_date=date(2026, 4, 1))
    db.commit()
    r = client.get("/today/predictor-card")
    assert r.status_code == 200
    assert "排卵" in r.text or "预测" in r.text
```

- [ ] **Step 2: Create `app/templates/fragments/partner_card.html`**

```html
<div class="card" hx-get="/today/partner-card"
     hx-trigger="every 30s [document.visibilityState==='visible']"
     hx-swap="outerHTML">
  {% if partner %}
    <p class="card-title">{{ partner.display_name }} 的今天</p>
    {% if partner.cycle_day %}
      <p>D{{ partner.cycle_day }} · {{ partner.phase or "" }}</p>
    {% endif %}
    {% if partner.tags %}
      <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px">
        {% for t in partner.tags %}
          <span class="pill">{{ t.emoji }} {{ t.label_zh }}</span>
        {% endfor %}
      </div>
    {% else %}
      <p class="subtitle">TA 今天还没记录</p>
    {% endif %}
  {% else %}
    <p class="subtitle">尚未绑定伴侣</p>
  {% endif %}
</div>
```

- [ ] **Step 3: Create `app/templates/fragments/predictor_card.html`**

```html
<div class="card" hx-get="/today/predictor-card"
     hx-trigger="every 5m [document.visibilityState==='visible']"
     hx-swap="outerHTML">
  <p class="card-title">🎯 排卵预测</p>
  {% if prediction and prediction.primary.predicted_ovulation %}
    <p>预计排卵：<strong>{{ prediction.primary.predicted_ovulation }}</strong>
       <span class="subtitle">
         (置信度 {{ "%.0f"|format(prediction.primary.confidence * 100) }}%)
       </span></p>
    <p class="subtitle">依据：{{ prediction.primary.evidence }}</p>
    <details style="margin-top:8px">
      <summary class="subtitle" style="cursor:pointer">查看所有信号</summary>
      <ul style="margin:8px 0 0;padding-left:20px">
        {% for e in prediction.evidence %}
          <li class="subtitle">[{{ e.source }}] {{ e.evidence }}
            ({{ "%.0f"|format(e.confidence * 100) }}%)</li>
        {% endfor %}
      </ul>
    </details>
  {% else %}
    <p class="subtitle">数据不足，先记几次经期</p>
  {% endif %}
</div>
```

- [ ] **Step 4: Add fragment routes to `app/modules/timeline/router.py`**

```python
@router.get("/today/partner-card", response_class=HTMLResponse)
def partner_card(
    request: Request,
    user: User = Depends(current_user),
    partner: User | None = Depends(current_partner),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    view = build_today_view(db, user=user, partner=partner, on=date.today())
    return templates.TemplateResponse(
        request, "fragments/partner_card.html", {"partner": view.partner},
    )


@router.get("/today/predictor-card", response_class=HTMLResponse)
def predictor_card(
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    view = build_today_view(db, user=user, partner=None, on=date.today())
    return templates.TemplateResponse(
        request, "fragments/predictor_card.html", {"prediction": view.prediction},
    )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_timeline/test_fragments.py -v
```
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add app/modules/timeline/router.py app/templates/fragments/partner_card.html app/templates/fragments/predictor_card.html tests/test_timeline/test_fragments.py
git commit -m "feat(timeline): partner-card and predictor-card HTMX fragments"
```

---

### Task 45: /calendar page (month view with periods + predictions)

**Files:**
- Modify: `app/modules/cycle/router.py` (add `/calendar` page)
- Create: `app/templates/pages/calendar.html`
- Create: `tests/test_cycle/test_calendar_page.py`

- [ ] **Step 1: Write failing test `tests/test_cycle/test_calendar_page.py`**

```python
from datetime import date

from app.modules.auth.invite import init_couple_invites
from app.modules.cycle.service import log_period_start


def _login_alice(client, db):
    he, she = init_couple_invites(db, he_display="Bob", she_display="Alice", ttl_days=7)
    db.commit()
    client.post(f"/bind?token={he.token}", data={"username": "bob", "password": "pw-12345678"})
    client.post(f"/bind?token={she.token}", data={"username": "alice", "password": "pw-12345678"})
    client.post("/login", data={"username": "alice", "password": "pw-12345678"})


def test_calendar_renders_current_month(client, db):
    _login_alice(client, db)
    r = client.get("/calendar")
    assert r.status_code == 200
    assert "日历" in r.text or "calendar" in r.text


def test_calendar_marks_period_days(client, db):
    _login_alice(client, db)
    from app.modules.auth.models import User
    alice = db.query(User).filter_by(username="alice").one()
    log_period_start(db, user_id=alice.id, start_date=date(2026, 5, 5))
    db.commit()
    r = client.get("/calendar?ym=2026-05")
    assert r.status_code == 200
    assert "data-period=\"true\"" in r.text or "period-day" in r.text


def test_calendar_navigates_months(client, db):
    _login_alice(client, db)
    r = client.get("/calendar?ym=2026-03")
    assert r.status_code == 200
    assert "2026" in r.text
```

- [ ] **Step 2: Append calendar handler to `app/modules/cycle/router.py`**

```python
import calendar as _stdcal
from datetime import date, timedelta

# (existing imports already include date)


@router.get("/calendar", response_class=HTMLResponse)
def calendar_page(
    request: Request,
    ym: str | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    if ym:
        year, month = (int(x) for x in ym.split("-"))
    else:
        today = date.today()
        year, month = today.year, today.month

    # Build a flat list of days in the month
    _, ndays = _stdcal.monthrange(year, month)
    days = [date(year, month, d) for d in range(1, ndays + 1)]

    # Mark period days (from periods within ±1 month for context)
    periods = list_periods(db, user_id=user.id)
    period_dates: set[date] = set()
    for p in periods:
        start = p.start_date
        end = p.end_date or start
        d = start
        while d <= end:
            period_dates.add(d); d += timedelta(days=1)

    # Predict next period start (if we have at least one full cycle)
    from app.modules.cycle.predictor.calendar import CalendarSignal
    sig = CalendarSignal().evaluate(db, user_id=user.id, target_date=date.today())
    next_period = sig.extra.get("next_start") if sig and sig.extra else None
    ovulation = sig.predicted_ovulation if sig else None

    prev_y, prev_m = (year - 1, 12) if month == 1 else (year, month - 1)
    next_y, next_m = (year + 1, 1) if month == 12 else (year, month + 1)

    return templates.TemplateResponse(
        request, "pages/calendar.html",
        {
            "year": year, "month": month, "days": days,
            "period_dates": period_dates,
            "next_period": next_period,
            "ovulation": ovulation,
            "prev_ym": f"{prev_y:04d}-{prev_m:02d}",
            "next_ym": f"{next_y:04d}-{next_m:02d}",
            "first_weekday": _stdcal.monthrange(year, month)[0],  # 0=Mon
        },
    )
```

- [ ] **Step 3: Create `app/templates/pages/calendar.html`**

```html
{% extends "base.html" %}
{% block title %}日历 · Couple Diary{% endblock %}
{% block head %}
<style>
  .cal { display:grid; grid-template-columns: repeat(7, 1fr); gap:4px; }
  .cal-head { text-align:center; font-size:11px; color:var(--text-muted); padding:6px 0; }
  .cal-cell { aspect-ratio:1; display:flex; align-items:center; justify-content:center;
              border-radius:8px; font-size:14px; }
  .cal-cell[data-period="true"] { background: var(--accent); color:white; font-weight:600; }
  .cal-cell[data-predicted-period="true"] {
    background: transparent; border: 2px dashed var(--accent); color: var(--accent-2);
  }
  .cal-cell[data-ovulation="true"] { background: #c8a8ff; color:white; }
  .cal-cell.empty { visibility:hidden; }
</style>
{% endblock %}
{% block content %}
<div style="display:flex;justify-content:space-between;align-items:center;margin:0 8px">
  <a class="pill" href="/calendar?ym={{ prev_ym }}">‹ 上月</a>
  <h2 style="margin:0">{{ year }} 年 {{ month }} 月</h2>
  <a class="pill" href="/calendar?ym={{ next_ym }}">下月 ›</a>
</div>

<div class="card">
  <div class="cal">
    {% for label in ["一", "二", "三", "四", "五", "六", "日"] %}
      <div class="cal-head">{{ label }}</div>
    {% endfor %}
    {% for _ in range(first_weekday) %}
      <div class="cal-cell empty"></div>
    {% endfor %}
    {% for d in days %}
      <a href="/log/{{ d.isoformat() }}" class="cal-cell"
         {% if d in period_dates %}data-period="true"{% endif %}
         {% if next_period and d == next_period %}data-predicted-period="true"{% endif %}
         {% if ovulation and d == ovulation %}data-ovulation="true"{% endif %}>
        {{ d.day }}
      </a>
    {% endfor %}
  </div>
  <div style="margin-top:12px;display:flex;gap:12px;font-size:11px">
    <span><span style="display:inline-block;width:12px;height:12px;background:var(--accent);border-radius:3px"></span> 经期</span>
    <span><span style="display:inline-block;width:10px;height:10px;border:2px dashed var(--accent);border-radius:3px"></span> 预测经期</span>
    <span><span style="display:inline-block;width:12px;height:12px;background:#c8a8ff;border-radius:3px"></span> 排卵日</span>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_cycle/test_calendar_page.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/modules/cycle/router.py app/templates/pages/calendar.html tests/test_cycle/test_calendar_page.py
git commit -m "feat(cycle): /calendar month view with period markers and predictions"
```

---

### Task 46: /me page (about us) + /me/settings page

**Files:**
- Modify: `app/modules/settings/__init__.py`
- Create: `app/modules/settings/router.py`
- Create: `app/templates/pages/me.html`
- Create: `app/templates/pages/settings.html`
- Modify: `app/main.py`
- Create: `tests/test_settings/test_pages.py`

- [ ] **Step 1: Write failing test `tests/test_settings/test_pages.py`**

```python
from app.modules.auth.invite import init_couple_invites


def _login_alice(client, db):
    he, she = init_couple_invites(db, he_display="Bob", she_display="Alice", ttl_days=7)
    db.commit()
    client.post(f"/bind?token={he.token}", data={"username": "bob", "password": "pw-12345678"})
    client.post(f"/bind?token={she.token}", data={"username": "alice", "password": "pw-12345678"})
    client.post("/login", data={"username": "alice", "password": "pw-12345678"})


def test_get_me_page(client, db):
    _login_alice(client, db)
    r = client.get("/me")
    assert r.status_code == 200
    assert "我们" in r.text or "Alice" in r.text


def test_get_me_settings_page(client, db):
    _login_alice(client, db)
    r = client.get("/me/settings")
    assert r.status_code == 200
    assert "可见性" in r.text or "visibility" in r.text


def test_post_visibility_change(client, db):
    _login_alice(client, db)
    r = client.post("/me/settings/visibility",
                    data={"data_type": "diary", "visibility": "shared"},
                    follow_redirects=False)
    assert r.status_code in (200, 303)
    from app.modules.auth.models import User
    from app.modules.settings.models import UserSettings
    alice = db.query(User).filter_by(username="alice").one()
    s = db.query(UserSettings).filter_by(user_id=alice.id).one()
    assert s.visibility["diary"] == "shared"
```

- [ ] **Step 2: Implement `app/modules/settings/router.py`**

```python
from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_partner, current_user
from app.errors import ValidationFailed
from app.modules.auth.models import Couple, User
from app.modules.settings.models import DEFAULT_VISIBILITY, ensure_settings
from app.modules.settings.visibility import set_visibility, Visibility
from app.templates_env import templates

router = APIRouter(tags=["settings"])

DATA_TYPE_LABELS = {
    "cycle": "经期",
    "bbt": "基础体温",
    "daily_log": "每日标签（心情/症状/亲密）",
    "diary": "日记",
    "trip": "旅行",
    "media": "上传文件",
    "health_metrics": "健康指标（RHR/HRV/睡眠）",
}


@router.get("/me", response_class=HTMLResponse)
def me_page(
    request: Request,
    user: User = Depends(current_user),
    partner: User | None = Depends(current_partner),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    couple = db.query(Couple).first()
    days_together = (date.today() - couple.bonded_at.date()).days if couple else None
    return templates.TemplateResponse(
        request, "pages/me.html",
        {"user": user, "partner": partner, "days_together": days_together},
    )


@router.get("/me/settings", response_class=HTMLResponse)
def settings_page(
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    s = ensure_settings(db, user_id=user.id)
    db.commit()
    return templates.TemplateResponse(
        request, "pages/settings.html",
        {"user": user, "settings": s, "labels": DATA_TYPE_LABELS},
    )


@router.post("/me/settings/visibility")
def update_visibility(
    data_type: str = Form(...),
    visibility: str = Form(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if data_type not in DEFAULT_VISIBILITY:
        raise ValidationFailed(f"unknown data_type: {data_type}")
    if visibility not in ("shared", "private"):
        raise ValidationFailed(f"unknown visibility: {visibility}")
    set_visibility(db, owner_id=user.id, data_type=data_type,
                   visibility=visibility)  # type: ignore[arg-type]
    db.commit()
    return RedirectResponse(url="/me/settings", status_code=303)
```

- [ ] **Step 3: Create `app/templates/pages/me.html`**

```html
{% extends "base.html" %}
{% block title %}我们 · Couple Diary{% endblock %}
{% block content %}
<h2 style="margin-top:0">我们</h2>

<div class="card" style="text-align:center;padding:32px 16px">
  <div style="display:flex;justify-content:center;gap:16px;margin-bottom:16px">
    <div>
      <div style="width:64px;height:64px;border-radius:50%;background:var(--accent-soft);
                  display:flex;align-items:center;justify-content:center;font-size:24px">
        {{ user.display_name[0] }}
      </div>
      <p class="subtitle" style="margin:8px 0 0">{{ user.display_name }}</p>
    </div>
    <div style="display:flex;align-items:center;color:var(--accent)">💗</div>
    {% if partner %}
      <div>
        <div style="width:64px;height:64px;border-radius:50%;background:var(--accent-soft);
                    display:flex;align-items:center;justify-content:center;font-size:24px">
          {{ partner.display_name[0] }}
        </div>
        <p class="subtitle" style="margin:8px 0 0">{{ partner.display_name }}</p>
      </div>
    {% else %}
      <div>
        <div style="width:64px;height:64px;border-radius:50%;border:2px dashed var(--accent);
                    display:flex;align-items:center;justify-content:center">?</div>
        <p class="subtitle" style="margin:8px 0 0">未绑定</p>
      </div>
    {% endif %}
  </div>
  {% if days_together is not none %}
    <p>在一起 <strong>{{ days_together }}</strong> 天</p>
  {% endif %}
</div>

<div class="card">
  <a href="/me/settings" style="display:block;padding:12px 0">⚙️ 设置</a>
  <form method="post" action="/logout" style="margin:0">
    <button class="pill" style="background:transparent;color:var(--danger)" type="submit">
      退出登录
    </button>
  </form>
</div>
{% endblock %}
```

- [ ] **Step 4: Create `app/templates/pages/settings.html`**

```html
{% extends "base.html" %}
{% block title %}设置 · Couple Diary{% endblock %}
{% block content %}
<h2 style="margin-top:0">设置</h2>

<div class="card">
  <p class="card-title">伴侣可见性</p>
  <p class="subtitle">控制 TA 能看到你的哪些数据</p>
  {% for key, label in labels.items() %}
    <form method="post" action="/me/settings/visibility"
          style="display:flex;justify-content:space-between;align-items:center;
                 padding:10px 0;border-bottom:1px solid var(--accent-soft)">
      <span>{{ label }}</span>
      <span>
        <input type="hidden" name="data_type" value="{{ key }}">
        <select class="input" name="visibility"
                onchange="this.form.submit()" style="width:auto;padding:6px 12px">
          <option value="shared" {% if settings.visibility.get(key) == "shared" %}selected{% endif %}>
            共享给 TA
          </option>
          <option value="private" {% if settings.visibility.get(key) == "private" %}selected{% endif %}>
            仅自己
          </option>
        </select>
      </span>
    </form>
  {% endfor %}
</div>
{% endblock %}
```

- [ ] **Step 5: Mount router in `app/main.py`**

Add import:
```python
from app.modules.settings.router import router as settings_router
```
After other includes:
```python
app.include_router(settings_router)
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_settings/test_pages.py -v
```
Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add app/modules/settings/router.py app/templates/pages/me.html app/templates/pages/settings.html app/main.py tests/test_settings/test_pages.py
git commit -m "feat(settings): /me and /me/settings pages with visibility controls"
```

---

### Task 47-50 collapsed: ensure dependencies + smoke run

(There are no further UI/settings tasks remaining for M1 beyond what is now in place. The "HealthMetric manual entry" originally numbered T50 is consumed by M3 — it's not needed for M1 since BBT alone satisfies the predictor. Skip it.)

The settings page now allows changing visibility for all data types planned for M1.

- [ ] **Run full suite to ensure Phase H is green end-to-end**

```bash
.venv/Scripts/python.exe -m pytest -v --cov=app --cov-report=term-missing
```
Expected: all green; coverage report printed.

- [ ] **Manual end-to-end smoke (local)**

```bash
.venv/Scripts/python.exe -m couple_diary init-couple --he Bob --she Alice \
    --base-url http://localhost:8001
# Open both bind URLs in private windows, set passwords
# Log in as Alice → see Today page → click "记录" → toggle some tags → see them appear
# Log in as Bob → see Alice's tags in "Alice 的今天" card
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8001 --reload
```

- [ ] **Commit (if any fixes needed during smoke)**

```bash
git commit -am "fix: any issues found during Phase H manual smoke (if any)"
```

---

**End of Phase H + I.** Today page, calendar, /me, /me/settings — all logged-in routes functional. M1 user experience complete in local dev. Phase J wires it up for production deployment.

---

## Phase J — Backup, Scheduler, Deployment

### Task 51: APScheduler integration

**Files:**
- Create: `app/scheduler.py`
- Modify: `app/main.py` (start/stop scheduler in lifespan)
- Create: `tests/test_scheduler.py`

- [ ] **Step 1: Write failing test `tests/test_scheduler.py`**

```python
from app.scheduler import build_scheduler


def test_scheduler_built_with_expected_jobs():
    sched = build_scheduler()
    job_ids = {j.id for j in sched.get_jobs()}
    must = {"backup_db", "backup_files_mirror", "cleanup_orphan_media"}
    assert must <= job_ids
    sched.shutdown(wait=False)
```

- [ ] **Step 2: Implement `app/scheduler.py`**

```python
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

log = logging.getLogger(__name__)


def _job_backup_db() -> None:
    from app.tasks.backup import backup_database
    try:
        backup_database()
    except Exception:
        log.exception("backup_db failed")


def _job_backup_files() -> None:
    from app.tasks.backup import mirror_uploads
    try:
        mirror_uploads()
    except Exception:
        log.exception("backup_files_mirror failed")


def _job_cleanup_orphans() -> None:
    from app.tasks.cleanup import cleanup_orphan_media
    try:
        cleanup_orphan_media()
    except Exception:
        log.exception("cleanup_orphan_media failed")


def build_scheduler() -> BackgroundScheduler:
    sched = BackgroundScheduler(timezone="Asia/Shanghai")
    sched.add_job(_job_backup_db, CronTrigger(hour=3, minute=0),
                  id="backup_db", replace_existing=True)
    sched.add_job(_job_backup_files, CronTrigger(hour=3, minute=15),
                  id="backup_files_mirror", replace_existing=True)
    sched.add_job(_job_cleanup_orphans, CronTrigger(hour=3, minute=30),
                  id="cleanup_orphan_media", replace_existing=True)
    return sched


_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = build_scheduler()
    _scheduler.start()
    log.info("scheduler started", extra={"jobs": [j.id for j in _scheduler.get_jobs()]})


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
```

- [ ] **Step 3: Wire into `app/main.py` lifespan**

Update lifespan:
```python
from app.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging(level="INFO" if settings.app_env == "production" else "DEBUG")
    if settings.app_env != "test":
        start_scheduler()
    yield
    if settings.app_env != "test":
        stop_scheduler()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/Scripts/python.exe -m pytest tests/test_scheduler.py -v
```
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add app/scheduler.py app/main.py tests/test_scheduler.py
git commit -m "feat(scheduler): APScheduler with backup and cleanup jobs"
```

---

### Task 52: Database backup task (mysqldump → gzipped file)

**Files:**
- Create: `app/tasks/__init__.py`
- Create: `app/tasks/backup.py`
- Create: `tests/test_tasks/__init__.py`
- Create: `tests/test_tasks/test_backup.py`

- [ ] **Step 1: Create `tests/test_tasks/__init__.py`** (empty)

- [ ] **Step 2: Write failing test `tests/test_tasks/test_backup.py`**

```python
from pathlib import Path

from app.tasks.backup import _dump_command, mirror_uploads


def test_dump_command_uses_single_transaction():
    cmd = _dump_command(
        host="127.0.0.1", port=3306, user="couple", password="pw",
        database="couple_diary",
    )
    assert "--single-transaction" in cmd
    assert "couple_diary" in cmd
    assert "-h127.0.0.1" in cmd or "-h" in cmd
    assert "--password=pw" in cmd or "-ppw" in cmd


def test_mirror_uploads_copies_tree(tmp_path):
    src = tmp_path / "uploads"; src.mkdir()
    (src / "a.txt").write_text("hello")
    sub = src / "1" / "2026" / "05"; sub.mkdir(parents=True)
    (sub / "b.txt").write_text("world")
    dst = tmp_path / "mirror"
    from unittest.mock import patch
    from app.config import Settings
    with patch.object(__import__("app.tasks.backup", fromlist=["_settings"]),
                      "_settings", Settings(
                          app_env="test",
                          secret_key="x"*40,
                          database_url="mysql+pymysql://x:y@127.0.0.1/test",
                          upload_dir=src, backup_dir=tmp_path, log_dir=tmp_path,
                      )):
        mirror_uploads(target_dir=dst)
    assert (dst / "a.txt").read_text() == "hello"
    assert (dst / "1" / "2026" / "05" / "b.txt").read_text() == "world"
```

- [ ] **Step 3: Implement `app/tasks/__init__.py`** (empty)

- [ ] **Step 4: Implement `app/tasks/backup.py`**

```python
import gzip
import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from app.config import get_settings

log = logging.getLogger(__name__)
_settings = get_settings()


def _parse_url(url: str) -> dict[str, str | int]:
    p = urlparse(url)
    return {
        "host": p.hostname or "127.0.0.1",
        "port": p.port or 3306,
        "user": p.username or "",
        "password": p.password or "",
        "database": (p.path or "/").lstrip("/").split("?")[0],
    }


def _dump_command(*, host: str, port: int, user: str, password: str,
                  database: str) -> list[str]:
    return [
        "mysqldump", "--single-transaction", "--quick",
        "--routines", "--triggers",
        f"-h{host}", f"-P{port}", f"-u{user}", f"--password={password}",
        database,
    ]


def backup_database(target_dir: Path | None = None) -> Path:
    cfg = _parse_url(str(_settings.database_url))
    target_dir = target_dir or Path(str(_settings.backup_dir)) / "db"
    target_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = target_dir / f"{ts}.sql.gz"
    log.info("backup_db_start", extra={"out": str(out_path)})
    proc = subprocess.Popen(
        _dump_command(**cfg),  # type: ignore[arg-type]
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    with gzip.open(out_path, "wb") as f:
        assert proc.stdout is not None
        shutil.copyfileobj(proc.stdout, f)
    _, err = proc.communicate(timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(f"mysqldump failed (rc={proc.returncode}): {err.decode()[:500]}")
    log.info("backup_db_done", extra={"out": str(out_path),
                                      "size": out_path.stat().st_size})
    # Retention: keep last 30
    files = sorted(target_dir.glob("*.sql.gz"), key=lambda p: p.stat().st_mtime)
    for old in files[:-30]:
        old.unlink(missing_ok=True)
    return out_path


def mirror_uploads(target_dir: Path | None = None) -> Path:
    target_dir = target_dir or Path(str(_settings.backup_dir)) / "uploads-mirror"
    target_dir.mkdir(parents=True, exist_ok=True)
    src = Path(str(_settings.upload_dir))
    if src.exists():
        # rsync-like behavior using copytree with replace semantics
        for item in src.rglob("*"):
            if item.is_file():
                rel = item.relative_to(src)
                dst_file = target_dir / rel
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst_file)
    log.info("mirror_uploads_done", extra={"target": str(target_dir)})
    return target_dir
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_tasks/test_backup.py -v
```
Expected: 2 passed (mirror test runs; dump_command shape test runs without invoking mysqldump).

- [ ] **Step 6: Manual smoke for backup_database (requires mysqldump installed)**

On the server:
```bash
ssh -i .../tencent_cloud root@150.158.3.104 \
    "which mysqldump"
# Expected: /usr/bin/mysqldump
```
(If missing on production server, `dnf install mariadb` brings it in.)

- [ ] **Step 7: Commit**

```bash
git add app/tasks/ tests/test_tasks/
git commit -m "feat(tasks): mysqldump-based DB backup and file mirror tasks"
```

---

### Task 53: Orphan media cleanup task

**Files:**
- Create: `app/tasks/cleanup.py`
- Create: `tests/test_tasks/test_cleanup.py`

- [ ] **Step 1: Write failing test `tests/test_tasks/test_cleanup.py`**

```python
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.modules.auth.models import User, UserRole
from app.modules.media.models import Media, MediaKind
from app.tasks.cleanup import cleanup_orphan_media


def _user(db):
    u = User(username="a", display_name="A", password_hash="x", role=UserRole.SHE)
    db.add(u); db.flush()
    return u


def test_cleanup_removes_orphans_older_than_threshold(db, tmp_path):
    u = _user(db)
    p = tmp_path / "orphan.webp"; p.write_bytes(b"x")
    pt = tmp_path / "orphan.thumb.webp"; pt.write_bytes(b"y")
    m = Media(
        owner_id=u.id, kind=MediaKind.IMAGE,
        original_path=str(p), thumb_path=str(pt),
        size=1, mime="image/webp", sha256="z" * 64,
    )
    db.add(m); db.flush()
    # Force-age
    m.created_at = datetime.now(timezone.utc) - timedelta(days=8)
    db.flush()
    db.commit()
    removed = cleanup_orphan_media(threshold_days=7)
    assert removed == 1
    assert not p.exists()
    assert not pt.exists()
    assert db.query(Media).filter_by(id=m.id).first() is None


def test_cleanup_keeps_recent_orphans(db, tmp_path):
    u = _user(db)
    p = tmp_path / "fresh.webp"; p.write_bytes(b"x")
    pt = tmp_path / "fresh.thumb.webp"; pt.write_bytes(b"y")
    m = Media(
        owner_id=u.id, kind=MediaKind.IMAGE,
        original_path=str(p), thumb_path=str(pt),
        size=1, mime="image/webp", sha256="z" * 64,
    )
    db.add(m); db.flush(); db.commit()
    removed = cleanup_orphan_media(threshold_days=7)
    assert removed == 0
    assert p.exists()


def test_cleanup_keeps_referenced_media(db, tmp_path):
    from datetime import date
    from app.modules.cycle.service import log_period_start
    from app.modules.media.models import CycleAttachment
    u = _user(db)
    p = tmp_path / "linked.webp"; p.write_bytes(b"x")
    pt = tmp_path / "linked.thumb.webp"; pt.write_bytes(b"y")
    m = Media(
        owner_id=u.id, kind=MediaKind.IMAGE,
        original_path=str(p), thumb_path=str(pt),
        size=1, mime="image/webp", sha256="z" * 64,
    )
    db.add(m); db.flush()
    period = log_period_start(db, user_id=u.id, start_date=date(2026, 5, 1))
    db.add(CycleAttachment(period_id=period.id, media_id=m.id, kind="ovulation_strip"))
    db.flush()
    m.created_at = datetime.now(timezone.utc) - timedelta(days=30)
    db.flush(); db.commit()
    removed = cleanup_orphan_media(threshold_days=7)
    assert removed == 0
```

- [ ] **Step 2: Implement `app/tasks/cleanup.py`**

```python
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.modules.media.models import (
    CycleAttachment, DailyAttachment, Media,
)

log = logging.getLogger(__name__)


def cleanup_orphan_media(threshold_days: int = 7) -> int:
    """Delete Media rows + files that have no link from any consumer table
    AND are older than threshold_days. Returns count of rows removed."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=threshold_days)
    with SessionLocal() as db:
        # Subqueries of referenced media_ids
        cycle_ids = select(CycleAttachment.media_id)
        daily_ids = select(DailyAttachment.media_id)
        # (Future: add diary_media, trip_media when those tables exist in M2)
        orphans = (
            db.query(Media)
            .filter(Media.created_at < cutoff)
            .filter(~Media.id.in_(cycle_ids))
            .filter(~Media.id.in_(daily_ids))
            .all()
        )
        removed = 0
        for m in orphans:
            for path in (m.original_path, m.thumb_path):
                p = Path(path)
                if p.exists():
                    try:
                        p.unlink()
                    except OSError as e:
                        log.warning("cleanup_unlink_failed",
                                    extra={"path": path, "err": str(e)})
            db.delete(m)
            removed += 1
        db.commit()
    log.info("cleanup_orphan_media_done", extra={"removed": removed})
    return removed
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
.venv/Scripts/python.exe -m pytest tests/test_tasks/test_cleanup.py -v
```
Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add app/tasks/cleanup.py tests/test_tasks/test_cleanup.py
git commit -m "feat(tasks): orphan media cleanup for files with no link references"
```

---

### Task 54: systemd unit + Nginx self-signed config files

**Files:**
- Create: `deploy/couple-diary.service`
- Create: `deploy/nginx-couple-diary.conf`
- Create: `deploy/mariadb-hardening.cnf`

(These are config templates copied into place by `bootstrap.sh`. No tests; manual verification only.)

- [ ] **Step 1: Create `deploy/couple-diary.service`**

```ini
[Unit]
Description=Couple Diary App
After=network.target mariadb.service

[Service]
Type=simple
User=couple
Group=couple
WorkingDirectory=/opt/couple_diary
EnvironmentFile=/opt/couple_diary/.env.production
ExecStart=/opt/couple_diary/.venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 --port 8000 --workers 2 --proxy-headers \
    --forwarded-allow-ips=127.0.0.1
Restart=on-failure
RestartSec=5
MemoryMax=600M
TasksMax=200
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/data /var/log/couple_diary
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 2: Create `deploy/nginx-couple-diary.conf`**

```nginx
server {
    listen 80;
    server_name 150.158.3.104;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name 150.158.3.104;

    ssl_certificate     /etc/nginx/ssl/couple.crt;
    ssl_certificate_key /etc/nginx/ssl/couple.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;

    # HSTS disabled while using self-signed (avoid locking browser in)
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy
        "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; font-src 'self' data:;"
        always;

    client_max_body_size 60M;
    client_body_timeout 60s;
    keepalive_timeout 65s;

    location /static/ {
        alias /opt/couple_diary/app/static/;
        expires 30d;
        access_log off;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
        proxy_buffering off;  # important for streaming media
    }
}
```

- [ ] **Step 3: Create `deploy/mariadb-hardening.cnf`**

```ini
# Drop this into /etc/my.cnf.d/01-couple-diary-hardening.cnf
[mysqld]
bind-address = 127.0.0.1
skip-name-resolve = 1
max_connections = 50
slow_query_log = 1
slow_query_log_file = /var/log/mariadb/slow.log
long_query_time = 0.5
```

- [ ] **Step 4: Commit**

```bash
git add deploy/
git commit -m "chore(deploy): systemd unit, nginx self-signed config, MariaDB hardening"
```

---

### Task 55: bootstrap.sh — first-time server deployment

**Files:**
- Create: `scripts/bootstrap.sh`

- [ ] **Step 1: Create `scripts/bootstrap.sh`**

```bash
#!/usr/bin/env bash
# First-time deployment on OpenCloudOS 9.x
# Usage: run as root on the server after cloning the repo to /opt/couple_diary
#   curl -fsSL https://your-git-host/.../bootstrap.sh | bash
# OR
#   cd /opt/couple_diary && sudo bash scripts/bootstrap.sh
set -euo pipefail

APP_DIR=/opt/couple_diary
DATA_DIR=/data
LOG_DIR=/var/log/couple_diary
APP_USER=couple
DB_NAME=couple_diary
DB_NAME_TEST=couple_diary_test
SERVER_IP="${SERVER_IP:-150.158.3.104}"

[[ "$EUID" -ne 0 ]] && { echo "must run as root"; exit 1; }
[[ ! -d "$APP_DIR" ]] && { echo "$APP_DIR missing — git clone first"; exit 1; }

echo "==> Installing system packages"
dnf install -y python3.11 python3.11-devel gcc openssl nginx mariadb tar gzip || true

echo "==> Creating system user $APP_USER"
id "$APP_USER" >/dev/null 2>&1 || useradd -r -s /usr/sbin/nologin "$APP_USER"

echo "==> Creating data + log directories"
mkdir -p "$DATA_DIR/uploads" "$DATA_DIR/backups/db" \
         "$DATA_DIR/backups/uploads-mirror" "$DATA_DIR/backups/pre-deploy" \
         "$LOG_DIR"
chown -R "$APP_USER:$APP_USER" "$DATA_DIR" "$LOG_DIR"
chmod 700 "$DATA_DIR/uploads" "$DATA_DIR/backups"

echo "==> Hardening MariaDB (bind 127.0.0.1)"
install -m 0644 "$APP_DIR/deploy/mariadb-hardening.cnf" \
    /etc/my.cnf.d/01-couple-diary-hardening.cnf
systemctl restart mariadb

echo "==> Creating databases + business account"
read -srp "Choose a strong DB password for app user '$APP_USER': " DB_PWD; echo
mysql -uroot <<SQL
CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS $DB_NAME_TEST CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$APP_USER'@'127.0.0.1' IDENTIFIED BY '$DB_PWD';
GRANT ALL ON $DB_NAME.* TO '$APP_USER'@'127.0.0.1';
GRANT ALL ON $DB_NAME_TEST.* TO '$APP_USER'@'127.0.0.1';
FLUSH PRIVILEGES;
SQL

echo "==> Python venv + dependencies"
cd "$APP_DIR"
python3.11 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e .
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo "==> Generating .env.production"
SECRET_KEY=$(openssl rand -hex 32)
cat >.env.production <<EOF
APP_ENV=production
SECRET_KEY=$SECRET_KEY
DATABASE_URL=mysql+pymysql://$APP_USER:$DB_PWD@127.0.0.1/$DB_NAME?charset=utf8mb4
DATABASE_TEST_URL=mysql+pymysql://$APP_USER:$DB_PWD@127.0.0.1/$DB_NAME_TEST?charset=utf8mb4
UPLOAD_DIR=$DATA_DIR/uploads
BACKUP_DIR=$DATA_DIR/backups
LOG_DIR=$LOG_DIR
SESSION_COOKIE_NAME=cdsid
SESSION_MAX_AGE_DAYS=30
COOKIE_SECURE=true
EOF
chmod 600 .env.production
chown "$APP_USER:$APP_USER" .env.production

echo "==> Running Alembic migrations"
sudo -u "$APP_USER" .venv/bin/alembic upgrade head

echo "==> Self-signed TLS cert"
mkdir -p /etc/nginx/ssl
openssl req -x509 -newkey rsa:4096 -nodes \
    -keyout /etc/nginx/ssl/couple.key \
    -out /etc/nginx/ssl/couple.crt \
    -days 365 -subj "/CN=$SERVER_IP"
chmod 600 /etc/nginx/ssl/couple.key

echo "==> Installing nginx config"
install -m 0644 "$APP_DIR/deploy/nginx-couple-diary.conf" \
    /etc/nginx/conf.d/couple-diary.conf
nginx -t
systemctl enable --now nginx
systemctl reload nginx

echo "==> Installing systemd unit"
install -m 0644 "$APP_DIR/deploy/couple-diary.service" \
    /etc/systemd/system/couple-diary.service
systemctl daemon-reload
systemctl enable --now couple-diary

echo "==> Smoke check"
sleep 3
curl -fsSk https://127.0.0.1/healthz && echo " ✓ healthz OK"

echo
echo "==> Generating invite tokens"
read -p "Display name for HE (you): " HE_NAME
read -p "Display name for SHE (partner): " SHE_NAME
sudo -u "$APP_USER" .venv/bin/couple-diary init-couple \
    --he "$HE_NAME" --she "$SHE_NAME" \
    --base-url "https://$SERVER_IP"

echo
echo "==> Done. Share the SHE link with your partner, use the HE link yourself."
echo "==> Note: first browser visit will warn about self-signed cert — accept it once."
```

- [ ] **Step 2: Make executable**

```bash
chmod +x scripts/bootstrap.sh
```

- [ ] **Step 3: Commit**

```bash
git add scripts/bootstrap.sh
git commit -m "feat(deploy): bootstrap.sh first-time server installer"
```

---

### Task 56: deploy.sh — update + auto-rollback

**Files:**
- Create: `scripts/deploy.sh`

- [ ] **Step 1: Create `scripts/deploy.sh`**

```bash
#!/usr/bin/env bash
# Run on the server as root from /opt/couple_diary after git pull.
set -euo pipefail

APP_DIR=/opt/couple_diary
DATA_DIR=/data
APP_USER=couple

cd "$APP_DIR"

echo "==> Pre-deploy DB snapshot"
TS=$(date +%Y%m%d-%H%M%S)
SNAP="$DATA_DIR/backups/pre-deploy/$TS.sql.gz"
mkdir -p "$(dirname "$SNAP")"
# Read DB credentials from .env.production
. <(grep '^DATABASE_URL=' .env.production)
DB_URL_NOPREFIX="${DATABASE_URL#mysql+pymysql://}"
DB_AUTH="${DB_URL_NOPREFIX%@*}"
DB_HOSTDB="${DB_URL_NOPREFIX#*@}"
DB_USER="${DB_AUTH%%:*}"
DB_PWD="${DB_AUTH#*:}"
DB_HOST="${DB_HOSTDB%%/*}"
DB_NAME="${DB_HOSTDB#*/}"; DB_NAME="${DB_NAME%%\?*}"
mysqldump --single-transaction "-h$DB_HOST" "-u$DB_USER" "--password=$DB_PWD" \
    "$DB_NAME" | gzip > "$SNAP"
echo "  snapshot: $SNAP"

CURRENT_SHA=$(git rev-parse HEAD)

echo "==> Installing deps"
sudo -u "$APP_USER" .venv/bin/pip install -e .

echo "==> Running migrations"
sudo -u "$APP_USER" .venv/bin/alembic upgrade head

echo "==> Restarting service"
systemctl restart couple-diary

echo "==> Health check"
sleep 3
if ! curl -fsSk https://127.0.0.1/healthz >/dev/null; then
    echo "  HEALTHZ FAILED — rolling back to $CURRENT_SHA~1"
    git reset --hard HEAD~1
    sudo -u "$APP_USER" .venv/bin/pip install -e .
    # Restore DB snapshot
    gunzip < "$SNAP" | mysql "-h$DB_HOST" "-u$DB_USER" "--password=$DB_PWD" "$DB_NAME"
    systemctl restart couple-diary
    sleep 3
    curl -fsSk https://127.0.0.1/healthz
    echo "  rollback complete"
    exit 1
fi

echo "==> Deploy successful (commit $CURRENT_SHA)"
```

- [ ] **Step 2: Make executable + commit**

```bash
chmod +x scripts/deploy.sh
git add scripts/deploy.sh
git commit -m "feat(deploy): deploy.sh with pre-deploy snapshot and healthz rollback"
```

---

### Task 57: Production runbook

**Files:**
- Create: `docs/runbook.md`

- [ ] **Step 1: Create `docs/runbook.md`**

```markdown
# Couple Diary Runbook

## Service status
```bash
systemctl status couple-diary
journalctl -u couple-diary -n 100 --no-pager
tail -f /var/log/couple_diary/app.log
```

## Common issues

### App won't start
1. `journalctl -u couple-diary -n 50` — check startup error
2. Common causes:
   - `.env.production` permissions wrong (`chmod 600`, `chown couple:couple`)
   - DB unreachable: `mysql -ucouple -p$PWD -h127.0.0.1 couple_diary -e 'SELECT 1'`
   - Migration pending: `cd /opt/couple_diary && sudo -u couple .venv/bin/alembic current`

### DB connection failing
1. Is MariaDB running? `systemctl status mariadb`
2. Is it bound to 127.0.0.1? `ss -tlnp | grep 3306`
3. Test user works? `mysql -ucouple -p... -h127.0.0.1`

### Disk full
1. `df -h /data /var/log`
2. Old backups: `ls -lah /data/backups/db/` — auto-trim is 30 days; if more, `find /data/backups/db -mtime +30 -delete`
3. Application logs: rotate via logrotate (configured separately) or `truncate -s 0 /var/log/couple_diary/app.log`

## Backup & restore

### Where backups live
- `/data/backups/db/<YYYYMMDD-HHMMSS>.sql.gz` (daily, 30-day retention)
- `/data/backups/uploads-mirror/` (file tree mirror, daily)
- `/data/backups/pre-deploy/` (snapshots before each deploy)

### Restore the database
```bash
systemctl stop couple-diary
mysql -uroot couple_diary < <(gunzip < /data/backups/db/20260522-030000.sql.gz)
systemctl start couple-diary
curl -fsSk https://127.0.0.1/healthz
```

### Restore one file
```bash
cp /data/backups/uploads-mirror/<user_id>/<YYYY>/<MM>/<sha>/... \
   /data/uploads/<user_id>/<YYYY>/<MM>/<sha>/
chown couple:couple /data/uploads/<...>
```

## Rotating an invite token (forgot password)
```bash
sudo -u couple /opt/couple_diary/.venv/bin/couple-diary init-couple \
    --he "Name" --she "Other" --base-url "https://150.158.3.104"
```
(Requires `users` table empty — for forgot-password mid-life, the SQL recipe is:
delete the affected user, generate one invite token, bind again. M2 will add a CLI subcommand.)

## When you eventually get a domain
1. Point A record to 150.158.3.104
2. Replace `server_name 150.158.3.104;` in nginx config with the domain
3. `dnf install certbot python3-certbot-nginx`
4. `certbot --nginx -d your.domain`
5. Edit `deploy/nginx-couple-diary.conf` — uncomment HSTS header
6. `nginx -t && systemctl reload nginx`
```

- [ ] **Step 2: Commit**

```bash
git add docs/runbook.md
git commit -m "docs: production runbook for service/DB/backup/restore/domain"
```

---

### Task 58: Final on-server smoke test

(Manual; no test code.)

- [ ] **Step 1: Push current branch to a git remote you control**

If the workspace is not yet pushed:
```bash
gh repo create couple-diary --private --source=. --remote=origin --push
# OR manually create the repo and:
git remote add origin <your-repo-url>
git push -u origin master
```

- [ ] **Step 2: Clone on server**

```bash
ssh -i .../tencent_cloud root@150.158.3.104
cd /opt
git clone <your-repo-url> couple_diary
cd couple_diary
```

- [ ] **Step 3: Run bootstrap**

```bash
bash scripts/bootstrap.sh
# Follow prompts: DB password, HE name, SHE name
# At the end, copy the two invite URLs
```

- [ ] **Step 4: Browser smoke test**

From your laptop browser:
1. Open `https://150.158.3.104/bind?token=<HE-TOKEN>` → accept cert warning → set password `<your-password>`
2. After redirect, login with `<your-username>` + that password → land on `/`
3. Click "记录" → toggle several tags across mood / symptoms / sex → confirm pills change colour and persist on refresh
4. Visit `/cycle/log` → log a period start for today → visit `/calendar` → see today highlighted red
5. Visit `/bbt/log` → log 36.5°C → confirm appears in list
6. Open the SHE invite URL in an incognito window on the same or partner's phone → bind → login → see Alice's view, including Alice's tags on her own / page
7. As Alice, visit `/me/settings` → change `diary` from private to shared → save → confirm setting persists
8. Logout / login as Bob → confirm `Alice 的今天` card shows her shared tags (cycle, daily_log) but not her diary content (since diary endpoints are M2 — should be 404 for now)

- [ ] **Step 5: Verify scheduler is running**

```bash
ssh -i .../tencent_cloud root@150.158.3.104 \
    "journalctl -u couple-diary | grep scheduler"
```
Expected: `scheduler started` line with backup_db/backup_files_mirror/cleanup_orphan_media jobs.

- [ ] **Step 6: Manually trigger one backup to verify mysqldump works**

```bash
ssh ... root@150.158.3.104 \
    "sudo -u couple /opt/couple_diary/.venv/bin/python -c 'from app.tasks.backup import backup_database; print(backup_database())'"
```
Expected: prints a path under `/data/backups/db/`, file exists and is non-empty.

- [ ] **Step 7: Tag the release**

```bash
git tag -a m1-shipped -m "M1 MVP shipped to production"
git push --tags
```

- [ ] **Step 8: Final commit if any fixes**

```bash
git commit -am "fix(deploy): any final tweaks from on-server smoke (if any)"
```

---

**End of Phase J. End of M1.**

The full M1 system is now in production at `https://150.158.3.104/`:
- Both partners can log in via invite-bound accounts
- Each can record period dates, BBT, and Flo-style daily tags
- The Today page shows cycle day, phase, ovulation prediction (Calendar + BBT + LH fused), today's own tags, and partner's shared tags
- The Calendar page shows past periods and predicted next period + ovulation day
- Each can upload images (M1 image-only; PDF in M2)
- Each can change visibility per data type in /me/settings
- Daily DB + file backup runs at 03:00 / 03:15
- Orphan media cleanup runs at 03:30
- The deploy script auto-rolls back if healthz fails

**Next:** M2 plan (diary, trip, PDF upload, web push, full polled partner card) and M3 plan (Apple Health import, full predictor with RHR/HRV/Mucus, charts) — each written separately after M1 lands.
