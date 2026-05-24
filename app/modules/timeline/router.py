"""Timeline (today aggregator) HTTP endpoints."""
import calendar as cal_module
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import NotFound
from app.modules.auth.models import User
from app.modules.cycle.models import Period
from app.modules.cycle.predictor import CombinedPredictor
from app.modules.cycle.service import get_latest_period, list_periods
from app.modules.timeline.service import (
    build_today_snapshot,
    days_together,
    find_partner,
    format_predictor_evidence,
)
from app.templating import templates

router = APIRouter(tags=["timeline"])


def _cycle_day_for(target: date, latest_period_start: date | None) -> int:
    if latest_period_start is None or target < latest_period_start:
        return 1
    return (target - latest_period_start).days + 1


def _phase_color(phase: str) -> str:
    return {
        "menstrual": "#ff7a9c",
        "follicular": "#a0c4ff",
        "fertile": "#ffb74d",
        "ovulation": "#e74e6e",
        "luteal": "#9c89b8",
    }.get(phase, "#cccccc")


def _phase_label(phase: str) -> str:
    return {
        "menstrual": "月经期",
        "follicular": "卵泡期",
        "fertile": "易孕窗口",
        "ovulation": "排卵日",
        "luteal": "黄体期",
        "unknown": "暂无数据",
    }.get(phase, phase)


@router.get("/")
def today_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    today = date.today()
    snap = build_today_snapshot(db, user=user, target_date=today)
    latest = get_latest_period(db, user_id=user.id)
    cycle_day = _cycle_day_for(today, latest.start_date if latest else None)
    # ring progress: scale to perimeter 2πr≈427 for r=68; cycle of ~28 days
    ring_progress = min(int((cycle_day / 28) * 427), 427)

    hour = today.weekday()  # placeholder; could use actual current hour
    greeting = "晚上好" if hour > 5 else "你好"

    return templates.TemplateResponse(
        request=request, name="pages/today.html",
        context={
            "active": "today",
            "user": user,
            "date": today,
            "greeting": greeting,
            "cycle_day": cycle_day,
            "phase_label": _phase_label(snap.cycle_prediction.phase),
            "phase_color": _phase_color(snap.cycle_prediction.phase),
            "ring_progress": ring_progress,
            "prediction": snap.cycle_prediction,
            "prediction_evidence": format_predictor_evidence(snap.cycle_prediction.evidence),
            "active_tags": snap.active_tags,
            "recent_bbt": snap.recent_bbt,
            "partner": snap.partner,
            "partner_tags": snap.partner_tags,
            "partner_phase": _phase_label(snap.partner_phase) if snap.partner_phase else None,
        },
    )


@router.get("/today/partner-card")
def today_partner_card(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    today = date.today()
    snap = build_today_snapshot(db, user=user, target_date=today)
    return templates.TemplateResponse(
        request=request, name="fragments/partner_card.html",
        context={
            "partner": snap.partner,
            "partner_tags": snap.partner_tags,
            "partner_phase": _phase_label(snap.partner_phase) if snap.partner_phase else None,
        },
    )


@router.get("/today/predictor-card")
def today_predictor_card(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pred = CombinedPredictor().predict(db, user_id=user.id, target_date=date.today())
    return templates.TemplateResponse(
        request=request, name="fragments/predictor_card.html",
        context={
            "prediction": pred,
            "prediction_evidence": format_predictor_evidence(pred.evidence),
        },
    )


@router.get("/today/cycle-ring")
def today_cycle_ring(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    today = date.today()
    latest = get_latest_period(db, user_id=user.id)
    pred = CombinedPredictor().predict(db, user_id=user.id, target_date=today)
    cycle_day = _cycle_day_for(today, latest.start_date if latest else None)
    return templates.TemplateResponse(
        request=request, name="fragments/cycle_ring.html",
        context={
            "cycle_day": cycle_day,
            "phase_label": _phase_label(pred.phase),
            "phase_color": _phase_color(pred.phase),
            "ring_progress": min(int((cycle_day / 28) * 427), 427),
        },
    )


def _build_calendar(year: int, month: int, periods: list[Period], pred) -> list[list[dict | None]]:
    """Return 6×7 grid of {day, is_period, is_predicted_period, is_fertile} or None."""
    period_dates: set[date] = set()
    for p in periods:
        end = p.end_date or p.start_date
        d = p.start_date
        while d <= end:
            if d.year == year and d.month == month:
                period_dates.add(d)
            d += timedelta(days=1)

    predicted_period_dates: set[date] = set()
    if (
        pred
        and pred.next_period
        and pred.next_period.year == year
        and pred.next_period.month == month
    ):
        # mark ~5 day window for predicted period
        for i in range(5):
            d = pred.next_period + timedelta(days=i)
            if d.month == month:
                predicted_period_dates.add(d)

    fertile_dates: set[date] = set()
    if pred and pred.fertile_window:
        fs, fe = pred.fertile_window
        d = fs
        while d <= fe:
            if d.year == year and d.month == month:
                fertile_dates.add(d)
            d += timedelta(days=1)

    cal = cal_module.Calendar(firstweekday=6)  # Sunday-first
    weeks: list[list[dict | None]] = []
    for week in cal.monthdayscalendar(year, month):
        row: list[dict | None] = []
        for d_int in week:
            if d_int == 0:
                row.append(None)
            else:
                d = date(year, month, d_int)
                row.append({
                    "day": d_int,
                    "is_period": d in period_dates,
                    "is_predicted_period": d in predicted_period_dates,
                    "is_fertile": d in fertile_dates,
                })
        weeks.append(row)
    return weeks


@router.get("/calendar")
def calendar_current(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    today = date.today()
    return _render_calendar(request, db, user, today.year, today.month)


@router.get("/calendar/{year}/{month}")
def calendar_for(
    year: int, month: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _render_calendar(request, db, user, year, month)


def _render_calendar(
    request: Request,
    db: Session,
    user: User,
    year: int,
    month: int,
) -> Response:
    if not (1 <= month <= 12):
        raise NotFound("invalid month")
    periods = list_periods(db, user_id=user.id)
    pred = CombinedPredictor().predict(
        db, user_id=user.id, target_date=date(year, month, 15),
    )
    weeks = _build_calendar(year, month, periods, pred)
    prev_year, prev_month = (year, month - 1) if month > 1 else (year - 1, 12)
    next_year, next_month = (year, month + 1) if month < 12 else (year + 1, 1)
    return templates.TemplateResponse(
        request=request, name="pages/calendar.html",
        context={
            "active": "calendar",
            "year": year, "month": month, "weeks": weeks,
            "prev_year": prev_year, "prev_month": prev_month,
            "next_year": next_year, "next_month": next_month,
        },
    )


@router.get("/me")
def me_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    partner = find_partner(db, user.id)
    days = days_together(db, user.id)
    from sqlalchemy import select

    from app.modules.auth.models import Couple
    couple = db.execute(
        select(Couple).where(
            (Couple.user_a_id == user.id) | (Couple.user_b_id == user.id),
        ),
    ).scalar_one_or_none()
    return templates.TemplateResponse(
        request=request, name="pages/me.html",
        context={
            "active": "me",
            "you": user, "partner": partner,
            "days_together": days, "couple": couple,
        },
    )


@router.post("/me/anniversary")
async def post_anniversary(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from datetime import date as _date

    from fastapi.responses import RedirectResponse as _Redirect
    from sqlalchemy import select as _select

    from app.modules.auth.models import Couple as _Couple
    form = await request.form()
    anniversary = form.get("anniversary")
    raw = anniversary.strip() if isinstance(anniversary, str) else ""
    couple = db.execute(
        _select(_Couple).where(
            (_Couple.user_a_id == user.id) | (_Couple.user_b_id == user.id),
        ),
    ).scalar_one_or_none()
    if couple is None:
        return _Redirect(url="/me", status_code=303)
    if not raw:
        couple.anniversary = None
    else:
        try:
            couple.anniversary = _date.fromisoformat(raw)
        except ValueError:
            pass
    db.commit()
    return _Redirect(url="/me", status_code=303)
