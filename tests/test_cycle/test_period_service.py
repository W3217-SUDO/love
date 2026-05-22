from datetime import date

import pytest

from app.modules.auth.models import User
from app.modules.cycle.models import Period
from app.modules.cycle.service import (
    PeriodNotFound,
    PeriodOverlapError,
    get_latest_period,
    list_periods,
    log_period_end,
    log_period_start,
)


def _user(db, name="alice"):
    u = User(username=name, display_name=name.title(), role="she")
    db.add(u)
    db.flush()
    return u


def test_log_period_start_creates_row(db):
    u = _user(db)
    p = log_period_start(db, user_id=u.id, start_date=date(2026, 5, 1))
    db.flush()
    assert p.id is not None
    assert p.start_date == date(2026, 5, 1)
    assert p.end_date is None


def test_log_period_start_is_idempotent(db):
    u = _user(db)
    p1 = log_period_start(db, user_id=u.id, start_date=date(2026, 5, 1))
    db.flush()
    p2 = log_period_start(db, user_id=u.id, start_date=date(2026, 5, 1))
    db.flush()
    assert p1.id == p2.id


def test_log_period_start_rejects_overlap_with_open_period(db):
    u = _user(db)
    log_period_start(db, user_id=u.id, start_date=date(2026, 5, 1))
    db.flush()
    # Within 30 days of an open period
    with pytest.raises(PeriodOverlapError):
        log_period_start(db, user_id=u.id, start_date=date(2026, 5, 15))


def test_log_period_start_rejects_inside_closed_period(db):
    u = _user(db)
    log_period_start(db, user_id=u.id, start_date=date(2026, 5, 1))
    db.flush()
    log_period_end(db, user_id=u.id, start_date=date(2026, 5, 1), end_date=date(2026, 5, 5))
    db.flush()
    # 2026-05-03 falls inside the existing 05-01..05-05 period
    with pytest.raises(PeriodOverlapError):
        log_period_start(db, user_id=u.id, start_date=date(2026, 5, 3))


def test_log_period_start_allows_distant_subsequent(db):
    u = _user(db)
    log_period_start(db, user_id=u.id, start_date=date(2026, 4, 1))
    db.flush()
    log_period_end(db, user_id=u.id, start_date=date(2026, 4, 1), end_date=date(2026, 4, 5))
    db.flush()
    # 30 days later is fine
    p2 = log_period_start(db, user_id=u.id, start_date=date(2026, 5, 1))
    db.flush()
    assert p2.id is not None


def test_log_period_end_sets_end_date(db):
    u = _user(db)
    log_period_start(db, user_id=u.id, start_date=date(2026, 5, 1))
    db.flush()
    p = log_period_end(db, user_id=u.id, start_date=date(2026, 5, 1), end_date=date(2026, 5, 5))
    db.flush()
    assert p.end_date == date(2026, 5, 5)


def test_log_period_end_unknown_start_raises(db):
    u = _user(db)
    with pytest.raises(PeriodNotFound):
        log_period_end(db, user_id=u.id, start_date=date(2026, 5, 1), end_date=date(2026, 5, 5))


def test_log_period_end_before_start_raises(db):
    u = _user(db)
    log_period_start(db, user_id=u.id, start_date=date(2026, 5, 5))
    db.flush()
    with pytest.raises(ValueError):
        log_period_end(db, user_id=u.id, start_date=date(2026, 5, 5), end_date=date(2026, 5, 1))


def test_list_periods_desc(db):
    u = _user(db)
    for d in [date(2026, 5, 1), date(2026, 4, 1), date(2026, 3, 1), date(2026, 2, 1)]:
        log_period_start(db, user_id=u.id, start_date=d)
        db.flush()
        log_period_end(db, user_id=u.id, start_date=d, end_date=d.replace(day=5))
        db.flush()
    rows = list_periods(db, user_id=u.id)
    assert [r.start_date for r in rows] == [
        date(2026, 5, 1), date(2026, 4, 1), date(2026, 3, 1), date(2026, 2, 1),
    ]


def test_get_latest_period(db):
    u = _user(db)
    assert get_latest_period(db, user_id=u.id) is None
    log_period_start(db, user_id=u.id, start_date=date(2026, 3, 1))
    db.flush()
    log_period_end(db, user_id=u.id, start_date=date(2026, 3, 1), end_date=date(2026, 3, 5))
    db.flush()
    log_period_start(db, user_id=u.id, start_date=date(2026, 5, 1))
    db.flush()
    p = get_latest_period(db, user_id=u.id)
    assert p.start_date == date(2026, 5, 1)
