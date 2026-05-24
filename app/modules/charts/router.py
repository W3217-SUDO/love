"""Charts center routes."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.modules.auth.models import User
from app.modules.charts.service import (
    build_bbt_series,
    build_cycle_series,
    build_health_series,
    build_tag_frequency,
)
from app.templating import templates

router = APIRouter(tags=["charts"])


@router.get("/charts")
def charts_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    summaries = {
        "bbt": build_bbt_series(db, user.id),
        "cycle": build_cycle_series(db, user.id),
        "symptoms": build_tag_frequency(db, user.id, "symptoms"),
        "mood": build_tag_frequency(db, user.id, "mood"),
        "intimacy": build_tag_frequency(db, user.id, "sex"),
        "health": build_health_series(db, user.id, "resting_heart_rate"),
    }
    return templates.TemplateResponse(
        request=request,
        name="pages/charts.html",
        context={"active": "charts", "summaries": summaries},
    )


@router.get("/charts/bbt.json")
def bbt_series(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    return build_bbt_series(db, user.id)


@router.get("/charts/cycle.json")
def cycle_series(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    return build_cycle_series(db, user.id)


@router.get("/charts/tags/{category}.json")
def tag_series(
    category: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    return build_tag_frequency(db, user.id, category)


@router.get("/charts/health/{metric_type}.json")
def health_series(
    metric_type: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    return build_health_series(db, user.id, metric_type)
