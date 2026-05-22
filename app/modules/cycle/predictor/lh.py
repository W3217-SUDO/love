"""LH (ovulation test strip) signal.

Reads positive LH tests from daily_tags. LH surge precedes ovulation by
24-36h. We treat ovulation as LH-test-date + 1 day. Active for a ~6-day
window starting the day before the positive test.
"""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cycle.predictor.base import SignalResult
from app.modules.daily_log.models import DailyEntry, DailyTag

LH_WINDOW_BEFORE = 1
LH_WINDOW_AFTER = 5
LOOKBACK_DAYS = 14  # how far back to consider an LH+ relevant


class LHSignal:
    source = "lh"

    def evaluate(self, db: Session, *, user_id: int, target_date: date) -> SignalResult:
        # Find the most recent LH+ within the lookback window
        cutoff = target_date - timedelta(days=LOOKBACK_DAYS)
        future_cap = target_date + timedelta(days=LH_WINDOW_BEFORE)
        row = db.execute(
            select(DailyEntry.date)
            .join(DailyTag, DailyTag.entry_id == DailyEntry.id)
            .where(
                DailyEntry.user_id == user_id,
                DailyTag.tag_key == "ovu_positive",
                DailyEntry.date >= cutoff,
                DailyEntry.date <= future_cap,
            )
            .order_by(DailyEntry.date.desc())
            .limit(1),
        ).scalar_one_or_none()

        if row is None:
            return SignalResult(
                source=self.source, active=False, confidence=0.0,
                evidence="no positive LH test in lookback window",
            )

        lh_date: date = row
        predicted_ovulation = lh_date + timedelta(days=1)
        days_from_lh = (target_date - lh_date).days
        if not (-LH_WINDOW_BEFORE <= days_from_lh <= LH_WINDOW_AFTER):
            return SignalResult(
                source=self.source, active=False, confidence=0.0,
                evidence=f"LH+ on {lh_date.isoformat()} outside active window",
            )

        if target_date < predicted_ovulation:
            phase = "fertile"
        elif target_date == predicted_ovulation:
            phase = "ovulation"
        else:
            phase = "luteal"

        return SignalResult(
            source=self.source,
            active=True,
            confidence=0.95,
            evidence=f"LH+ on {lh_date.isoformat()}",
            predicted_ovulation=predicted_ovulation,
            phase=phase,
        )
