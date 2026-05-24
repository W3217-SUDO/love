from datetime import date as date_t
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.health.models import HealthMetric


class MetricType(StrEnum):
    RESTING_HEART_RATE = "resting_heart_rate"
    HRV = "hrv"
    SLEEP_DURATION = "sleep_duration"
    SLEEP_QUALITY = "sleep_quality"
    WEIGHT = "weight"


def upsert_metric(
    db: Session,
    *,
    user_id: int,
    date: date_t,
    metric_type: MetricType | str,
    value: Decimal,
    unit: str,
    source: str = "manual",
    meta_json: dict | None = None,
) -> HealthMetric:
    """Create or update one metric for a user/date/type/source."""
    metric_type_value = str(metric_type)
    if not isinstance(value, Decimal):
        value = Decimal(str(value))

    existing = db.execute(
        select(HealthMetric).where(
            HealthMetric.user_id == user_id,
            HealthMetric.date == date,
            HealthMetric.metric_type == metric_type_value,
            HealthMetric.source == source,
        ),
    ).scalar_one_or_none()

    if existing is not None:
        existing.value = value
        existing.unit = unit
        existing.meta_json = meta_json if meta_json is not None else {}
        metric = existing
    else:
        metric = HealthMetric(
            user_id=user_id,
            date=date,
            metric_type=metric_type_value,
            value=value,
            unit=unit,
            source=source,
            meta_json=meta_json if meta_json is not None else {},
        )
        db.add(metric)

    db.commit()
    db.refresh(metric)
    return metric


def list_metrics(
    db: Session,
    *,
    user_id: int,
    metric_type: MetricType | str | None = None,
    start: date_t | None = None,
    end: date_t | None = None,
) -> list[HealthMetric]:
    """Return metrics ordered by date ascending, then type and source."""
    stmt = select(HealthMetric).where(HealthMetric.user_id == user_id)
    if metric_type is not None:
        stmt = stmt.where(HealthMetric.metric_type == str(metric_type))
    if start is not None:
        stmt = stmt.where(HealthMetric.date >= start)
    if end is not None:
        stmt = stmt.where(HealthMetric.date <= end)
    stmt = stmt.order_by(
        HealthMetric.date.asc(),
        HealthMetric.metric_type.asc(),
        HealthMetric.source.asc(),
    )
    return list(db.execute(stmt).scalars().all())
