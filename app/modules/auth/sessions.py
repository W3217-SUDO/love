"""Server-side session store: create/lookup/revoke/touch."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.modules.auth.models import AuthSession, User

TOKEN_BYTES = 32  # -> ~43-char base64-urlsafe


class SessionError(Exception):
    pass


class SessionNotFound(SessionError):
    pass


class SessionExpired(SessionError):
    pass


def _now_naive_utc() -> datetime:
    # DB stores naive UTC; keep all internal math aware then strip tzinfo on write.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_session(
    db: Session,
    *,
    user_id: int,
    ip: str | None,
    user_agent: str | None,
) -> str:
    """Create a new session row and return its token."""
    settings = get_settings()
    token = secrets.token_urlsafe(TOKEN_BYTES)
    now = _now_naive_utc()
    expires_at = now + timedelta(days=settings.session_max_age_days)
    db.add(AuthSession(
        token=token, user_id=user_id, ip=ip, user_agent=user_agent,
        expires_at=expires_at,
        created_at=now, last_seen_at=now,
    ))
    return token


def lookup_session(db: Session, *, token: str) -> User:
    """Return the User for an active session token. Raises on missing/expired."""
    row = db.query(AuthSession).filter_by(token=token).one_or_none()
    if row is None:
        raise SessionNotFound("session not found")
    expires_at = row.expires_at
    if expires_at.tzinfo is not None:
        expires_at = expires_at.replace(tzinfo=None)
    if expires_at < _now_naive_utc():
        raise SessionExpired("session has expired")
    user = db.query(User).filter_by(id=row.user_id).one()
    return user


def revoke_session(db: Session, *, token: str) -> None:
    """Delete the session row (no-op if it doesn't exist)."""
    row = db.query(AuthSession).filter_by(token=token).one_or_none()
    if row is not None:
        db.delete(row)


def touch_session(db: Session, *, token: str) -> None:
    """Update last_seen_at and sliding-extend expires_at if within last 7 days of expiry."""
    settings = get_settings()
    row = db.query(AuthSession).filter_by(token=token).one_or_none()
    if row is None:
        return
    now = _now_naive_utc()
    row.last_seen_at = now
    # Sliding renewal: if expiry is within 7 days, push out to max again.
    if (row.expires_at - now) < timedelta(days=7):
        row.expires_at = now + timedelta(days=settings.session_max_age_days)
