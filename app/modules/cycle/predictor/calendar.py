"""Calendar-method cycle prediction.

Uses mean gaps between period starts to project the next cycle. The luteal
phase is treated as a constant 14 days (per most fertility-awareness literature),
so ovulation = next_period_start - 14.
"""
from datetime import date, timedelta
from statistics import mean, pstdev

from sqlalchemy.orm import Session

from app.modules.cycle.predictor.base import SignalResult
from app.modules.cycle.service import list_periods

LUTEAL_PHASE_DAYS = 14
FERTILE_WINDOW_BEFORE = 5
FERTILE_WINDOW_AFTER = 1
HISTORY_WINDOW = 12  # load up to last 12 periods for stats; confidence tiers map to n


def _phase_for(
    target: date,
    last_period_start: date,
    last_period_end: date | None,
    ovulation: date,
    fertile_start: date,
    fertile_end: date,
    next_period: date,
) -> str:
    if last_period_end is not None and last_period_start <= target <= last_period_end:
        return "menstrual"
    if last_period_end is not None and last_period_end < target < fertile_start:
        return "follicular"
    if target == ovulation:
        return "ovulation"
    if fertile_start <= target <= fertile_end:
        return "fertile"
    if fertile_end < target < next_period:
        return "luteal"
    if target >= next_period:
        # Probably a new cycle started -- let the caller refresh data.
        return "menstrual"
    # Target before the latest period start, or other edge cases.
    return "follicular"


class CalendarSignal:
    source = "calendar"

    def evaluate(self, db: Session, *, user_id: int, target_date: date) -> SignalResult:
        # list_periods returns DESC; reverse to ASC for stats
        periods = list_periods(db, user_id=user_id, limit=HISTORY_WINDOW)
        if len(periods) < 1:
            return SignalResult(
                source=self.source, active=False, confidence=0.0,
                evidence="no period history yet — add at least one period to start predicting",
            )
        # ASC order for diff
        periods_asc = list(reversed(periods))
        starts = [p.start_date for p in periods_asc]
        if len(starts) >= 2:
            gaps = [(starts[i + 1] - starts[i]).days for i in range(len(starts) - 1)]
            avg_cycle = round(mean(gaps))
            cycle_std = pstdev(gaps) if len(gaps) >= 2 else 0.0
        else:
            # Single-period fallback: assume default 28-day cycle.
            gaps = []
            avg_cycle = 28
            cycle_std = 0.0

        # Period length (closed periods only)
        durations = [
            (p.end_date - p.start_date).days + 1
            for p in periods_asc
            if p.end_date is not None
        ]
        avg_period = round(mean(durations)) if durations else 5

        latest = periods_asc[-1]
        next_period = latest.start_date + timedelta(days=avg_cycle)
        ovulation = next_period - timedelta(days=LUTEAL_PHASE_DAYS)
        fertile_start = ovulation - timedelta(days=FERTILE_WINDOW_BEFORE)
        fertile_end = ovulation + timedelta(days=FERTILE_WINDOW_AFTER)

        # If target_date already past the predicted next_period, project forward.
        if target_date >= next_period:
            next_period = next_period + timedelta(days=avg_cycle)
            ovulation = next_period - timedelta(days=LUTEAL_PHASE_DAYS)
            fertile_start = ovulation - timedelta(days=FERTILE_WINDOW_BEFORE)
            fertile_end = ovulation + timedelta(days=FERTILE_WINDOW_AFTER)

        phase = _phase_for(
            target_date, latest.start_date, latest.end_date,
            ovulation, fertile_start, fertile_end, next_period,
        )

        if len(periods) >= 7:
            confidence = 0.65
        elif len(periods) >= 4:
            confidence = 0.50
        elif len(periods) >= 2:
            confidence = 0.30
        else:
            confidence = 0.20  # 1 period + default 28-day cycle: rough baseline

        return SignalResult(
            source=self.source,
            active=True,
            confidence=confidence,
            evidence=(
                f"avg_cycle={avg_cycle}d (sigma={cycle_std:.1f}), "
                f"avg_period={avg_period}d, n={len(periods)}"
            ),
            predicted_next_period=next_period,
            predicted_ovulation=ovulation,
            fertile_window=(fertile_start, fertile_end),
            phase=phase,
        )
