from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.auth.models import InviteToken, User


def _make_user(db, name="alice", role="she"):
    u = User(username=name, display_name=name.title(), role=role)
    db.add(u)
    db.flush()
    return u


def test_create_invite_token(db):
    u = _make_user(db)
    future = datetime.now(timezone.utc) + timedelta(days=7)
    token = InviteToken(token="abc" * 12, user_id=u.id, expires_at=future)
    db.add(token)
    db.flush()
    assert token.id is not None
    assert token.used_at is None
    assert token.created_at is not None


def test_token_value_unique(db):
    u = _make_user(db, name="bob", role="he")
    future = datetime.now(timezone.utc) + timedelta(days=7)
    db.add(InviteToken(token="dup-token-aaaa", user_id=u.id, expires_at=future))
    db.flush()
    db.add(InviteToken(token="dup-token-aaaa", user_id=u.id, expires_at=future))
    with pytest.raises(IntegrityError):
        db.flush()
