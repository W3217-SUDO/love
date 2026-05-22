from datetime import date, time
from decimal import Decimal

import pytest

from app.modules.auth.models import User
from app.modules.cycle.models import BbtReading
from app.modules.cycle.service import (
    InvalidBbtReading,
    list_bbt,
    log_bbt,
)


def _user(db, name="alice"):
    u = User(username=name, display_name=name.title(), role="she")
    db.add(u)
    db.flush()
    return u


def test_log_bbt_inserts(db):
    u = _user(db)
    r = log_bbt(db, user_id=u.id, date=date(2026, 5, 10), temp_c=Decimal("36.55"))
    db.flush()
    assert r.id is not None
    assert r.temp_c == Decimal("36.55")


def test_log_bbt_updates_existing_for_same_day(db):
    u = _user(db)
    r1 = log_bbt(db, user_id=u.id, date=date(2026, 5, 10), temp_c=Decimal("36.55"))
    db.flush()
    r2 = log_bbt(
        db, user_id=u.id, date=date(2026, 5, 10),
        temp_c=Decimal("36.70"), method="oral",
        measure_time=time(7, 0), notes="updated",
    )
    db.flush()
    assert r1.id == r2.id  # same row updated
    assert r2.temp_c == Decimal("36.70")
    assert r2.method == "oral"


def test_log_bbt_rejects_out_of_range(db):
    u = _user(db)
    with pytest.raises(InvalidBbtReading):
        log_bbt(db, user_id=u.id, date=date(2026, 5, 10), temp_c=Decimal("42.00"))
    with pytest.raises(InvalidBbtReading):
        log_bbt(db, user_id=u.id, date=date(2026, 5, 10), temp_c=Decimal("30.00"))


def test_log_bbt_rejects_invalid_method(db):
    u = _user(db)
    with pytest.raises(InvalidBbtReading):
        log_bbt(
            db, user_id=u.id, date=date(2026, 5, 10),
            temp_c=Decimal("36.50"), method="badmethod",
        )


def test_list_bbt_orders_by_date_asc(db):
    u = _user(db)
    for d, t in [
        (date(2026, 5, 3), "36.51"),
        (date(2026, 5, 1), "36.40"),
        (date(2026, 5, 2), "36.45"),
    ]:
        log_bbt(db, user_id=u.id, date=d, temp_c=Decimal(t))
        db.flush()
    rows = list_bbt(db, user_id=u.id)
    assert [r.date for r in rows] == [date(2026, 5, 1), date(2026, 5, 2), date(2026, 5, 3)]


def test_list_bbt_date_filter(db):
    u = _user(db)
    for d in [date(2026, 5, 1), date(2026, 5, 5), date(2026, 5, 10)]:
        log_bbt(db, user_id=u.id, date=d, temp_c=Decimal("36.50"))
        db.flush()
    rows = list_bbt(db, user_id=u.id, start_date=date(2026, 5, 4), end_date=date(2026, 5, 7))
    assert [r.date for r in rows] == [date(2026, 5, 5)]
