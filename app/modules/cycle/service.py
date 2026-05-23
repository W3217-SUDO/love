"""Period and BBT CRUD service for the cycle domain.

Wraps raw SQLAlchemy with business invariants:
  - Period overlap protection (new start can't fall inside another period)
  - BBT upsert semantics (one reading per user per day)
  - Validation of temp range and method before DB

Endpoints in router.py and predictors call these functions; nothing should hit
the cycle models directly.
"""
from datetime import date, time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cycle.models import BbtReading, Period

VALID_BBT_METHODS = {"oral", "vaginal", "axillary", "wrist", "other"}
MIN_TEMP_C = Decimal("35.00")
MAX_TEMP_C = Decimal("38.00")
# How close to an open (no-end) period is considered "overlapping". A typical
# period is ~5 days, average cycle ~28; a new start within 30 days of an open
# period is almost certainly the same period restated.
OPEN_PERIOD_BUFFER_DAYS = 30


class CycleError(Exception):
    """Base class for cycle service errors."""


class PeriodOverlapError(CycleError):
    """Raised when a new period start falls inside an existing period or too
    close to an open one."""


class PeriodNotFound(CycleError):
    """Raised when an operation references a period that doesn't exist."""


class InvalidBbtReading(CycleError):
    """Raised when BBT input fails validation before hitting the DB."""


# ---------- Period ----------

def log_period_start(
    db: Session,
    *,
    user_id: int,
    start_date: date,
    notes: str | None = None,
) -> Period:
    """Idempotently start a period.

    Returns the existing row if (user_id, start_date) already matches; else
    inserts new after overlap check.
    """
    existing = db.execute(
        select(Period).where(
            Period.user_id == user_id, Period.start_date == start_date,
        ),
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    # Overlap check
    candidates = db.execute(
        select(Period).where(Period.user_id == user_id),
    ).scalars().all()
    for other in candidates:
        if other.end_date is not None:
            if other.start_date <= start_date <= other.end_date:
                raise PeriodOverlapError(
                    f"{start_date} falls inside existing period "
                    f"{other.start_date}..{other.end_date}",
                )
        else:
            # Open period — block anything within buffer days either direction
            delta = abs((start_date - other.start_date).days)
            if delta <= OPEN_PERIOD_BUFFER_DAYS:
                raise PeriodOverlapError(
                    f"{start_date} is within {OPEN_PERIOD_BUFFER_DAYS} days of "
                    f"open period starting {other.start_date}",
                )

    period = Period(user_id=user_id, start_date=start_date, notes=notes)
    db.add(period)
    return period


def log_period_end(
    db: Session,
    *,
    user_id: int,
    start_date: date,
    end_date: date,
) -> Period:
    """Set end_date on the period with matching (user_id, start_date)."""
    if end_date < start_date:
        raise ValueError(
            f"end_date ({end_date}) must be on or after start_date ({start_date})",
        )
    period = db.execute(
        select(Period).where(
            Period.user_id == user_id, Period.start_date == start_date,
        ),
    ).scalar_one_or_none()
    if period is None:
        raise PeriodNotFound(
            f"no period with start_date {start_date} for user {user_id}",
        )
    period.end_date = end_date
    return period


def list_periods(
    db: Session,
    *,
    user_id: int,
    limit: int | None = None,
    offset: int = 0,
) -> list[Period]:
    """Return periods for a user, most-recent first."""
    stmt = (
        select(Period)
        .where(Period.user_id == user_id)
        .order_by(Period.start_date.desc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset:
        stmt = stmt.offset(offset)
    return list(db.execute(stmt).scalars().all())


def get_latest_period(db: Session, *, user_id: int) -> Period | None:
    """Highest start_date period, or None if user has none."""
    return db.execute(
        select(Period)
        .where(Period.user_id == user_id)
        .order_by(Period.start_date.desc())
        .limit(1),
    ).scalar_one_or_none()


# ---------- BBT ----------

def log_bbt(
    db: Session,
    *,
    user_id: int,
    date: date,
    temp_c: Decimal,
    measure_time: time | None = None,
    method: str | None = None,
    notes: str | None = None,
) -> BbtReading:
    """Upsert today's BBT reading."""
    # Validate before DB
    if not isinstance(temp_c, Decimal):
        temp_c = Decimal(str(temp_c))
    if temp_c < MIN_TEMP_C or temp_c > MAX_TEMP_C:
        raise InvalidBbtReading(
            f"temp_c {temp_c} outside allowed range [{MIN_TEMP_C}, {MAX_TEMP_C}]",
        )
    if method is not None and method not in VALID_BBT_METHODS:
        raise InvalidBbtReading(
            f"method {method!r} not in {sorted(VALID_BBT_METHODS)}",
        )

    existing = db.execute(
        select(BbtReading).where(
            BbtReading.user_id == user_id, BbtReading.date == date,
        ),
    ).scalar_one_or_none()
    if existing is not None:
        existing.temp_c = temp_c
        if measure_time is not None:
            existing.measure_time = measure_time
        if method is not None:
            existing.method = method
        if notes is not None:
            existing.notes = notes
        return existing

    row = BbtReading(
        user_id=user_id, date=date, temp_c=temp_c,
        measure_time=measure_time, method=method, notes=notes,
    )
    db.add(row)
    return row


def list_bbt(
    db: Session,
    *,
    user_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int | None = None,
) -> list[BbtReading]:
    """Return readings ordered by date ASC; optional date filter."""
    stmt = select(BbtReading).where(BbtReading.user_id == user_id)
    if start_date is not None:
        stmt = stmt.where(BbtReading.date >= start_date)
    if end_date is not None:
        stmt = stmt.where(BbtReading.date <= end_date)
    stmt = stmt.order_by(BbtReading.date.asc())
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.execute(stmt).scalars().all())
