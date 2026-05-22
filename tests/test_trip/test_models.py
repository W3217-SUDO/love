from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.auth.models import User
from app.modules.trip.models import Trip


def _user(db, name="alice"):
    u = User(username=name, display_name=name.title(), role="she")
    db.add(u)
    db.flush()
    return u


def test_create_trip(db):
    u = _user(db)
    t = Trip(title="京都", start_date=date(2026, 5, 1), created_by_id=u.id)
    db.add(t)
    db.flush()
    assert t.id is not None
    assert t.end_date is None


def test_trip_title_required(db):
    u = _user(db)
    t = Trip(title=None, start_date=date(2026, 5, 1), created_by_id=u.id)
    db.add(t)
    with pytest.raises(IntegrityError):
        db.flush()
