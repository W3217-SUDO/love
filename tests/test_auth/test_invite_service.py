from datetime import datetime, timedelta, timezone

import pytest

from app.modules.auth.invite import (
    InviteAlreadyUsed,
    InviteExpired,
    InviteNotFound,
    create_couple_and_invites,
    redeem_invite,
)
from app.modules.auth.models import Couple, InviteToken, User


def test_create_couple_and_invites_creates_users_and_tokens(db):
    he_token, she_token = create_couple_and_invites(
        db, he_name="Alice", she_name="Bob"
    )
    db.flush()
    users = db.query(User).order_by(User.role).all()
    assert len(users) == 2
    roles = {u.role for u in users}
    assert roles == {"he", "she"}
    tokens = db.query(InviteToken).all()
    assert len(tokens) == 2
    assert he_token != she_token
    assert all(len(t) >= 32 for t in (he_token, she_token))
    couple = db.query(Couple).one()
    assert couple.bonded_at is None


def test_create_couple_refuses_if_users_already_exist(db):
    create_couple_and_invites(db, he_name="A", she_name="B")
    db.flush()
    with pytest.raises(RuntimeError, match="already exists"):
        create_couple_and_invites(db, he_name="C", she_name="D")


def test_redeem_invite_sets_password_and_marks_used(db):
    he_token, _ = create_couple_and_invites(db, he_name="X", she_name="Y")
    db.flush()
    user = redeem_invite(db, token=he_token, plain_password="strongpassword")
    db.flush()
    assert user.password_hash is not None
    assert user.password_hash.startswith("$argon2id$")
    tok = db.query(InviteToken).filter_by(token=he_token).one()
    assert tok.used_at is not None


def test_redeem_invite_unknown_token_raises(db):
    with pytest.raises(InviteNotFound):
        redeem_invite(db, token="nonexistent", plain_password="strongpassword")


def test_redeem_invite_used_token_raises(db):
    he_token, _ = create_couple_and_invites(db, he_name="X", she_name="Y")
    db.flush()
    redeem_invite(db, token=he_token, plain_password="strongpassword")
    db.flush()
    with pytest.raises(InviteAlreadyUsed):
        redeem_invite(db, token=he_token, plain_password="otherpassword")


def test_redeem_invite_expired_token_raises(db):
    he_token, _ = create_couple_and_invites(db, he_name="X", she_name="Y")
    db.flush()
    tok = db.query(InviteToken).filter_by(token=he_token).one()
    tok.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db.flush()
    with pytest.raises(InviteExpired):
        redeem_invite(db, token=he_token, plain_password="strongpassword")
