from copy import deepcopy
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.settings.models import UserSettings


class Visibility(StrEnum):
    PRIVATE = "private"
    SHARED = "shared"


DATA_TYPES = ("diary", "daily_log", "cycle", "bbt", "trip", "report", "health")

DEFAULT_VISIBILITY: dict[str, str] = {
    "diary": Visibility.PRIVATE.value,
    "daily_log": Visibility.SHARED.value,
    "cycle": Visibility.SHARED.value,
    "bbt": Visibility.PRIVATE.value,
    "trip": Visibility.SHARED.value,
    "report": Visibility.PRIVATE.value,
    "health": Visibility.PRIVATE.value,
}

DEFAULT_NOTIFICATION_PREFS: dict[str, object] = {
    "daily_record": {"enabled": False, "time": "21:00"},
    "period": {"enabled": False, "days_before": 2},
    "fertile_window": {"enabled": False, "days_before": 1},
    "bbt": {"enabled": False, "time": "07:30"},
    "partner_activity": {"enabled": False},
}


def _default_notification_prefs() -> dict[str, object]:
    return deepcopy(DEFAULT_NOTIFICATION_PREFS)


def ensure_settings(db: Session, user_id: int) -> UserSettings:
    settings = db.scalar(select(UserSettings).where(UserSettings.user_id == user_id))
    if settings is not None:
        changed = False
        visibility = dict(settings.visibility or {})
        for key, value in DEFAULT_VISIBILITY.items():
            if key not in visibility:
                visibility[key] = value
                changed = True

        notification_prefs = dict(settings.notification_prefs or {})
        for key, value in DEFAULT_NOTIFICATION_PREFS.items():
            if key not in notification_prefs:
                notification_prefs[key] = deepcopy(value)
                changed = True

        if changed:
            settings.visibility = visibility
            settings.notification_prefs = notification_prefs
            db.commit()
            db.refresh(settings)
        return settings

    settings = UserSettings(
        user_id=user_id,
        theme="system",
        visibility=dict(DEFAULT_VISIBILITY),
        notification_prefs=_default_notification_prefs(),
    )
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def set_visibility(
    db: Session,
    settings: UserSettings,
    data_type: str,
    visibility: Visibility,
) -> UserSettings:
    if data_type not in DATA_TYPES:
        raise ValueError(f"unknown data type: {data_type}")

    values = dict(settings.visibility or {})
    values[data_type] = visibility.value
    settings.visibility = values
    db.commit()
    db.refresh(settings)
    return settings


def can_partner_view(settings: UserSettings, data_type: str) -> bool:
    visibility = dict(settings.visibility or {})
    return visibility.get(data_type, DEFAULT_VISIBILITY.get(data_type)) == Visibility.SHARED.value
