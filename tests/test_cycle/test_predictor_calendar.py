from datetime import date, timedelta

from app.modules.auth.models import User
from app.modules.cycle.predictor.calendar import CalendarSignal
from app.modules.cycle.service import log_period_end, log_period_start


def _user(db, name="alice"):
    u = User(username=name, display_name=name.title(), role="she")
    db.add(u)
    db.flush()
    return u


def _seed_cycles(db, user_id, starts, length=5):
    """starts: list of date for each period start. Each is closed after `length` days."""
    for s in starts:
        log_period_start(db, user_id=user_id, start_date=s)
        db.flush()
        log_period_end(db, user_id=user_id, start_date=s, end_date=s + timedelta(days=length - 1))
        db.flush()


def test_calendar_inactive_with_no_periods(db):
    u = _user(db)
    sig = CalendarSignal()
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 5, 22))
    assert r.active is False
    assert r.source == "calendar"


def test_calendar_uses_default_cycle_with_one_period(db):
    u = _user(db)
    _seed_cycles(db, u.id, [date(2026, 4, 1)])
    sig = CalendarSignal()
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 5, 22))
    assert r.active is True
    assert r.confidence == 0.20
    assert r.predicted_next_period == date(2026, 5, 27)
    assert "avg_cycle=28d" in r.evidence


def test_calendar_predicts_with_two_periods(db):
    u = _user(db)
    _seed_cycles(db, u.id, [date(2026, 4, 1), date(2026, 4, 29)])  # 28-day gap
    sig = CalendarSignal()
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 5, 15))
    assert r.active is True
    assert r.predicted_next_period == date(2026, 4, 29) + timedelta(days=28)
    assert r.predicted_ovulation == r.predicted_next_period - timedelta(days=14)
    assert r.fertile_window[0] == r.predicted_ovulation - timedelta(days=5)
    assert r.fertile_window[1] == r.predicted_ovulation + timedelta(days=1)


def test_calendar_uses_mean_cycle_length(db):
    u = _user(db)
    # Gaps: 30, 28, 28 -> mean = 28.67 -> rounded to 29
    starts = [date(2026, 1, 1), date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 28)]
    _seed_cycles(db, u.id, starts)
    sig = CalendarSignal()
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 4, 15))
    # Predicted next period = last start + round(mean of [30, 28, 28]) = Mar 28 + 29 = Apr 26
    assert r.predicted_next_period == date(2026, 3, 28) + timedelta(days=29)


def test_calendar_phase_menstrual(db):
    u = _user(db)
    _seed_cycles(db, u.id, [date(2026, 4, 1), date(2026, 4, 29)], length=5)
    sig = CalendarSignal()
    # Target falls inside the latest period (Apr 29 - May 3)
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 4, 30))
    assert r.phase == "menstrual"


def test_calendar_phase_follicular(db):
    u = _user(db)
    _seed_cycles(db, u.id, [date(2026, 4, 1), date(2026, 4, 29)], length=5)
    sig = CalendarSignal()
    # Target after period end, before fertile window
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 5, 7))
    assert r.phase == "follicular"


def test_calendar_phase_fertile(db):
    u = _user(db)
    _seed_cycles(db, u.id, [date(2026, 4, 1), date(2026, 4, 29)], length=5)
    sig = CalendarSignal()
    # Ovulation = May 27 - 14 = May 13. Fertile window (May 8, May 14).
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 5, 10))
    assert r.phase == "fertile"


def test_calendar_phase_luteal(db):
    u = _user(db)
    _seed_cycles(db, u.id, [date(2026, 4, 1), date(2026, 4, 29)], length=5)
    sig = CalendarSignal()
    # Target after fertile window (after May 14), before next period (May 27)
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 5, 20))
    assert r.phase == "luteal"


def test_calendar_confidence_scales_with_history(db):
    u = _user(db)
    _seed_cycles(db, u.id, [date(2026, 1, 1) + timedelta(days=28 * i) for i in range(7)])
    sig = CalendarSignal()
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 6, 1))
    assert r.confidence >= 0.6  # plenty of history
