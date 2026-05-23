"""HTML pages + delete endpoints for cycle log and BBT log."""
from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import NotFound
from app.modules.auth.models import User
from app.modules.cycle.models import BbtReading, Period
from app.modules.cycle.service import list_bbt, list_periods
from app.templating import templates

router = APIRouter(tags=["cycle-html"])


@router.get("/cycle/log", response_class=HTMLResponse)
def cycle_log_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    periods = list_periods(db, user_id=user.id)
    return templates.TemplateResponse(
        request=request,
        name="pages/cycle_log.html",
        context={
            "user": user,
            "periods": periods,
            "today": date.today().isoformat(),
            "active": "cycle",
        },
    )


@router.post("/cycle/log/{period_id}/delete")
def delete_period(
    period_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    p = db.query(Period).filter_by(id=period_id, user_id=user.id).one_or_none()
    if p is None:
        raise NotFound(f"period {period_id} not found")
    db.delete(p)
    db.commit()
    return RedirectResponse(url="/cycle/log", status_code=303)


@router.get("/bbt/log", response_class=HTMLResponse)
def bbt_log_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    readings = list_bbt(db, user_id=user.id, limit=60)
    # service returns ASC — reverse for "recent first" display
    readings = list(reversed(readings))
    return templates.TemplateResponse(
        request=request,
        name="pages/bbt_log.html",
        context={
            "user": user,
            "readings": readings,
            "today": date.today().isoformat(),
            "active": "bbt",
        },
    )


@router.post("/bbt/log/{reading_id}/delete")
def delete_bbt(
    reading_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = db.query(BbtReading).filter_by(id=reading_id, user_id=user.id).one_or_none()
    if r is None:
        raise NotFound(f"reading {reading_id} not found")
    db.delete(r)
    db.commit()
    return RedirectResponse(url="/bbt/log", status_code=303)
