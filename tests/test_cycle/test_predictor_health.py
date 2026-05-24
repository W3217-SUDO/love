from datetime import date
from decimal import Decimal

from app.modules.auth.models import User
from app.modules.cycle.predictor.health import HealthMetricSignal
from app.modules.health.service import MetricType, upsert_metric


def _user(db, name="alice"):
    u = User(username=name, display_name=name.title(), role="she")
    db.add(u)
    db.flush()
    return u


def test_health_metric_signal_adds_low_confidence_rhr_evidence(db):
    u = _user(db)
    target = date(2026, 5, 24)
    upsert_metric(
        db,
        user_id=u.id,
        date=target,
        metric_type=MetricType.RESTING_HEART_RATE,
        value=Decimal("62"),
        unit="bpm",
    )

    result = HealthMetricSignal().evaluate(db, user_id=u.id, target_date=target)

    assert result is not None
    assert result.active is True
    assert "静息心率" in result.evidence
    assert result.confidence <= 0.35


def test_health_metric_signal_uses_most_recently_updated_source(db):
    u = _user(db)
    target = date(2026, 5, 24)
    upsert_metric(
        db,
        user_id=u.id,
        date=target,
        metric_type=MetricType.RESTING_HEART_RATE,
        value=Decimal("62"),
        unit="bpm",
        source="zzz_watch",
    )
    upsert_metric(
        db,
        user_id=u.id,
        date=target,
        metric_type=MetricType.RESTING_HEART_RATE,
        value=Decimal("64"),
        unit="bpm",
        source="aaa_ring",
    )
    upsert_metric(
        db,
        user_id=u.id,
        date=target,
        metric_type=MetricType.RESTING_HEART_RATE,
        value=Decimal("66"),
        unit="bpm",
        source="aaa_ring",
    )

    result = HealthMetricSignal().evaluate(db, user_id=u.id, target_date=target)

    assert "66" in result.evidence
