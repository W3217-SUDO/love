"""Cervical mucus signal.

Egg-white discharge is a fertility-awareness sign that ovulation may be near.
It is useful evidence, but lower priority than LH and BBT.
"""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cycle.predictor.base import SignalResult
from app.modules.daily_log.models import DailyEntry, DailyTag

FERTILE_MUCUS_TAG = "disch_egg_white"


class MucusSignal:
    source = "mucus"

    def evaluate(self, db: Session, *, user_id: int, target_date: date) -> SignalResult:
        row = db.execute(
            select(DailyEntry.date)
            .join(DailyTag, DailyTag.entry_id == DailyEntry.id)
            .where(
                DailyEntry.user_id == user_id,
                DailyEntry.date == target_date,
                DailyTag.tag_key == FERTILE_MUCUS_TAG,
            )
            .limit(1),
        ).scalar_one_or_none()

        if row is None:
            return SignalResult(
                source=self.source,
                active=False,
                confidence=0.0,
                evidence="no egg-white discharge logged today",
            )

        predicted_ovulation = target_date + timedelta(days=1)
        return SignalResult(
            source=self.source,
            active=True,
            confidence=0.60,
            evidence="接近排卵：蛋清状分泌物",
            predicted_ovulation=predicted_ovulation,
            phase="fertile",
        )
