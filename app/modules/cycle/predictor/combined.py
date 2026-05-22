"""Combined predictor: merges signals into a single CyclePrediction.

M1 implements Calendar + BBT. Future: LH, Mucus, RHR/HRV per spec section 7.1.
"""
from datetime import date

from sqlalchemy.orm import Session

from app.modules.cycle.predictor.base import (
    ConfidenceLevel,
    CyclePrediction,
    Signal,
    SignalResult,
)
from app.modules.cycle.predictor.bbt import BBTSignal
from app.modules.cycle.predictor.calendar import CalendarSignal


def _confidence_level(score: float) -> ConfidenceLevel:
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


class CombinedPredictor:
    """Order matters: signals listed first take priority when conflicts arise."""

    def __init__(self, signals: list[Signal] | None = None) -> None:
        self.signals: list[Signal] = signals if signals is not None else [
            BBTSignal(),       # post-hoc ovulation lock
            CalendarSignal(),  # baseline projection
        ]

    def predict(
        self,
        db: Session,
        *,
        user_id: int,
        target_date: date,
    ) -> CyclePrediction:
        results: list[SignalResult] = [
            sig.evaluate(db, user_id=user_id, target_date=target_date)
            for sig in self.signals
        ]
        active = [r for r in results if r.active]

        if not active:
            return CyclePrediction(
                target_date=target_date,
                next_period=None,
                ovulation=None,
                fertile_window=None,
                phase="unknown",
                confidence_level="low",
                confidence_score=0.0,
                evidence=results,
            )

        # Merge: start with calendar (if active) for next_period, override
        # ovulation with BBT (if active) for high-confidence post-hoc lock.
        cal = next((r for r in active if r.source == "calendar"), None)
        bbt = next((r for r in active if r.source == "bbt"), None)

        next_period = cal.predicted_next_period if cal else None
        ovulation = (bbt.predicted_ovulation if bbt
                     else (cal.predicted_ovulation if cal else None))
        fertile_window = cal.fertile_window if cal else None
        phase = (bbt.phase if bbt
                 else (cal.phase if cal else "unknown"))

        confidence_score = max(r.confidence for r in active)
        return CyclePrediction(
            target_date=target_date,
            next_period=next_period,
            ovulation=ovulation,
            fertile_window=fertile_window,
            phase=phase or "unknown",
            confidence_level=_confidence_level(confidence_score),
            confidence_score=confidence_score,
            evidence=results,  # all results, including inactive, for UI
        )
