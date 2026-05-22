from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.auth.models import User
from app.modules.daily_log.models import DailyEntry, DailyTag


def _user(db, name="alice"):
    u = User(username=name, display_name=name.title(), role="she")
    db.add(u)
    db.flush()
    return u


def test_create_daily_entry(db):
    u = _user(db)
    e = DailyEntry(user_id=u.id, date=date(2026, 5, 22), notes="good day")
    db.add(e)
    db.flush()
    assert e.id is not None
    assert e.created_at is not None


def test_one_entry_per_user_per_day(db):
    u = _user(db)
    db.add(DailyEntry(user_id=u.id, date=date(2026, 5, 22)))
    db.flush()
    db.add(DailyEntry(user_id=u.id, date=date(2026, 5, 22)))
    with pytest.raises(IntegrityError):
        db.flush()


def test_create_daily_tag(db):
    u = _user(db)
    e = DailyEntry(user_id=u.id, date=date(2026, 5, 22))
    db.add(e)
    db.flush()
    t = DailyTag(entry_id=e.id, category="mood", tag_key="mood_happy")
    db.add(t)
    db.flush()
    assert t.id is not None
    assert t.value is None


def test_tag_unique_per_entry(db):
    u = _user(db)
    e = DailyEntry(user_id=u.id, date=date(2026, 5, 22))
    db.add(e)
    db.flush()
    db.add(DailyTag(entry_id=e.id, category="mood", tag_key="mood_happy"))
    db.flush()
    db.add(DailyTag(entry_id=e.id, category="mood", tag_key="mood_happy"))
    with pytest.raises(IntegrityError):
        db.flush()


def test_tag_with_value(db):
    u = _user(db)
    e = DailyEntry(user_id=u.id, date=date(2026, 5, 22))
    db.add(e)
    db.flush()
    t = DailyTag(
        entry_id=e.id, category="ovulation", tag_key="ovu_positive",
        value="dark line",
    )
    db.add(t)
    db.flush()
    assert t.value == "dark line"
