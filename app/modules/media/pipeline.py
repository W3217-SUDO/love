"""Upload pipeline: validate → dedup → store → derive thumbnails."""
from __future__ import annotations

import hashlib
import io
from datetime import datetime
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.modules.media.models import Media

MAX_SIZE_BYTES = 50 * 1024 * 1024  # Legacy fallback for older settings doubles.
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
IMAGE_FORMAT_BY_MIME = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}
PDF_MAGIC = b"%PDF-"
THUMB_MAX = (400, 400)
PREVIEW_MAX_LONG_EDGE = 1200


class PipelineError(Exception):
    """Base pipeline error."""


class UnsupportedMimeError(PipelineError):
    pass


class FileTooLargeError(PipelineError):
    pass


def _validate_pdf(payload: bytes) -> None:
    if not payload.startswith(PDF_MAGIC):
        raise PipelineError("not a valid PDF")


def _upload_limit_bytes(settings: object, *, requested_kind: str) -> int:
    if requested_kind == "pdf":
        return int(getattr(settings, "max_pdf_upload_bytes", MAX_SIZE_BYTES))
    return int(getattr(settings, "max_image_upload_bytes", MAX_SIZE_BYTES))


def _open_verified_image(*, mime: str, payload: bytes) -> Image.Image:
    try:
        probe = Image.open(io.BytesIO(payload))
        if probe.format != IMAGE_FORMAT_BY_MIME[mime]:
            raise PipelineError(f"not a valid {mime} file")
        probe.verify()  # raises on non-image / corrupt image
    except PipelineError:
        raise
    except UnidentifiedImageError as exc:
        raise PipelineError(f"not a valid image: {exc}") from exc
    except Exception as exc:  # Pillow raises a variety of exceptions
        raise PipelineError(f"not a valid image: {exc}") from exc

    return Image.open(io.BytesIO(payload))


def _exif_taken_at(img: Image.Image) -> datetime | None:
    try:
        exif = img.getexif()
        if not exif:
            return None
        # Try DateTimeOriginal (36867) then fallback DateTime (306)
        for tag_id in (36867, 306):
            val = exif.get(tag_id)
            if not val:
                continue
            for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(val, fmt)
                except ValueError:
                    continue
    except Exception:
        return None
    return None


def process_upload(
    db: Session,
    *,
    owner_id: int,
    filename: str,
    mime: str,
    payload: bytes,
) -> Media:
    """Validate, store, derive. Returns a (possibly pre-existing) Media row."""
    if mime not in ALLOWED_MIME:
        raise UnsupportedMimeError(f"mime {mime!r} not allowed")

    requested_kind = "pdf" if mime == "application/pdf" else "image"
    settings = config.get_settings()
    max_upload_bytes = _upload_limit_bytes(settings, requested_kind=requested_kind)
    if len(payload) > max_upload_bytes:
        raise FileTooLargeError(
            f"file is {len(payload)} bytes; max {max_upload_bytes}",
        )

    if requested_kind == "pdf":
        _validate_pdf(payload)
        img = None
    else:
        img = _open_verified_image(mime=mime, payload=payload)

    sha = hashlib.sha256(payload).hexdigest()

    # Dedup by (owner_id, sha256)
    existing = db.execute(
        select(Media).where(
            Media.owner_id == owner_id, Media.sha256 == sha,
        ),
    ).scalar_one_or_none()
    if existing is not None:
        if existing.kind != requested_kind or existing.mime != mime:
            raise PipelineError("content already exists with a different media type")
        return existing

    upload_dir = Path(settings.upload_dir)
    now = datetime.now()
    rel_dir = (
        Path(str(owner_id)) / f"{now.year:04d}" / f"{now.month:02d}" / sha[:2]
    )
    abs_dir = upload_dir / rel_dir
    abs_dir.mkdir(parents=True, exist_ok=True)

    if requested_kind == "pdf":
        original_path = abs_dir / f"{sha}.pdf"
        original_path.write_bytes(payload)
        row = Media(
            owner_id=owner_id, kind="pdf", sha256=sha, mime=mime,
            size_bytes=len(payload), width=None, height=None,
            original_path=str(original_path), thumb_path=None,
            preview_path=None, exif_taken_at=None,
        )
        db.add(row)
        db.flush()
        return row

    assert img is not None

    # Save original as WebP (strips EXIF naturally)
    original_path = abs_dir / f"{sha}.webp"
    img.convert("RGB").save(original_path, format="WEBP", quality=92, method=4)

    # Thumb: 400×400 max, fit inside
    thumb = img.copy()
    thumb.thumbnail(THUMB_MAX)
    thumb_path = abs_dir / f"{sha}.thumb.webp"
    thumb.convert("RGB").save(thumb_path, format="WEBP", quality=85, method=4)

    # Preview: long edge ≤ PREVIEW_MAX_LONG_EDGE
    preview = img.copy()
    long_edge = max(preview.size)
    if long_edge > PREVIEW_MAX_LONG_EDGE:
        scale = PREVIEW_MAX_LONG_EDGE / long_edge
        preview = preview.resize(
            (int(preview.size[0] * scale), int(preview.size[1] * scale)),
        )
    preview_path = abs_dir / f"{sha}.preview.webp"
    preview.convert("RGB").save(preview_path, format="WEBP", quality=88, method=4)

    taken_at = _exif_taken_at(img)
    width, height = img.size

    row = Media(
        owner_id=owner_id, kind="image", sha256=sha, mime=mime,
        size_bytes=len(payload), width=width, height=height,
        original_path=str(original_path), thumb_path=str(thumb_path),
        preview_path=str(preview_path), exif_taken_at=taken_at,
    )
    db.add(row)
    db.flush()
    return row
