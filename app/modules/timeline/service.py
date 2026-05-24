"""TimelineService — assemble today aggregator data."""
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.models import Couple, User
from app.modules.cycle.predictor import CombinedPredictor, CyclePrediction
from app.modules.cycle.predictor.base import SignalResult
from app.modules.cycle.predictor.calendar import CalendarSignal
from app.modules.cycle.service import list_bbt
from app.modules.daily_log.catalog import TAG_BY_KEY
from app.modules.daily_log.models import DailyTag
from app.modules.daily_log.service import list_tags_for_day
from app.modules.settings.service import can_partner_view, ensure_settings


@dataclass
class TagDisplay:
    """A tag enriched with its catalog metadata for the template."""
    tag_key: str
    category: str
    label: str
    emoji: str


@dataclass(frozen=True)
class EvidenceDisplay:
    """A predictor signal prepared for user-facing rendering."""
    source_label: str
    status_label: str
    evidence: str
    active: bool


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


def _source_label(source: str) -> str:
    return {
        "calendar": "周期记录",
        "bbt": "基础体温",
        "lh": "LH 试纸",
        "mucus": "分泌物",
        "health": "健康指标",
    }.get(source, source)


def _fallback_evidence(source: str) -> str:
    return {
        "calendar": "已记录周期证据",
        "bbt": "已记录基础体温证据",
        "lh": "已记录排卵测试证据",
        "mucus": "已记录辅助健康证据",
        "health": "已记录辅助健康证据",
    }.get(source, "已记录辅助健康证据")


def _translate_evidence(text: str, *, source: str) -> str:
    avg_match = re.search(
        r"avg_cycle=(?P<cycle>\d+)d \(sigma=(?P<sigma>[\d.]+)\), "
        r"avg_period=(?P<period>\d+)d, n=(?P<count>\d+)",
        text,
    )
    if avg_match:
        return (
            f"平均周期 {avg_match['cycle']} 天，波动 {avg_match['sigma']} 天；"
            f"平均经期 {avg_match['period']} 天；样本 {avg_match['count']} 次"
        )

    need_match = re.search(r"need >=(?P<need>\d+) readings, have (?P<have>\d+)", text)
    if need_match:
        return f"基础体温记录不足：需要至少 {need_match['need']} 条，目前 {need_match['have']} 条"

    lh_outside_match = re.search(
        r"LH\+ on (?P<date>\d{4}-\d{2}-\d{2}) outside active window",
        text,
    )
    if lh_outside_match:
        return f"LH 阳性记录在 {lh_outside_match['date']}，已超出当前参考窗口"

    lh_match = re.search(r"LH\+ on (?P<date>\d{4}-\d{2}-\d{2})", text)
    if lh_match:
        return f"LH 阳性记录：{lh_match['date']}"

    bbt_match = re.search(
        r"BBT 3-step at (?P<start>\d{4}-\d{2}-\d{2})->(?P<end>\d{4}-\d{2}-\d{2})",
        text,
    )
    if bbt_match:
        return f"基础体温三步升温：{bbt_match['start']} 至 {bbt_match['end']}"

    translations = {
        "no period history yet — add at least one period to start predicting":
            "暂无月经记录：至少记录一次经期后可开始预测",
        "no positive LH test in lookback window": "回看窗口内暂无 LH 阳性记录",
        "no three-step temperature rise detected": "暂未发现连续升温信号",
        "no egg-white discharge logged today": "今日未记录蛋清状分泌物",
        "no resting heart rate logged today": "今日未记录静息心率",
    }
    return translations.get(text, _fallback_evidence(source))


def format_predictor_evidence(evidence: list[SignalResult]) -> list[EvidenceDisplay]:
    return [
        EvidenceDisplay(
            source_label=_source_label(item.source),
            status_label="已纳入预测" if item.active else "暂无有效信号",
            evidence=_translate_evidence(item.evidence, source=item.source),
            active=item.active,
        )
        for item in evidence
    ]


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
    d = bonded.date() if isinstance(bonded, datetime) else bonded
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
        partner_settings = ensure_settings(db, partner.id)
        if can_partner_view(partner_settings, "cycle"):
            p_signal = CalendarSignal().evaluate(
                db, user_id=partner.id, target_date=target_date,
            )
            partner_phase = p_signal.phase if p_signal.active and p_signal.phase else None
        if can_partner_view(partner_settings, "daily_log"):
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
