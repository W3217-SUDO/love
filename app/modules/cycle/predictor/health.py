"""Health metric signal.

Resting heart rate and related wearable metrics can add context to cycle
prediction, but are intentionally weak evidence compared with LH/BBT.
"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cycle.predictor.base import SignalResult
from app.modules.health.models import HealthMetric
from app.modules.health.service import MetricType


class HealthMetricSignal:
    source = "health"

    def evaluate(self, db: Session, *, user_id: int, target_date: date) -> SignalResult:
        metric = db.execute(
            select(HealthMetric)
            .where(
                HealthMetric.user_id == user_id,
                HealthMetric.metric_type == MetricType.RESTING_HEART_RATE,
                HealthMetric.date == target_date,
            )
            .order_by(HealthMetric.updated_at.desc(), HealthMetric.id.desc())
            .limit(1),
        ).scalar_one_or_none()
        if metric is None:
            return SignalResult(
                source=self.source,
                active=False,
                confidence=0.0,
                evidence="no resting heart rate logged today",
            )

        return SignalResult(
            source=self.source,
            active=True,
            confidence=0.30,
            evidence=f"静息心率 {metric.value:g} {metric.unit}",
        )
