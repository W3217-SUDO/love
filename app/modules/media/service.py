"""Small read helpers for the media module."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.models import Couple
from app.modules.media.models import Media


def get_media(db: Session, media_id: int) -> Media | None:
    return db.execute(
        select(Media).where(Media.id == media_id),
    ).scalar_one_or_none()


def is_owner_or_partner(db: Session, *, media: Media, user_id: int) -> bool:
    if media.owner_id == user_id:
        return True
    # Look up couple
    c = db.execute(
        select(Couple).where(
            ((Couple.user_a_id == user_id) & (Couple.user_b_id == media.owner_id))
            | ((Couple.user_b_id == user_id) & (Couple.user_a_id == media.owner_id))
        ),
    ).scalar_one_or_none()
    return c is not None
