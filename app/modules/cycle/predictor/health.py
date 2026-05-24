"""Health metric signal.

Resting heart rate and related wearable metrics can add context to cycle
prediction, but are intentionally weak evidence compared with LH/BBT.
"""
from datetime import date

from sqlalchemy.orm import Session

from app.modules.cycle.predictor.base import SignalResult
from app.modules.health.service import MetricType, list_metrics


class HealthMetricSignal:
    source = "health"

    def evaluate(self, db: Session, *, user_id: int, target_date: date) -> SignalResult:
        rows = list_metrics(
            db,
            user_id=user_id,
            metric_type=MetricType.RESTING_HEART_RATE,
            start=target_date,
            end=target_date,
        )
        if not rows:
            return SignalResult(
                source=self.source,
                active=False,
                confidence=0.0,
                evidence="no resting heart rate logged today",
            )

        metric = rows[-1]
        return SignalResult(
            source=self.source,
            active=True,
            confidence=0.30,
            evidence=f"静息心率 {metric.value:g} {metric.unit}",
        )
