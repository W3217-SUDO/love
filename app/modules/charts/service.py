"""Small deterministic series builders for the charts center."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.cycle.service import list_bbt, list_periods
from app.modules.daily_log.models import DailyEntry, DailyTag
from app.modules.health.service import list_metrics


def _number(value) -> float:
    return float(value)


def build_bbt_series(db: Session, user_id: int) -> dict:
    rows = list_bbt(db, user_id=user_id)
    return {
        "kind": "bbt",
        "points": [
            {"date": row.date.isoformat(), "value": _number(row.temp_c)}
            for row in rows
        ],
    }


def build_cycle_series(db: Session, user_id: int) -> dict:
    periods = list(reversed(list_periods(db, user_id=user_id)))
    points = [
        {
            "date": period.start_date.isoformat(),
            "value": (next_period.start_date - period.start_date).days,
        }
        for period, next_period in zip(periods, periods[1:], strict=False)
    ]
    return {"kind": "cycle", "points": points}


def build_tag_frequency(db: Session, user_id: int, category: str) -> dict:
    stmt = (
        select(DailyTag.tag_key, func.count(DailyTag.id))
        .join(DailyEntry, DailyEntry.id == DailyTag.entry_id)
        .where(DailyEntry.user_id == user_id, DailyTag.category == category)
        .group_by(DailyTag.tag_key)
        .order_by(func.count(DailyTag.id).desc(), DailyTag.tag_key.asc())
    )
    points = [
        {"tag": tag_key, "count": int(count)}
        for tag_key, count in db.execute(stmt).all()
    ]
    return {"kind": "tags", "category": category, "points": points}


def build_health_series(db: Session, user_id: int, metric_type: str) -> dict:
    rows = list_metrics(db, user_id=user_id, metric_type=metric_type)
    return {
        "kind": "health",
        "metric_type": metric_type,
        "points": [
            {
                "date": row.date.isoformat(),
                "value": _number(row.value),
                "unit": row.unit,
                "source": row.source,
            }
            for row in rows
        ],
    }
