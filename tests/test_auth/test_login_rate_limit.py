"""Login rate limit: 20 attempts per 5 min per IP."""
import pytest
from sqlalchemy import delete

from app.modules.auth.invite import create_couple_and_invites, redeem_invite
from app.modules.auth.models import AuthSession, Couple, InviteToken, User


def _seed_bound(db):
    db.execute(delete(AuthSession))
    db.execute(delete(InviteToken))
    db.execute(delete(Couple))
    db.execute(delete(User))
    db.flush()
    he_tok, _ = create_couple_and_invites(db, he_name="Alice", she_name="Bob")
    db.flush()
    redeem_invite(db, token=he_tok, plain_password="strongpassword")
    db.flush()


@pytest.fixture(autouse=True)
def _reset_limiter():
    """Each test in this file starts with a fresh rate limit counter."""
    from app.rate_limit import limiter
    limiter.reset()
    yield
    limiter.reset()


def test_login_rate_limit_kicks_in_after_n_attempts(client, db):
    """The 21st attempt within the window should get 429."""
    _seed_bound(db)
    # Hit /login 20 times with wrong password - all should return 401, not 429
    for _ in range(20):
        r = client.post("/login", json={"username": "alice", "password": "wrong"})
        assert r.status_code == 401, f"unexpected status: {r.status_code}"
    # 21st call should be rate limited
    r = client.post("/login", json={"username": "alice", "password": "wrong"})
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "rate_limited"


def test_correct_password_within_limit_succeeds(client, db):
    _seed_bound(db)
    # Burn 10 wrong attempts
    for _ in range(10):
        r = client.post("/login", json={"username": "alice", "password": "wrong"})
        assert r.status_code == 401
    # 11th call with correct password should succeed
    r = client.post("/login", json={"username": "alice", "password": "strongpassword"})
    assert r.status_code == 200
