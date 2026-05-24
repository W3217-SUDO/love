from datetime import date as date_t
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.health.models import HealthMetric


class MetricType(StrEnum):
    RESTING_HEART_RATE = "resting_heart_rate"
    HRV = "hrv"
    SLEEP_DURATION = "sleep_duration"
    SLEEP_QUALITY = "sleep_quality"
    WEIGHT = "weight"


def _find_metric(
    db: Session,
    *,
    user_id: int,
    date: date_t,
    metric_type: str,
    source: str,
) -> HealthMetric | None:
    return db.execute(
        select(HealthMetric).where(
            HealthMetric.user_id == user_id,
            HealthMetric.date == date,
            HealthMetric.metric_type == metric_type,
            HealthMetric.source == source,
        ),
    ).scalar_one_or_none()


def _update_metric(
    metric: HealthMetric,
    *,
    value: Decimal,
    unit: str,
    meta_json: dict | None,
) -> None:
    metric.value = value
    metric.unit = unit
    metric.meta_json = meta_json if meta_json is not None else {}


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

    existing = _find_metric(
        db,
        user_id=user_id,
        date=date,
        metric_type=metric_type_value,
        source=source,
    )

    if existing is not None:
        _update_metric(existing, value=value, unit=unit, meta_json=meta_json)
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

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        metric = _find_metric(
            db,
            user_id=user_id,
            date=date,
            metric_type=metric_type_value,
            source=source,
        )
        if metric is None:
            raise
        _update_metric(metric, value=value, unit=unit, meta_json=meta_json)
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
