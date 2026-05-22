"""Daily log domain service: get_or_create_entry, toggle_tag, list_tags_for_day, set_notes."""
from datetime import date as date_t

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.daily_log.catalog import category_of, is_valid_tag
from app.modules.daily_log.models import DailyEntry, DailyTag


class UnknownTagError(Exception):
    """Raised when a tag_key is not in the catalog."""


def get_or_create_entry(
    db: Session, *, user_id: int, date: date_t,
) -> DailyEntry:
    """Return existing entry for (user_id, date) or create one."""
    existing = db.execute(
        select(DailyEntry).where(
            DailyEntry.user_id == user_id, DailyEntry.date == date,
        ),
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    entry = DailyEntry(user_id=user_id, date=date)
    db.add(entry)
    db.flush()
    return entry


def toggle_tag(
    db: Session, *, user_id: int, date: date_t, tag_key: str,
    value: str | None = None,
) -> tuple[DailyEntry, bool]:
    """Activate (insert) or deactivate (delete) the given tag for the day.

    Returns (entry, active_now). UnknownTagError if tag_key not in catalog.
    """
    if not is_valid_tag(tag_key):
        raise UnknownTagError(f"unknown tag_key: {tag_key!r}")

    category = category_of(tag_key)
    entry = get_or_create_entry(db, user_id=user_id, date=date)
    existing = db.execute(
        select(DailyTag).where(
            DailyTag.entry_id == entry.id,
            DailyTag.category == category,
            DailyTag.tag_key == tag_key,
        ),
    ).scalar_one_or_none()

    if existing is not None:
        db.delete(existing)
        return entry, False

    db.add(DailyTag(
        entry_id=entry.id, category=category, tag_key=tag_key, value=value,
    ))
    return entry, True


def list_tags_for_day(
    db: Session, *, user_id: int, date: date_t,
) -> list[DailyTag]:
    """All active tags for the user's day. Empty list if no entry."""
    entry = db.execute(
        select(DailyEntry).where(
            DailyEntry.user_id == user_id, DailyEntry.date == date,
        ),
    ).scalar_one_or_none()
    if entry is None:
        return []
    return list(db.execute(
        select(DailyTag)
        .where(DailyTag.entry_id == entry.id)
        .order_by(DailyTag.category, DailyTag.tag_key),
    ).scalars().all())


def set_notes(
    db: Session, *, user_id: int, date: date_t, notes: str,
) -> DailyEntry:
    """Update or create the entry with the given notes."""
    entry = get_or_create_entry(db, user_id=user_id, date=date)
    entry.notes = notes
    return entry
