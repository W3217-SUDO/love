from datetime import datetime, timedelta, timezone

from app.modules.auth.models import AuthSession, User


def _user(db):
    u = User(username="alice", display_name="Alice", role="she")
    db.add(u)
    db.flush()
    return u


def test_create_session(db):
    u = _user(db)
    future = datetime.now(timezone.utc) + timedelta(days=30)
    s = AuthSession(
        token="x" * 48, user_id=u.id, expires_at=future,
        ip="127.0.0.1", user_agent="pytest",
    )
    db.add(s)
    db.flush()
    assert s.id is not None
    assert s.created_at is not None
    assert s.last_seen_at is not None


def test_session_token_unique(db):
    u = _user(db)
    future = datetime.now(timezone.utc) + timedelta(days=30)
    db.add(AuthSession(token="dup-token", user_id=u.id, expires_at=future))
    db.flush()
    import pytest
    from sqlalchemy.exc import IntegrityError
    db.add(AuthSession(token="dup-token", user_id=u.id, expires_at=future))
    with pytest.raises(IntegrityError):
        db.flush()
