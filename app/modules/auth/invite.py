"""Invite token issuance and redemption for the closed 2-person bind flow."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.modules.auth.models import Couple, InviteToken, User
from app.modules.auth.passwords import hash_password

TOKEN_TTL = timedelta(days=7)
TOKEN_BYTES = 32  # → ~43-char base64-urlsafe string


class InviteError(Exception):
    """Base class for invite-related errors."""


class InviteNotFound(InviteError):
    pass


class InviteAlreadyUsed(InviteError):
    pass


class InviteExpired(InviteError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_couple_and_invites(
    db: Session, *, he_name: str, she_name: str,
) -> tuple[str, str]:
    """Create the 2 User rows, the Couple row, and 2 InviteToken rows.

    Refuses if any User or Couple row already exists (system is closed and
    only one bonding is allowed).

    Returns (he_token, she_token).
    """
    existing_users = db.query(User).count()
    existing_couples = db.query(Couple).count()
    if existing_users or existing_couples:
        raise RuntimeError(
            "couple already exists — cannot init twice; "
            "wipe users/couples/invite_tokens first if you really mean it"
        )

    he = User(username=he_name.lower(), display_name=he_name, role="he")
    she = User(username=she_name.lower(), display_name=she_name, role="she")
    db.add_all([he, she])
    db.flush()  # populate IDs

    couple = Couple(user_a_id=he.id, user_b_id=she.id)
    db.add(couple)

    he_token = secrets.token_urlsafe(TOKEN_BYTES)
    she_token = secrets.token_urlsafe(TOKEN_BYTES)
    expires = _now() + TOKEN_TTL
    db.add_all([
        InviteToken(token=he_token, user_id=he.id, expires_at=expires),
        InviteToken(token=she_token, user_id=she.id, expires_at=expires),
    ])

    return he_token, she_token


def redeem_invite(
    db: Session, *, token: str, plain_password: str,
) -> User:
    """Set the user's password from an unused, unexpired invite token.

    Marks the token as used. Returns the User.
    """
    row = db.query(InviteToken).filter_by(token=token).one_or_none()
    if row is None:
        raise InviteNotFound("invite token does not exist")
    if row.used_at is not None:
        raise InviteAlreadyUsed("invite token has already been used")
    # Compare both as aware UTC (DB stores naive UTC; treat as UTC).
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < _now():
        raise InviteExpired("invite token has expired")

    user = db.query(User).filter_by(id=row.user_id).one()
    user.password_hash = hash_password(plain_password)
    row.used_at = _now().replace(tzinfo=None)  # DB column is naive

    return user
