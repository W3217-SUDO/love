"""Daily log HTTP endpoints."""
from datetime import date as date_t
from datetime import datetime

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import NotFound
from app.modules.auth.models import User
from app.modules.daily_log.catalog import (
    CATEGORIES,
    TAG_BY_KEY,
    TAGS_BY_CATEGORY,
    is_valid_tag,
)
from app.modules.daily_log.schemas import (
    DailyTagOut,
    NotesRequest,
    ToggleResponse,
)
from app.modules.daily_log.service import (
    UnknownTagError,
    list_tags_for_day,
    set_notes,
    toggle_tag,
)
from app.templating import templates
from app.util.http import wants_html

router = APIRouter(tags=["daily_log"])


@router.get("/log/today")
def get_log_today(
    user: User = Depends(get_current_user),
) -> RedirectResponse:
    today = date_t.today()
    return RedirectResponse(
        url=f"/log/{today.isoformat()}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/log/{date_str}")
def get_log_for_date(
    date_str: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        day = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise NotFound(f"invalid date: {date_str!r}") from exc

    active_tags = list_tags_for_day(db, user_id=user.id, date=day)
    active_keys = {t.tag_key for t in active_tags}

    # JSON response for programmatic clients
    if not wants_html(request):
        return {
            "date": day.isoformat(),
            "tags": [DailyTagOut.model_validate(t).model_dump() for t in active_tags],
        }

    # HTML — render the log sheet
    return templates.TemplateResponse(
        request=request, name="pages/log_sheet.html",
        context={
            "date": day,
            "categories": CATEGORIES,
            "tags_by_category": TAGS_BY_CATEGORY,
            "active_keys": active_keys,
            "notes": None,
        },
    )


@router.post("/log/{date_str}/tag/{tag_key}/toggle")
def post_toggle_tag(
    date_str: str,
    tag_key: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        day = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise NotFound(f"invalid date: {date_str!r}") from exc

    if not is_valid_tag(tag_key):
        raise NotFound(f"unknown tag: {tag_key!r}")

    try:
        _, active = toggle_tag(db, user_id=user.id, date=day, tag_key=tag_key)
        db.commit()
    except UnknownTagError as exc:
        raise NotFound(str(exc)) from exc

    if wants_html(request):
        tag = TAG_BY_KEY[tag_key]
        return templates.TemplateResponse(
            request=request,
            name="fragments/tag_pill.html",
            context={"tag": tag, "active": active, "date": day},
        )

    return ToggleResponse(tag_key=tag_key, active=active)


@router.put("/log/{date_str}/notes")
def put_notes(
    date_str: str,
    payload: NotesRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        day = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise NotFound(f"invalid date: {date_str!r}") from exc
    set_notes(db, user_id=user.id, date=day, notes=payload.notes)
    db.commit()
    return {"status": "ok"}
