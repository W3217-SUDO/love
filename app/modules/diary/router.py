"""Diary HTTP endpoints — HTML pages and JSON API."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import Forbidden, NotFound
from app.modules.auth.models import User
from app.modules.diary.schemas import AttachMediaRequest, DiaryEntryOut
from app.modules.diary.service import (
    DiaryForbidden,
    DiaryNotFound,
    attach_media,
    create_entry,
    delete_entry,
    detach_media,
    get_entry,
    list_media,
    list_visible_entries,
    update_entry,
)
from app.modules.media.signing import sign_media_url
from app.templating import templates
from app.util.http import wants_html


router = APIRouter(tags=["diary"])


def _author_name(db: Session, author_id: int) -> str:
    u = db.execute(
        select(User).where(User.id == author_id),
    ).scalar_one_or_none()
    return u.display_name if u else "?"


@router.get("/diary")
def diary_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    entries_raw = list_visible_entries(db, requester_id=user.id)
    entries = []
    for e in entries_raw:
        entries.append({
            "id": e.id,
            "title": e.title,
            "date": e.date,
            "body_excerpt": (e.body[:200] + "…") if len(e.body) > 200 else e.body,
            "visibility": e.visibility,
            "author_name": _author_name(db, e.author_id),
            "cover_thumb_url": None,  # could query first media; deferred
        })
    if wants_html(request):
        return templates.TemplateResponse(
            request=request, name="pages/diary_list.html",
            context={"entries": entries},
        )
    return [DiaryEntryOut.model_validate(e).model_dump(mode="json") for e in entries_raw]


@router.get("/diary/new")
def diary_new(
    request: Request,
    user: User = Depends(get_current_user),
):
    return templates.TemplateResponse(
        request=request, name="pages/diary_edit.html",
        context={"entry": None, "media_list": []},
    )


@router.get("/diary/{entry_id}")
def diary_detail(
    entry_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        e = get_entry(db, entry_id=entry_id, requester_id=user.id)
    except DiaryNotFound as exc:
        raise NotFound(str(exc)) from exc
    except DiaryForbidden as exc:
        raise Forbidden(str(exc)) from exc

    media_pairs = list_media(db, entry_id=entry_id, requester_id=user.id)
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
        request=request, name="pages/diary_detail.html",
        context={
            "entry": e, "media_list": media_list,
            "author_name": _author_name(db, e.author_id),
            "is_author": e.author_id == user.id,
        },
    )


@router.get("/diary/{entry_id}/edit")
def diary_edit_get(
    entry_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        e = get_entry(db, entry_id=entry_id, requester_id=user.id)
    except DiaryNotFound as exc:
        raise NotFound(str(exc)) from exc
    if e.author_id != user.id:
        raise Forbidden("only the author may edit")
    media_pairs = list_media(db, entry_id=entry_id, requester_id=user.id)
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
        request=request, name="pages/diary_edit.html",
        context={"entry": e, "media_list": media_list},
    )


@router.post("/diary")
async def diary_create(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    form = await request.form()
    body = form.get("body", "")
    title = form.get("title") or None
    visibility = form.get("visibility", "shared")
    try:
        e = create_entry(
            db, author_id=user.id, body=body,
            title=title, visibility=visibility,
        )
        db.commit()
    except ValueError as exc:
        from app.errors import ValidationFailed
        raise ValidationFailed(str(exc)) from exc
    return RedirectResponse(url=f"/diary/{e.id}", status_code=303)


@router.post("/diary/{entry_id}")
async def diary_update(
    entry_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    form = await request.form()
    body = form.get("body") or None
    title = form.get("title") or None
    visibility = form.get("visibility") or None
    try:
        e = update_entry(
            db, entry_id=entry_id, requester_id=user.id,
            title=title, body=body, visibility=visibility,
        )
        db.commit()
    except DiaryNotFound as exc:
        raise NotFound(str(exc)) from exc
    except DiaryForbidden as exc:
        raise Forbidden(str(exc)) from exc
    except ValueError as exc:
        from app.errors import ValidationFailed
        raise ValidationFailed(str(exc)) from exc
    return RedirectResponse(url=f"/diary/{e.id}", status_code=303)


@router.post("/diary/{entry_id}/delete")
def diary_delete(
    entry_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        delete_entry(db, entry_id=entry_id, requester_id=user.id)
        db.commit()
    except DiaryNotFound as exc:
        raise NotFound(str(exc)) from exc
    except DiaryForbidden as exc:
        raise Forbidden(str(exc)) from exc
    return RedirectResponse(url="/diary", status_code=303)


@router.post("/diary/{entry_id}/media")
def diary_attach_media(
    entry_id: int,
    payload: AttachMediaRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        attach_media(
            db, entry_id=entry_id, requester_id=user.id,
            media_id=payload.media_id, caption=payload.caption,
        )
        db.commit()
    except DiaryNotFound as exc:
        raise NotFound(str(exc)) from exc
    except DiaryForbidden as exc:
        raise Forbidden(str(exc)) from exc
    return {"status": "ok"}


@router.post("/diary/{entry_id}/media/{media_id}/delete")
def diary_detach_media(
    entry_id: int,
    media_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        detach_media(
            db, entry_id=entry_id, requester_id=user.id, media_id=media_id,
        )
        db.commit()
    except DiaryNotFound as exc:
        raise NotFound(str(exc)) from exc
    except DiaryForbidden as exc:
        raise Forbidden(str(exc)) from exc
    return RedirectResponse(url=f"/diary/{entry_id}/edit", status_code=303)
