"""BBT three-step (coverline) ovulation detection.

Standard fertility-awareness method: find a day T1 where the BBT exceeds the
maximum of the previous 6 days by >=0.2C, and the following two days (T2, T3)
both stay above that coverline (with at least one day >=0.2C above it).
Ovulation is identified as T1 - 1 day.

We declare the signal active only when target_date falls within ~5 days after
the detected ovulation (post-ovulation luteal window).
"""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.cycle.predictor.base import SignalResult
from app.modules.cycle.service import list_bbt

MIN_READINGS = 9  # 6-day coverline + T1 + T2 + T3
COVERLINE_LOOKBACK = 6
TEMP_RISE_THRESHOLD = Decimal("0.20")
POST_OVULATION_WINDOW = 5  # days where BBT signal stays "active"


class BBTSignal:
    source = "bbt"

    def evaluate(self, db: Session, *, user_id: int, target_date: date) -> SignalResult:
        # Load 30 days ending at target_date
        start = target_date - timedelta(days=30)
        readings = list_bbt(db, user_id=user_id, start_date=start, end_date=target_date)
        if len(readings) < MIN_READINGS:
            return SignalResult(
                source=self.source, active=False, confidence=0.0,
                evidence=f"need >={MIN_READINGS} readings, have {len(readings)}",
            )

        readings_sorted = sorted(readings, key=lambda r: r.date)

        # Slide T1 across readings starting from index COVERLINE_LOOKBACK
        detected_t1: date | None = None
        t3_date: date | None = None
        for idx in range(COVERLINE_LOOKBACK, len(readings_sorted) - 2):
            t1 = readings_sorted[idx]
            t2 = readings_sorted[idx + 1]
            t3 = readings_sorted[idx + 2]
            # Coverline = max of the 6 days before T1
            coverline_window = readings_sorted[idx - COVERLINE_LOOKBACK:idx]
            coverline = max(r.temp_c for r in coverline_window)

            if t1.temp_c - coverline < TEMP_RISE_THRESHOLD:
                continue
            if t2.temp_c <= coverline or t3.temp_c <= coverline:
                continue
            # At least one of T2/T3 must be coverline + threshold
            if (t2.temp_c - coverline < TEMP_RISE_THRESHOLD
                    and t3.temp_c - coverline < TEMP_RISE_THRESHOLD):
                continue
            detected_t1 = t1.date
            t3_date = t3.date
            break

        if detected_t1 is None:
            return SignalResult(
                source=self.source, active=False, confidence=0.0,
                evidence="no three-step temperature rise detected",
            )

        ovulation = detected_t1 - timedelta(days=1)
        days_since = (target_date - ovulation).days
        if not (0 <= days_since <= POST_OVULATION_WINDOW):
            return SignalResult(
                source=self.source, active=False, confidence=0.0,
                evidence=(
                    f"BBT detected ovulation on {ovulation.isoformat()} "
                    f"but target {target_date.isoformat()} outside post-ovulation window"
                ),
            )

        return SignalResult(
            source=self.source,
            active=True,
            confidence=0.85,
            evidence=f"BBT 3-step at {detected_t1.isoformat()}->{t3_date.isoformat()}",
            predicted_ovulation=ovulation,
            phase="luteal",
        )
