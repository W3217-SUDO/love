from datetime import date

import pytest

from app.modules.auth.models import User
from app.modules.daily_log.models import DailyEntry, DailyTag
from app.modules.daily_log.service import (
    UnknownTagError,
    get_or_create_entry,
    list_tags_for_day,
    set_notes,
    toggle_tag,
)


def _user(db, name="alice"):
    u = User(username=name, display_name=name.title(), role="she")
    db.add(u)
    db.flush()
    return u


def test_get_or_create_creates_then_idempotent(db):
    u = _user(db)
    e1 = get_or_create_entry(db, user_id=u.id, date=date(2026, 5, 22))
    db.flush()
    e2 = get_or_create_entry(db, user_id=u.id, date=date(2026, 5, 22))
    db.flush()
    assert e1.id == e2.id


def test_toggle_tag_activates_then_deactivates(db):
    u = _user(db)
    _, active = toggle_tag(db, user_id=u.id, date=date(2026, 5, 22), tag_key="mood_happy")
    db.flush()
    assert active is True
    rows = db.query(DailyTag).all()
    assert len(rows) == 1
    _, active2 = toggle_tag(db, user_id=u.id, date=date(2026, 5, 22), tag_key="mood_happy")
    db.flush()
    assert active2 is False
    assert db.query(DailyTag).count() == 0


def test_toggle_tag_unknown_raises(db):
    u = _user(db)
    with pytest.raises(UnknownTagError):
        toggle_tag(db, user_id=u.id, date=date(2026, 5, 22), tag_key="not_in_catalog")


def test_toggle_tag_stores_value_if_given(db):
    u = _user(db)
    _, _ = toggle_tag(
        db, user_id=u.id, date=date(2026, 5, 22),
        tag_key="ovu_positive", value="dark line",
    )
    db.flush()
    tag = db.query(DailyTag).one()
    assert tag.value == "dark line"


def test_list_tags_for_day_returns_empty_if_no_entry(db):
    u = _user(db)
    rows = list_tags_for_day(db, user_id=u.id, date=date(2026, 5, 22))
    assert rows == []


def test_list_tags_for_day_returns_active_tags(db):
    u = _user(db)
    toggle_tag(db, user_id=u.id, date=date(2026, 5, 22), tag_key="mood_happy")
    toggle_tag(db, user_id=u.id, date=date(2026, 5, 22), tag_key="sym_cramps")
    db.flush()
    rows = list_tags_for_day(db, user_id=u.id, date=date(2026, 5, 22))
    assert len(rows) == 2
    keys = {r.tag_key for r in rows}
    assert keys == {"mood_happy", "sym_cramps"}


def test_set_notes(db):
    u = _user(db)
    e = set_notes(db, user_id=u.id, date=date(2026, 5, 22), notes="hello")
    db.flush()
    assert e.notes == "hello"
    e2 = set_notes(db, user_id=u.id, date=date(2026, 5, 22), notes="updated")
    db.flush()
    assert e2.id == e.id
    assert e2.notes == "updated"
