import pytest

from app.modules.auth.models import User
from app.modules.settings.service import (
    DATA_TYPES,
    Visibility,
    can_partner_view,
    ensure_settings,
    set_visibility,
)


def _user(db, name="alice"):
    user = User(username=name, display_name=name.title(), role="she")
    db.add(user)
    db.flush()
    return user


def test_ensure_settings_creates_defaults(db):
    user = _user(db)

    settings = ensure_settings(db, user.id)

    assert settings.user_id == user.id
    assert settings.theme == "system"
    assert settings.visibility["diary"] == "private"
    assert settings.visibility["cycle"] == "shared"


def test_set_visibility_persists_known_type(db):
    user = _user(db)
    settings = ensure_settings(db, user.id)

    set_visibility(db, settings, "diary", Visibility.SHARED)
    db.commit()

    loaded = ensure_settings(db, user.id)
    assert loaded.visibility["diary"] == "shared"


def test_set_visibility_rejects_unknown_type(db):
    user = _user(db)
    settings = ensure_settings(db, user.id)

    with pytest.raises(ValueError, match="unknown data type"):
        set_visibility(db, settings, "secret", Visibility.SHARED)


def test_can_partner_view_uses_defaults_and_data_types(db):
    user = _user(db)
    settings = ensure_settings(db, user.id)

    assert DATA_TYPES == ("diary", "daily_log", "cycle", "bbt", "trip", "report", "health")
    assert can_partner_view(settings, "diary") is False
    assert can_partner_view(settings, "daily_log") is True
    assert can_partner_view(settings, "cycle") is True
    assert can_partner_view(settings, "bbt") is False
    assert can_partner_view(settings, "trip") is True
    assert can_partner_view(settings, "report") is False
    assert can_partner_view(settings, "health") is False
