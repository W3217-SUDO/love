from datetime import date

from app.modules.auth.models import User
from app.modules.cycle.predictor.lh import LHSignal
from app.modules.daily_log.service import toggle_tag


def _user(db, name="alice"):
    u = User(username=name, display_name=name.title(), role="she")
    db.add(u)
    db.flush()
    return u


def test_lh_inactive_with_no_tags(db):
    u = _user(db)
    r = LHSignal().evaluate(db, user_id=u.id, target_date=date(2026, 5, 22))
    assert r.active is False
    assert r.source == "lh"


def test_lh_active_on_positive_test_day(db):
    u = _user(db)
    toggle_tag(db, user_id=u.id, date=date(2026, 5, 14), tag_key="ovu_positive")
    db.flush()
    # Target = same day as LH+
    r = LHSignal().evaluate(db, user_id=u.id, target_date=date(2026, 5, 14))
    assert r.active is True
    # Ovulation expected the day after LH+
    assert r.predicted_ovulation == date(2026, 5, 15)
    assert r.confidence >= 0.9


def test_lh_active_day_after(db):
    u = _user(db)
    toggle_tag(db, user_id=u.id, date=date(2026, 5, 14), tag_key="ovu_positive")
    db.flush()
    r = LHSignal().evaluate(db, user_id=u.id, target_date=date(2026, 5, 15))
    assert r.active is True
    assert r.phase in ("ovulation", "fertile")


def test_lh_inactive_too_far_after(db):
    u = _user(db)
    toggle_tag(db, user_id=u.id, date=date(2026, 5, 14), tag_key="ovu_positive")
    db.flush()
    r = LHSignal().evaluate(db, user_id=u.id, target_date=date(2026, 5, 25))
    assert r.active is False


def test_lh_ignores_negative_tests(db):
    u = _user(db)
    toggle_tag(db, user_id=u.id, date=date(2026, 5, 14), tag_key="ovu_negative")
    db.flush()
    r = LHSignal().evaluate(db, user_id=u.id, target_date=date(2026, 5, 14))
    assert r.active is False
