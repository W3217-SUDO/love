from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.auth.models import User
from app.modules.cycle.models import Period


def _user(db, name="alice"):
    u = User(username=name, display_name=name.title(), role="she")
    db.add(u)
    db.flush()
    return u


def test_create_period(db):
    u = _user(db)
    p = Period(user_id=u.id, start_date=date(2026, 5, 1))
    db.add(p)
    db.flush()
    assert p.id is not None
    assert p.end_date is None
    assert p.created_at is not None


def test_period_end_date(db):
    u = _user(db)
    p = Period(user_id=u.id, start_date=date(2026, 5, 1), end_date=date(2026, 5, 5))
    db.add(p)
    db.flush()
    assert p.end_date == date(2026, 5, 5)


def test_user_id_start_date_unique(db):
    u = _user(db)
    db.add(Period(user_id=u.id, start_date=date(2026, 5, 1)))
    db.flush()
    db.add(Period(user_id=u.id, start_date=date(2026, 5, 1)))
    with pytest.raises(IntegrityError):
        db.flush()
