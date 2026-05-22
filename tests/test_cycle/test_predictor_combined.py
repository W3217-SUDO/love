from datetime import date, timedelta
from decimal import Decimal

from app.modules.auth.models import User
from app.modules.cycle.predictor.combined import CombinedPredictor
from app.modules.cycle.service import log_bbt, log_period_end, log_period_start


def _user(db, name="alice"):
    u = User(username=name, display_name=name.title(), role="she")
    db.add(u)
    db.flush()
    return u


def _seed_cycles(db, user_id, starts, length=5):
    for s in starts:
        log_period_start(db, user_id=user_id, start_date=s)
        db.flush()
        log_period_end(db, user_id=user_id, start_date=s, end_date=s + timedelta(days=length - 1))
        db.flush()


def test_combined_unknown_with_no_data(db):
    u = _user(db)
    pred = CombinedPredictor().predict(db, user_id=u.id, target_date=date(2026, 5, 22))
    assert pred.phase == "unknown"
    assert pred.confidence_level == "low"


def test_combined_uses_calendar_when_only_calendar(db):
    u = _user(db)
    _seed_cycles(db, u.id, [date(2026, 4, 1), date(2026, 4, 29)], length=5)
    pred = CombinedPredictor().predict(db, user_id=u.id, target_date=date(2026, 5, 10))
    assert pred.next_period == date(2026, 5, 27)
    assert pred.ovulation == date(2026, 5, 13)
    assert pred.phase == "fertile"
    assert any(e.source == "calendar" for e in pred.evidence)


def test_combined_bbt_overrides_ovulation_when_active(db):
    """When BBT confirms ovulation, use that date even if calendar disagrees."""
    u = _user(db)
    # Calendar would predict ovulation around mid-cycle of a future cycle.
    _seed_cycles(db, u.id, [date(2026, 4, 1), date(2026, 4, 29)], length=5)
    # BBT confirms ovulation around May 6
    temps = ["36.40", "36.35", "36.40", "36.30", "36.35", "36.40", "36.65", "36.60", "36.70"]
    for i, t in enumerate(temps):
        log_bbt(db, user_id=u.id, date=date(2026, 5, 1) + timedelta(days=i), temp_c=Decimal(t))
        db.flush()
    pred = CombinedPredictor().predict(db, user_id=u.id, target_date=date(2026, 5, 11))
    # BBT ovulation = May 6 (T1 - 1)
    assert pred.ovulation == date(2026, 5, 6)
    assert pred.confidence_level == "high"
    bbt_evidence = [e for e in pred.evidence if e.source == "bbt"]
    assert bbt_evidence and bbt_evidence[0].active is True


def test_combined_evidence_includes_all_signals(db):
    u = _user(db)
    _seed_cycles(db, u.id, [date(2026, 4, 1), date(2026, 4, 29)])
    pred = CombinedPredictor().predict(db, user_id=u.id, target_date=date(2026, 5, 10))
    sources = {e.source for e in pred.evidence}
    assert "calendar" in sources
    assert "bbt" in sources  # included even when inactive
