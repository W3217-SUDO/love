"""Combined predictor: merges signals into a single CyclePrediction."""
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
from app.modules.cycle.predictor.health import HealthMetricSignal
from app.modules.cycle.predictor.lh import LHSignal
from app.modules.cycle.predictor.mucus import MucusSignal


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
            LHSignal(),         # highest priority -- real-time
            BBTSignal(),        # post-hoc lock
            CalendarSignal(),   # baseline
            MucusSignal(),      # supportive evidence
            HealthMetricSignal(),  # weak wearable evidence
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

        # Merge: priority LH > BBT > Calendar. Supportive signals stay evidence-only.
        lh = next((r for r in active if r.source == "lh"), None)
        bbt = next((r for r in active if r.source == "bbt"), None)
        cal = next((r for r in active if r.source == "calendar"), None)
        core = lh or bbt or cal

        next_period = cal.predicted_next_period if cal else None
        ovulation = (
            lh.predicted_ovulation if lh
            else (bbt.predicted_ovulation if bbt
                  else (cal.predicted_ovulation if cal else None))
        )
        fertile_window = cal.fertile_window if cal else None
        phase = (
            lh.phase if lh
            else (bbt.phase if bbt
                  else (cal.phase if cal else "unknown"))
        )

        confidence_score = core.confidence if core is not None else 0.0
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
