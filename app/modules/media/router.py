"""Media HTTP endpoints: upload + serve with cookie OR signed-URL auth."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Cookie, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import AppError, FileTooLarge, NotFound, ValidationFailed
from app.modules.auth.models import User
from app.modules.auth.sessions import lookup_session
from app.modules.media.pipeline import (
    FileTooLargeError,
    PipelineError,
    UnsupportedMimeError,
    process_upload,
)
from app.modules.media.schemas import MediaOut
from app.modules.media.service import get_media, is_owner_or_partner
from app.modules.media.signing import (
    InvalidSignature,
    sign_media_url,
    verify_media_url,
)

router = APIRouter(tags=["media"])


def _to_out(media) -> MediaOut:
    out = MediaOut.model_validate(media)
    out.thumb_url = f"/media/{media.id}/thumb?{sign_media_url(media.id)}"
    out.preview_url = f"/media/{media.id}/preview?{sign_media_url(media.id)}"
    return out


@router.post("/media/upload", response_model=MediaOut)
async def post_upload(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MediaOut:
    payload = await file.read()
    try:
        media = process_upload(
            db, owner_id=user.id,
            filename=file.filename or "untitled",
            mime=file.content_type or "application/octet-stream",
            payload=payload,
        )
        db.commit()
    except UnsupportedMimeError as exc:
        raise ValidationFailed(str(exc)) from exc
    except FileTooLargeError as exc:
        raise FileTooLarge(str(exc)) from exc
    except PipelineError as exc:
        raise ValidationFailed(str(exc)) from exc
    return _to_out(media)


def _serve_file(
    request: Request,
    media_id: int,
    db: Session,
    cdsid: str | None,
    which: str,  # "original" | "thumb" | "preview"
) -> FileResponse:
    media = get_media(db, media_id)
    if media is None:
        raise NotFound("media not found")
    # If a signature is present, it must be valid (no falling through to cookie).
    qs = str(request.url.query)
    if "s=" in qs:
        try:
            mid = verify_media_url(qs)
            if mid != media.id:
                raise NotFound("media not found")
        except InvalidSignature as exc:
            raise AppError(
                "invalid or expired signed URL", code="invalid_signature",
                http_status=403,
            ) from exc
    else:
        # No signature → must have a cookie session AND be owner/partner.
        if not cdsid:
            raise AppError(
                "authentication required", code="not_authenticated",
                http_status=401,
            )
        try:
            user = lookup_session(db, token=cdsid)
        except Exception as exc:
            raise AppError(
                "authentication required", code="not_authenticated",
                http_status=401,
            ) from exc
        if not is_owner_or_partner(db, media=media, user_id=user.id):
            raise AppError("forbidden", code="forbidden", http_status=403)

    paths = {
        "original": media.original_path,
        "thumb": media.thumb_path,
        "preview": media.preview_path,
    }
    path = paths[which]
    if not path or not Path(path).is_file():
        raise NotFound("file missing on disk")
    # All derivatives are WebP; original is also stored as WebP (lossless conv).
    return FileResponse(
        path,
        media_type="image/webp",
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.get("/media/{media_id}")
def get_media_original(
    media_id: int,
    request: Request,
    db: Session = Depends(get_db),
    cdsid: str | None = Cookie(default=None),
) -> FileResponse:
    return _serve_file(request, media_id, db, cdsid, which="original")


@router.get("/media/{media_id}/thumb")
def get_media_thumb(
    media_id: int,
    request: Request,
    db: Session = Depends(get_db),
    cdsid: str | None = Cookie(default=None),
) -> FileResponse:
    return _serve_file(request, media_id, db, cdsid, which="thumb")


@router.get("/media/{media_id}/preview")
def get_media_preview(
    media_id: int,
    request: Request,
    db: Session = Depends(get_db),
    cdsid: str | None = Cookie(default=None),
) -> FileResponse:
    return _serve_file(request, media_id, db, cdsid, which="preview")
