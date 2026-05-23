from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete

from app.modules.auth.models import AuthSession, Couple, InviteToken, User
from app.modules.auth.sessions import (
    SessionExpired,
    SessionNotFound,
    create_session,
    lookup_session,
    revoke_session,
    touch_session,
)


def _wipe(db):
    db.execute(delete(AuthSession))
    db.execute(delete(InviteToken))
    db.execute(delete(Couple))
    db.execute(delete(User))
    db.flush()


def _user(db, name="alice", role="she"):
    _wipe(db)
    u = User(username=name, display_name=name.title(), role=role)
    db.add(u)
    db.flush()
    return u


def test_create_session_returns_token(db):
    u = _user(db)
    token = create_session(db, user_id=u.id, ip="1.2.3.4", user_agent="UA")
    db.flush()
    assert isinstance(token, str) and len(token) >= 32
    row = db.query(AuthSession).filter_by(token=token).one()
    assert row.user_id == u.id
    assert row.ip == "1.2.3.4"


def test_lookup_session_returns_user(db):
    u = _user(db)
    token = create_session(db, user_id=u.id, ip=None, user_agent=None)
    db.flush()
    found_user = lookup_session(db, token=token)
    assert found_user.id == u.id


def test_lookup_session_unknown_raises(db):
    _wipe(db)
    with pytest.raises(SessionNotFound):
        lookup_session(db, token="nonexistent")


def test_lookup_session_expired_raises(db):
    u = _user(db)
    token = create_session(db, user_id=u.id, ip=None, user_agent=None)
    db.flush()
    row = db.query(AuthSession).filter_by(token=token).one()
    row.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)
    db.flush()
    with pytest.raises(SessionExpired):
        lookup_session(db, token=token)


def test_revoke_session_deletes_row(db):
    u = _user(db)
    token = create_session(db, user_id=u.id, ip=None, user_agent=None)
    db.flush()
    revoke_session(db, token=token)
    db.flush()
    assert db.query(AuthSession).filter_by(token=token).count() == 0


def test_touch_session_updates_last_seen(db):
    u = _user(db)
    token = create_session(db, user_id=u.id, ip=None, user_agent=None)
    db.flush()
    row = db.query(AuthSession).filter_by(token=token).one()
    original = row.last_seen_at
    # Force a different "now" by manipulating
    import time
    time.sleep(1.1)
    touch_session(db, token=token)
    db.flush()
    db.refresh(row)
    assert row.last_seen_at > original
