from datetime import date, timedelta
from decimal import Decimal

from app.modules.auth.models import User
from app.modules.cycle.predictor.bbt import BBTSignal
from app.modules.cycle.service import log_bbt


def _user(db, name="alice"):
    u = User(username=name, display_name=name.title(), role="she")
    db.add(u)
    db.flush()
    return u


def _seed_temps(db, user_id, base_date, temps):
    """temps: list of decimal strings. Sequential days starting at base_date."""
    for i, t in enumerate(temps):
        log_bbt(db, user_id=user_id, date=base_date + timedelta(days=i), temp_c=Decimal(t))
        db.flush()


def test_bbt_inactive_with_no_readings(db):
    u = _user(db)
    sig = BBTSignal()
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 5, 22))
    assert r.active is False
    assert r.source == "bbt"


def test_bbt_inactive_with_few_readings(db):
    u = _user(db)
    _seed_temps(db, u.id, date(2026, 5, 1), ["36.5", "36.5", "36.4"])
    sig = BBTSignal()
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 5, 22))
    assert r.active is False


def test_bbt_detects_three_step_rise(db):
    """Classic biphasic curve: low followed by sustained high."""
    u = _user(db)
    # Days 1..6 (follicular): all <= 36.40
    # Day 7 (T1): 36.65 (rise of 0.25C above max coverline of 36.40)
    # Day 8 (T2): 36.60 (still above coverline)
    # Day 9 (T3): 36.70 (above coverline + 0.2)
    temps = ["36.40", "36.35", "36.40", "36.30", "36.35", "36.40", "36.65", "36.60", "36.70"]
    _seed_temps(db, u.id, date(2026, 5, 1), temps)
    sig = BBTSignal()
    # Target a few days after the rise -- within the post-ovulation window
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 5, 11))
    assert r.active is True
    # T1 is day 7 (May 7); ovulation = T1 - 1 = May 6
    assert r.predicted_ovulation == date(2026, 5, 6)
    assert r.phase == "luteal"
    assert r.confidence >= 0.8


def test_bbt_inactive_when_no_clear_rise(db):
    """Flat temperatures -- no triplet should be detected."""
    u = _user(db)
    flat = ["36.50"] * 12
    _seed_temps(db, u.id, date(2026, 5, 1), flat)
    sig = BBTSignal()
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 5, 12))
    assert r.active is False


def test_bbt_inactive_when_target_too_far_after_ovulation(db):
    """If ovulation was detected but target is way later, signal goes quiet."""
    u = _user(db)
    temps = ["36.40", "36.35", "36.40", "36.30", "36.35", "36.40", "36.65", "36.60", "36.70"]
    _seed_temps(db, u.id, date(2026, 5, 1), temps)
    sig = BBTSignal()
    # Target 14 days after ovulation -- outside 5-day post-ovulation window
    r = sig.evaluate(db, user_id=u.id, target_date=date(2026, 5, 25))
    assert r.active is False
