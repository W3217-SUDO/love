from datetime import date, time
from decimal import Decimal

import pytest
from sqlalchemy.exc import DatabaseError, IntegrityError

from app.modules.auth.models import User
from app.modules.cycle.models import BbtReading


def _user(db, name="alice"):
    u = User(username=name, display_name=name.title(), role="she")
    db.add(u)
    db.flush()
    return u


def test_create_bbt_reading(db):
    u = _user(db)
    r = BbtReading(
        user_id=u.id, date=date(2026, 5, 10),
        temp_c=Decimal("36.55"), measure_time=time(7, 30), method="oral",
    )
    db.add(r)
    db.flush()
    assert r.id is not None
    assert r.temp_c == Decimal("36.55")


def test_user_date_unique(db):
    u = _user(db)
    db.add(BbtReading(user_id=u.id, date=date(2026, 5, 10), temp_c=Decimal("36.55")))
    db.flush()
    db.add(BbtReading(user_id=u.id, date=date(2026, 5, 10), temp_c=Decimal("36.60")))
    with pytest.raises(IntegrityError):
        db.flush()


def test_temp_out_of_range_rejected(db):
    u = _user(db)
    r = BbtReading(user_id=u.id, date=date(2026, 5, 11), temp_c=Decimal("99.99"))
    db.add(r)
    # MariaDB CHECK constraint may raise OperationalError or IntegrityError
    with pytest.raises((IntegrityError, DatabaseError)):
        db.flush()


def test_invalid_method_rejected(db):
    u = _user(db)
    r = BbtReading(
        user_id=u.id, date=date(2026, 5, 12),
        temp_c=Decimal("36.50"), method="invalid_method",
    )
    db.add(r)
    with pytest.raises((IntegrityError, DatabaseError)):
        db.flush()


def test_method_can_be_null(db):
    u = _user(db)
    r = BbtReading(user_id=u.id, date=date(2026, 5, 13), temp_c=Decimal("36.50"))
    db.add(r)
    db.flush()
    assert r.method is None
