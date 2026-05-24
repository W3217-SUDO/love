from datetime import date
from decimal import Decimal

from app.modules.auth.models import User
from app.modules.health.service import MetricType, list_metrics, upsert_metric


def _user(db, name="alice"):
    u = User(username=name, display_name=name.title(), role="she")
    db.add(u)
    db.flush()
    return u


def test_upsert_metric_creates_and_updates_same_row(db):
    u = _user(db)
    metric_date = date(2026, 5, 24)

    first = upsert_metric(
        db,
        user_id=u.id,
        date=metric_date,
        metric_type=MetricType.RESTING_HEART_RATE,
        value=Decimal("61.5"),
        unit="bpm",
        source="manual",
        meta_json={"device": "watch"},
    )
    second = upsert_metric(
        db,
        user_id=u.id,
        date=metric_date,
        metric_type=MetricType.RESTING_HEART_RATE,
        value=Decimal("63.0"),
        unit="bpm",
        source="manual",
        meta_json={"device": "ring"},
    )

    assert second.id == first.id
    assert second.value == Decimal("63.00")
    assert second.unit == "bpm"
    assert second.meta_json == {"device": "ring"}


def test_list_metrics_filters_by_type(db):
    u = _user(db)
    metric_date = date(2026, 5, 24)
    upsert_metric(
        db,
        user_id=u.id,
        date=metric_date,
        metric_type=MetricType.RESTING_HEART_RATE,
        value=Decimal("61.5"),
        unit="bpm",
    )
    upsert_metric(
        db,
        user_id=u.id,
        date=metric_date,
        metric_type=MetricType.HRV,
        value=Decimal("47"),
        unit="ms",
    )

    rows = list_metrics(db, user_id=u.id, metric_type=MetricType.HRV)

    assert len(rows) == 1
    assert rows[0].metric_type == MetricType.HRV
    assert rows[0].value == Decimal("47.00")
