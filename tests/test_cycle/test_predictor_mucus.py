from datetime import date

from app.modules.auth.models import User
from app.modules.cycle.predictor.mucus import MucusSignal
from app.modules.daily_log.service import toggle_tag


def _user(db, name="alice"):
    u = User(username=name, display_name=name.title(), role="she")
    db.add(u)
    db.flush()
    return u


def test_mucus_signal_marks_egg_white_as_near_ovulation(db):
    u = _user(db)
    target = date(2026, 5, 24)
    toggle_tag(db, user_id=u.id, date=target, tag_key="disch_egg_white")
    db.flush()

    result = MucusSignal().evaluate(db, user_id=u.id, target_date=target)

    assert result is not None
    assert result.active is True
    assert "接近排卵" in result.evidence
    assert result.phase == "fertile"
    assert result.confidence >= 0.55
