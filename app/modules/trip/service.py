"""Trip CRUD service. Trips are always shared between bonded partners."""
from datetime import date as date_t

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.auth.models import Couple
from app.modules.media.models import Media
from app.modules.trip.models import Trip, TripMedia


class TripError(Exception):
    pass


class TripNotFound(TripError):
    pass


class TripForbidden(TripError):
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


def _is_partner_or_self(db: Session, owner_id: int, requester_id: int) -> bool:
    if owner_id == requester_id:
        return True
    return _partner_of(db, owner_id) == requester_id


def create_trip(
    db: Session, *, creator_id: int, title: str,
    location: str | None = None,
    start_date: date_t | None = None,
    end_date: date_t | None = None,
    description: str | None = None,
) -> Trip:
    if not title or not title.strip():
        raise ValueError("title cannot be empty")
    if end_date is not None and start_date is not None and end_date < start_date:
        raise ValueError("end_date must be >= start_date")
    t = Trip(
        title=title.strip(),
        location=(location or "").strip() or None,
        start_date=start_date or date_t.today(),
        end_date=end_date,
        description=description,
        created_by_id=creator_id,
    )
    db.add(t)
    db.flush()
    return t


def get_trip(db: Session, *, trip_id: int, requester_id: int) -> Trip:
    t = db.execute(
        select(Trip).where(Trip.id == trip_id),
    ).scalar_one_or_none()
    if t is None:
        raise TripNotFound(f"trip {trip_id} not found")
    if not _is_partner_or_self(db, t.created_by_id, requester_id):
        raise TripForbidden("not a partner of this trip's creator")
    return t


def update_trip(
    db: Session, *, trip_id: int, requester_id: int,
    title: str | None = None, location: str | None = None,
    start_date: date_t | None = None, end_date: date_t | None = None,
    description: str | None = None, cover_media_id: int | None = None,
) -> Trip:
    t = get_trip(db, trip_id=trip_id, requester_id=requester_id)
    if title is not None:
        if not title.strip():
            raise ValueError("title cannot be empty")
        t.title = title.strip()
    if location is not None:
        t.location = location.strip() or None
    if start_date is not None:
        t.start_date = start_date
    if end_date is not None:
        t.end_date = end_date
    if description is not None:
        t.description = description
    if cover_media_id is not None:
        t.cover_media_id = cover_media_id
    if (t.start_date is not None and t.end_date is not None
            and t.end_date < t.start_date):
        raise ValueError("end_date must be >= start_date")
    return t


def delete_trip(db: Session, *, trip_id: int, requester_id: int) -> None:
    t = db.execute(
        select(Trip).where(Trip.id == trip_id),
    ).scalar_one_or_none()
    if t is None:
        raise TripNotFound(f"trip {trip_id} not found")
    if t.created_by_id != requester_id:
        raise TripForbidden("only the creator may delete this trip")
    db.delete(t)


def list_trips(
    db: Session, *, requester_id: int, limit: int = 20, offset: int = 0,
) -> list[Trip]:
    partner_id = _partner_of(db, requester_id)
    if partner_id is not None:
        ids = [requester_id, partner_id]
    else:
        ids = [requester_id]
    rows = db.execute(
        select(Trip)
        .where(Trip.created_by_id.in_(ids))
        .order_by(Trip.start_date.desc(), Trip.created_at.desc())
        .limit(limit).offset(offset),
    ).scalars().all()
    return list(rows)


def attach_media(
    db: Session, *, trip_id: int, requester_id: int, media_id: int,
    sort_order: int | None = None, caption: str | None = None,
) -> TripMedia:
    get_trip(db, trip_id=trip_id, requester_id=requester_id)
    media = db.execute(
        select(Media).where(Media.id == media_id),
    ).scalar_one_or_none()
    if media is None:
        raise TripNotFound(f"media {media_id} not found")
    # Either partner can attach their own media to the shared trip
    if not _is_partner_or_self(db, media.owner_id, requester_id):
        raise TripForbidden("media owner mismatch")
    if sort_order is None:
        existing = db.execute(
            select(TripMedia).where(TripMedia.trip_id == trip_id),
        ).scalars().all()
        sort_order = (max((tm.sort_order for tm in existing), default=-1)) + 1
    link = TripMedia(
        trip_id=trip_id, media_id=media_id,
        sort_order=sort_order, caption=caption,
    )
    db.add(link)
    return link


def detach_media(
    db: Session, *, trip_id: int, requester_id: int, media_id: int,
) -> None:
    t = get_trip(db, trip_id=trip_id, requester_id=requester_id)
    link = db.execute(
        select(TripMedia).where(
            TripMedia.trip_id == trip_id,
            TripMedia.media_id == media_id,
        ),
    ).scalar_one_or_none()
    if link is not None:
        db.delete(link)
    # Also clear cover if it pointed here
    if t.cover_media_id == media_id:
        t.cover_media_id = None


def list_media(
    db: Session, *, trip_id: int, requester_id: int,
) -> list[tuple[TripMedia, Media]]:
    get_trip(db, trip_id=trip_id, requester_id=requester_id)
    rows = db.execute(
        select(TripMedia, Media)
        .join(Media, Media.id == TripMedia.media_id)
        .where(TripMedia.trip_id == trip_id)
        .order_by(TripMedia.sort_order, Media.id),
    ).all()
    return [(tm, m) for tm, m in rows]


def set_cover(
    db: Session, *, trip_id: int, requester_id: int, media_id: int,
) -> Trip:
    t = get_trip(db, trip_id=trip_id, requester_id=requester_id)
    # Verify the media is attached to this trip
    link = db.execute(
        select(TripMedia).where(
            TripMedia.trip_id == trip_id, TripMedia.media_id == media_id,
        ),
    ).scalar_one_or_none()
    if link is None:
        raise TripNotFound(f"media {media_id} not attached to trip {trip_id}")
    t.cover_media_id = media_id
    return t
