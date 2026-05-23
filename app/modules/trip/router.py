"""Trip HTTP endpoints."""
from datetime import date as date_t

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import Forbidden, NotFound
from app.modules.auth.models import User
from app.modules.media.signing import sign_media_url
from app.modules.trip.schemas import AttachMediaRequest, TripOut
from app.modules.trip.service import (
    TripForbidden,
    TripNotFound,
    attach_media,
    create_trip,
    delete_trip,
    detach_media,
    get_trip,
    list_media,
    list_trips,
    set_cover,
    update_trip,
)
from app.templating import templates
from app.util.http import wants_html

router = APIRouter(tags=["trip"])


def _form_str(value: object, default: str | None = None) -> str | None:
    return value if isinstance(value, str) else default


def _creator_name(db: Session, user_id: int) -> str:
    u = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    return u.display_name if u else "?"


def _parse_date(s: str | None) -> date_t | None:
    if not s:
        return None
    return date_t.fromisoformat(s)


@router.get("/trip")
def trip_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    trips = list_trips(db, requester_id=user.id)
    enriched = []
    for t in trips:
        thumb_url = None
        if t.cover_media_id:
            thumb_url = f"/media/{t.cover_media_id}/thumb?{sign_media_url(t.cover_media_id)}"
        enriched.append({
            "id": t.id, "title": t.title, "location": t.location,
            "start_date": t.start_date, "end_date": t.end_date,
            "cover_thumb_url": thumb_url,
        })
    if wants_html(request):
        return templates.TemplateResponse(
            request=request, name="pages/trip_list.html",
            context={"trips": enriched},
        )
    return [TripOut.model_validate(t).model_dump(mode="json") for t in trips]


@router.get("/trip/new")
def trip_new(
    request: Request,
    user: User = Depends(get_current_user),
):
    return templates.TemplateResponse(
        request=request, name="pages/trip_edit.html",
        context={"trip": None, "media_list": []},
    )


@router.get("/trip/{trip_id}")
def trip_detail(
    trip_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        t = get_trip(db, trip_id=trip_id, requester_id=user.id)
    except TripNotFound as exc:
        raise NotFound(str(exc)) from exc
    except TripForbidden as exc:
        raise Forbidden(str(exc)) from exc
    media_pairs = list_media(db, trip_id=trip_id, requester_id=user.id)
    media_list = []
    for link, m in media_pairs:
        media_list.append((
            link,
            type("M", (), {
                "id": m.id,
                "thumb_url": f"/media/{m.id}/thumb?{sign_media_url(m.id)}",
                "preview_url": f"/media/{m.id}/preview?{sign_media_url(m.id)}",
            })(),
        ))
    return templates.TemplateResponse(
        request=request, name="pages/trip_detail.html",
        context={
            "trip": t, "media_list": media_list,
            "creator_name": _creator_name(db, t.created_by_id),
            "is_creator": t.created_by_id == user.id,
        },
    )


@router.get("/trip/{trip_id}/edit")
def trip_edit_get(
    trip_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        t = get_trip(db, trip_id=trip_id, requester_id=user.id)
    except TripNotFound as exc:
        raise NotFound(str(exc)) from exc
    except TripForbidden as exc:
        raise Forbidden(str(exc)) from exc
    media_pairs = list_media(db, trip_id=trip_id, requester_id=user.id)
    media_list = []
    for link, m in media_pairs:
        media_list.append((
            link,
            type("M", (), {
                "id": m.id,
                "thumb_url": f"/media/{m.id}/thumb?{sign_media_url(m.id)}",
            })(),
        ))
    return templates.TemplateResponse(
        request=request, name="pages/trip_edit.html",
        context={"trip": t, "media_list": media_list},
    )


@router.post("/trip")
async def trip_create(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    form = await request.form()
    try:
        t = create_trip(
            db,
            creator_id=user.id,
            title=_form_str(form.get("title"), "") or "",
            location=_form_str(form.get("location")) or None,
            start_date=_parse_date(_form_str(form.get("start_date"))),
            end_date=_parse_date(_form_str(form.get("end_date"))),
            description=_form_str(form.get("description")) or None,
        )
        db.commit()
    except ValueError as exc:
        from app.errors import ValidationFailed
        raise ValidationFailed(str(exc)) from exc
    return RedirectResponse(url=f"/trip/{t.id}", status_code=303)


@router.post("/trip/{trip_id}")
async def trip_update(
    trip_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    form = await request.form()
    try:
        location = _form_str(form.get("location"))
        description = _form_str(form.get("description"))
        t = update_trip(
            db,
            trip_id=trip_id, requester_id=user.id,
            title=_form_str(form.get("title")) or None,
            location=location if location is not None else None,
            start_date=_parse_date(_form_str(form.get("start_date"))),
            end_date=_parse_date(_form_str(form.get("end_date"))),
            description=description if description is not None else None,
        )
        db.commit()
    except TripNotFound as exc:
        raise NotFound(str(exc)) from exc
    except TripForbidden as exc:
        raise Forbidden(str(exc)) from exc
    except ValueError as exc:
        from app.errors import ValidationFailed
        raise ValidationFailed(str(exc)) from exc
    return RedirectResponse(url=f"/trip/{t.id}", status_code=303)


@router.post("/trip/{trip_id}/delete")
def trip_delete(
    trip_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        delete_trip(db, trip_id=trip_id, requester_id=user.id)
        db.commit()
    except TripNotFound as exc:
        raise NotFound(str(exc)) from exc
    except TripForbidden as exc:
        raise Forbidden(str(exc)) from exc
    return RedirectResponse(url="/trip", status_code=303)


@router.post("/trip/{trip_id}/media")
def trip_attach_media(
    trip_id: int,
    payload: AttachMediaRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        attach_media(
            db, trip_id=trip_id, requester_id=user.id,
            media_id=payload.media_id, caption=payload.caption,
        )
        db.commit()
    except TripNotFound as exc:
        raise NotFound(str(exc)) from exc
    except TripForbidden as exc:
        raise Forbidden(str(exc)) from exc
    return {"status": "ok"}


@router.post("/trip/{trip_id}/media/{media_id}/delete")
def trip_detach_media(
    trip_id: int,
    media_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        detach_media(
            db, trip_id=trip_id, requester_id=user.id, media_id=media_id,
        )
        db.commit()
    except TripNotFound as exc:
        raise NotFound(str(exc)) from exc
    except TripForbidden as exc:
        raise Forbidden(str(exc)) from exc
    return RedirectResponse(url=f"/trip/{trip_id}/edit", status_code=303)


@router.post("/trip/{trip_id}/cover/{media_id}")
def trip_set_cover(
    trip_id: int,
    media_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        set_cover(db, trip_id=trip_id, requester_id=user.id, media_id=media_id)
        db.commit()
    except TripNotFound as exc:
        raise NotFound(str(exc)) from exc
    except TripForbidden as exc:
        raise Forbidden(str(exc)) from exc
    return RedirectResponse(url=f"/trip/{trip_id}/edit", status_code=303)
