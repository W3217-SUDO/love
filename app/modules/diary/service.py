"""Diary CRUD service with visibility guards."""
from datetime import date as date_t

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.auth.models import Couple
from app.modules.diary.models import DiaryEntry, DiaryMedia
from app.modules.media.models import Media


class DiaryError(Exception):
    pass


class DiaryNotFound(DiaryError):
    pass


class DiaryForbidden(DiaryError):
    pass


def _partner_of(db: Session, user_id: int) -> int | None:
    c = db.execute(
        select(Couple).where(
            or_(Couple.user_a_id == user_id, Couple.user_b_id == user_id),
        ),
    ).scalar_one_or_none()
    if c is None:
        return None
    return c.user_b_id if c.user_a_id == user_id else c.user_a_id


def create_entry(
    db: Session, *, author_id: int, body: str,
    title: str | None = None, date: date_t | None = None,
    visibility: str = "shared",
) -> DiaryEntry:
    if visibility not in ("private", "shared"):
        raise ValueError(f"invalid visibility: {visibility!r}")
    if not body or not body.strip():
        raise ValueError("body cannot be empty")
    entry = DiaryEntry(
        author_id=author_id,
        date=date or date_t.today(),
        title=title,
        body=body,
        visibility=visibility,
    )
    db.add(entry)
    db.flush()
    return entry


def get_entry(db: Session, *, entry_id: int, requester_id: int) -> DiaryEntry:
    e = db.execute(
        select(DiaryEntry).where(DiaryEntry.id == entry_id),
    ).scalar_one_or_none()
    if e is None:
        raise DiaryNotFound(f"diary entry {entry_id} not found")
    if e.author_id == requester_id:
        return e
    if e.visibility == "shared":
        partner = _partner_of(db, e.author_id)
        if partner == requester_id:
            return e
    raise DiaryForbidden("you do not have access to this entry")


def update_entry(
    db: Session, *, entry_id: int, requester_id: int,
    title: str | None = None, body: str | None = None,
    visibility: str | None = None,
) -> DiaryEntry:
    e = db.execute(
        select(DiaryEntry).where(DiaryEntry.id == entry_id),
    ).scalar_one_or_none()
    if e is None:
        raise DiaryNotFound(f"diary entry {entry_id} not found")
    if e.author_id != requester_id:
        raise DiaryForbidden("only the author may edit this entry")
    if title is not None:
        e.title = title
    if body is not None:
        if not body.strip():
            raise ValueError("body cannot be empty")
        e.body = body
    if visibility is not None:
        if visibility not in ("private", "shared"):
            raise ValueError(f"invalid visibility: {visibility!r}")
        e.visibility = visibility
    return e


def delete_entry(db: Session, *, entry_id: int, requester_id: int) -> None:
    e = db.execute(
        select(DiaryEntry).where(DiaryEntry.id == entry_id),
    ).scalar_one_or_none()
    if e is None:
        raise DiaryNotFound(f"diary entry {entry_id} not found")
    if e.author_id != requester_id:
        raise DiaryForbidden("only the author may delete this entry")
    db.delete(e)


def list_visible_entries(
    db: Session, *, requester_id: int, limit: int = 20, offset: int = 0,
) -> list[DiaryEntry]:
    partner_id = _partner_of(db, requester_id)
    if partner_id is not None:
        # Own (any visibility) + partner's shared
        stmt = (
            select(DiaryEntry)
            .where(or_(
                DiaryEntry.author_id == requester_id,
                ((DiaryEntry.author_id == partner_id)
                 & (DiaryEntry.visibility == "shared")),
            ))
            .order_by(DiaryEntry.date.desc(), DiaryEntry.created_at.desc())
            .limit(limit).offset(offset)
        )
    else:
        stmt = (
            select(DiaryEntry)
            .where(DiaryEntry.author_id == requester_id)
            .order_by(DiaryEntry.date.desc(), DiaryEntry.created_at.desc())
            .limit(limit).offset(offset)
        )
    return list(db.execute(stmt).scalars().all())


def attach_media(
    db: Session, *, entry_id: int, requester_id: int, media_id: int,
    sort_order: int | None = None, caption: str | None = None,
) -> DiaryMedia:
    e = db.execute(
        select(DiaryEntry).where(DiaryEntry.id == entry_id),
    ).scalar_one_or_none()
    if e is None:
        raise DiaryNotFound(f"diary entry {entry_id} not found")
    if e.author_id != requester_id:
        raise DiaryForbidden("only the author may attach media")
    media = db.execute(
        select(Media).where(Media.id == media_id),
    ).scalar_one_or_none()
    if media is None:
        raise DiaryNotFound(f"media {media_id} not found")
    if media.owner_id != requester_id:
        raise DiaryForbidden("media owner mismatch")
    # Compute sort_order if not given
    if sort_order is None:
        existing = db.execute(
            select(DiaryMedia).where(DiaryMedia.diary_id == entry_id),
        ).scalars().all()
        sort_order = (max((dm.sort_order for dm in existing), default=-1)) + 1
    link = DiaryMedia(
        diary_id=entry_id, media_id=media_id,
        sort_order=sort_order, caption=caption,
    )
    db.add(link)
    return link


def detach_media(
    db: Session, *, entry_id: int, requester_id: int, media_id: int,
) -> None:
    e = db.execute(
        select(DiaryEntry).where(DiaryEntry.id == entry_id),
    ).scalar_one_or_none()
    if e is None:
        raise DiaryNotFound(f"diary entry {entry_id} not found")
    if e.author_id != requester_id:
        raise DiaryForbidden("only the author may detach media")
    link = db.execute(
        select(DiaryMedia).where(
            DiaryMedia.diary_id == entry_id,
            DiaryMedia.media_id == media_id,
        ),
    ).scalar_one_or_none()
    if link is not None:
        db.delete(link)


def list_media(
    db: Session, *, entry_id: int, requester_id: int,
) -> list[tuple[DiaryMedia, Media]]:
    # Use get_entry for visibility check
    get_entry(db, entry_id=entry_id, requester_id=requester_id)
    rows = db.execute(
        select(DiaryMedia, Media)
        .join(Media, Media.id == DiaryMedia.media_id)
        .where(DiaryMedia.diary_id == entry_id)
        .order_by(DiaryMedia.sort_order, Media.id),
    ).all()
    return [(dm, m) for dm, m in rows]
