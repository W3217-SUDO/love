"""Shared FastAPI dependencies (current user, current couple)."""
from __future__ import annotations

from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.modules.auth.models import User
from app.modules.auth.sessions import SessionError, lookup_session, touch_session


class NotAuthenticated(AppError):
    http_status = 401
    code = "not_authenticated"


def get_current_user(
    db: Session = Depends(get_db),
    cdsid: str | None = Cookie(default=None),
) -> User:
    if not cdsid:
        raise NotAuthenticated("authentication required")
    try:
        user = lookup_session(db, token=cdsid)
    except SessionError as exc:
        raise NotAuthenticated(str(exc)) from exc
    # Sliding refresh
    touch_session(db, token=cdsid)
    db.commit()
    return user
