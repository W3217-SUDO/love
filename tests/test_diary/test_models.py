from datetime import date

import pytest
from sqlalchemy.exc import DatabaseError, IntegrityError

from app.modules.auth.models import User
from app.modules.diary.models import DiaryEntry


def _user(db, name="alice"):
    u = User(username=name, display_name=name.title(), role="she")
    db.add(u)
    db.flush()
    return u


def test_create_diary_entry(db):
    u = _user(db)
    e = DiaryEntry(author_id=u.id, date=date(2026, 5, 22), body="Hello world")
    db.add(e)
    db.flush()
    assert e.id is not None
    assert e.visibility == "shared"
    assert e.created_at is not None


def test_diary_visibility_check_constraint(db):
    u = _user(db)
    e = DiaryEntry(author_id=u.id, date=date(2026, 5, 22), body="x", visibility="bogus")
    db.add(e)
    with pytest.raises((IntegrityError, DatabaseError)):
        db.flush()


def test_diary_body_required(db):
    u = _user(db)
    e = DiaryEntry(author_id=u.id, date=date(2026, 5, 22), body=None)
    db.add(e)
    with pytest.raises(IntegrityError):
        db.flush()
