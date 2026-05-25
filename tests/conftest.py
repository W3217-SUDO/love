import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
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


def _drop_schema() -> None:
    with test_engine.begin() as connection:
        preparer = connection.dialect.identifier_preparer
        is_mysql = connection.dialect.name in {"mysql", "mariadb"}
        if is_mysql:
            connection.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        table_names = set(inspect(connection).get_table_names()) | set(Base.metadata.tables)
        for table_name in sorted(table_names, reverse=True):
            quoted_name = preparer.quote(table_name)
            connection.execute(text(f"DROP TABLE IF EXISTS {quoted_name}"))
        if is_mysql:
            connection.execute(text("SET FOREIGN_KEY_CHECKS=1"))


@pytest.fixture(scope="session", autouse=True)
def _create_schema() -> Iterator[None]:
    # Import all models so metadata is populated
    import app.modules  # noqa: F401
    _drop_schema()
    Base.metadata.create_all(bind=test_engine)
    yield
    _drop_schema()


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
