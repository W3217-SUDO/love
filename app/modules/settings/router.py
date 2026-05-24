from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import ValidationFailed
from app.modules.auth.models import User
from app.modules.settings.service import (
    DATA_TYPES,
    Visibility,
    ensure_settings,
    set_visibility,
)
from app.templating import templates

router = APIRouter(tags=["settings"])

LABELS = {
    "diary": "日记",
    "daily_log": "每日记录",
    "cycle": "经期",
    "bbt": "基础体温",
    "trip": "旅行相册",
    "report": "报告",
    "health": "健康指标",
}


@router.get("/me/settings", response_class=HTMLResponse)
def settings_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    settings = ensure_settings(db, user.id)
    return templates.TemplateResponse(
        request=request,
        name="pages/settings.html",
        context={
            "user": user,
            "settings": settings,
            "data_types": DATA_TYPES,
            "labels": LABELS,
            "active": "me",
        },
    )


@router.post("/me/settings/visibility")
def update_visibility(
    data_type: str = Form(...),
    visibility: Visibility = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RedirectResponse:
    settings = ensure_settings(db, user.id)
    try:
        set_visibility(db, settings, data_type, visibility)
    except ValueError as exc:
        raise ValidationFailed(str(exc)) from exc
    return RedirectResponse("/me/settings", status_code=303)
