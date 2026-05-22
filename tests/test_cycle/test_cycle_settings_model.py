import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.auth.models import User
from app.modules.cycle.models import CycleSettings


def _user(db, name="alice"):
    u = User(username=name, display_name=name.title(), role="she")
    db.add(u)
    db.flush()
    return u


def test_create_cycle_settings_with_defaults(db):
    u = _user(db)
    s = CycleSettings(user_id=u.id)
    db.add(s)
    db.flush()
    assert s.avg_cycle_length == 28
    assert s.avg_period_length == 5
    assert s.mode == "auto"


def test_only_one_settings_per_user(db):
    u = _user(db)
    db.add(CycleSettings(user_id=u.id))
    db.flush()
    db.add(CycleSettings(user_id=u.id))
    with pytest.raises(IntegrityError):
        db.flush()
