from sqlalchemy import text

from app.db import SessionLocal, engine


def test_engine_connects_and_returns_one():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1


def test_session_factory_yields_session():
    with SessionLocal() as session:
        result = session.execute(text("SELECT 2")).scalar()
        assert result == 2
