"""HTML pages for cycle log and BBT log — overlay the JSON API endpoints."""
from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.modules.auth.models import User
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


@router.get("/bbt/log", response_class=HTMLResponse)
def bbt_log_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    readings = list_bbt(db, user_id=user.id, limit=60)
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
