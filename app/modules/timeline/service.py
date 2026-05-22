"""TimelineService — assemble today aggregator data."""
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.models import Couple, User
from app.modules.cycle.predictor import CombinedPredictor, CyclePrediction
from app.modules.cycle.service import list_bbt
from app.modules.daily_log.catalog import TAG_BY_KEY
from app.modules.daily_log.models import DailyTag
from app.modules.daily_log.service import list_tags_for_day


@dataclass
class TagDisplay:
    """A tag enriched with its catalog metadata for the template."""
    tag_key: str
    category: str
    label: str
    emoji: str


def _enrich_tags(rows: list[DailyTag]) -> list[TagDisplay]:
    out: list[TagDisplay] = []
    for r in rows:
        meta = TAG_BY_KEY.get(r.tag_key)
        if meta is None:
            out.append(TagDisplay(
                tag_key=r.tag_key, category=r.category,
                label=r.tag_key, emoji="🏷",
            ))
        else:
            out.append(TagDisplay(
                tag_key=meta.key, category=meta.category,
                label=meta.label, emoji=meta.emoji,
            ))
    return out


def find_partner(db: Session, user_id: int) -> User | None:
    """Return the other user in the Couple, or None if not bonded."""
    couple = db.execute(
        select(Couple).where(
            (Couple.user_a_id == user_id) | (Couple.user_b_id == user_id),
        ),
    ).scalar_one_or_none()
    if couple is None:
        return None
    partner_id = (
        couple.user_b_id if couple.user_a_id == user_id else couple.user_a_id
    )
    return db.execute(
        select(User).where(User.id == partner_id),
    ).scalar_one_or_none()


def days_together(db: Session, user_id: int) -> int | None:
    couple = db.execute(
        select(Couple).where(
            (Couple.user_a_id == user_id) | (Couple.user_b_id == user_id),
        ),
    ).scalar_one_or_none()
    if couple is None:
        return None
    bonded = couple.anniversary or couple.bonded_at or couple.created_at
    if bonded is None:
        return None
    d = bonded.date() if hasattr(bonded, "date") and not isinstance(bonded, date) else bonded
    return (date.today() - d).days


@dataclass
class TodaySnapshot:
    user: User
    date: date
    cycle_prediction: CyclePrediction
    active_tags: list[TagDisplay]
    recent_bbt: list  # list[BbtReading]
    partner: User | None
    partner_tags: list[TagDisplay] = field(default_factory=list)
    partner_phase: str | None = None


def build_today_snapshot(
    db: Session, *, user: User, target_date: date,
) -> TodaySnapshot:
    pred = CombinedPredictor().predict(db, user_id=user.id, target_date=target_date)
    own_tags = list_tags_for_day(db, user_id=user.id, date=target_date)
    bbt = list_bbt(
        db, user_id=user.id,
        start_date=target_date - timedelta(days=6),
        end_date=target_date,
    )
    partner = find_partner(db, user.id)
    partner_tags: list[TagDisplay] = []
    partner_phase: str | None = None
    if partner is not None:
        p_pred = CombinedPredictor().predict(
            db, user_id=partner.id, target_date=target_date,
        )
        partner_phase = p_pred.phase if p_pred.phase != "unknown" else None
        partner_tags = _enrich_tags(
            list_tags_for_day(db, user_id=partner.id, date=target_date),
        )

    return TodaySnapshot(
        user=user, date=target_date,
        cycle_prediction=pred,
        active_tags=_enrich_tags(own_tags),
        recent_bbt=bbt,
        partner=partner,
        partner_tags=partner_tags,
        partner_phase=partner_phase,
    )
