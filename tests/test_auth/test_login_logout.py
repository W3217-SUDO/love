from sqlalchemy import delete

from app.modules.auth.invite import create_couple_and_invites, redeem_invite
from app.modules.auth.models import AuthSession, Couple, InviteToken, User


def _seed_bound(db, password="strongpassword"):
    """Create couple, redeem one token so 'alice' has a password set."""
    db.execute(delete(AuthSession))
    db.execute(delete(InviteToken))
    db.execute(delete(Couple))
    db.execute(delete(User))
    db.flush()
    he_tok, _she_tok = create_couple_and_invites(db, he_name="Alice", she_name="Bob")
    db.flush()
    redeem_invite(db, token=he_tok, plain_password=password)
    db.flush()


def test_login_with_correct_credentials_sets_cookie(client, db):
    _seed_bound(db, password="strongpassword")
    r = client.post("/login", json={"username": "alice", "password": "strongpassword"})
    assert r.status_code == 200
    assert "cdsid" in r.cookies
    body = r.json()
    assert body["user"]["username"] == "alice"


def test_login_with_wrong_password_401(client, db):
    _seed_bound(db, password="strongpassword")
    r = client.post("/login", json={"username": "alice", "password": "wrongpassword"})
    assert r.status_code == 401
    assert "cdsid" not in r.cookies


def test_login_with_unknown_username_401(client, db):
    _seed_bound(db, password="strongpassword")
    r = client.post("/login", json={"username": "ghost", "password": "anypassword"})
    assert r.status_code == 401


def test_login_with_unbound_user_401(client, db):
    """User has no password_hash yet - login must fail (don't leak existence)."""
    from app.modules.auth.invite import create_couple_and_invites
    db.execute(delete(AuthSession))
    db.execute(delete(InviteToken))
    db.execute(delete(Couple))
    db.execute(delete(User))
    db.flush()
    create_couple_and_invites(db, he_name="Alice", she_name="Bob")
    db.flush()
    # alice has not redeemed her invite yet
    r = client.post("/login", json={"username": "alice", "password": "anypassword"})
    assert r.status_code == 401


def test_logout_clears_cookie(client, db):
    _seed_bound(db, password="strongpassword")
    r = client.post("/login", json={"username": "alice", "password": "strongpassword"})
    assert r.status_code == 200
    token = r.cookies["cdsid"]
    # Logout (the test client carries the cookie automatically)
    r2 = client.post("/logout")
    assert r2.status_code == 204
    # Cookie should be cleared (Max-Age=0 or expires past)
    set_cookie = r2.headers.get("set-cookie", "")
    assert "cdsid=" in set_cookie
    # Session row should be gone
    assert db.query(AuthSession).filter_by(token=token).count() == 0


def test_logout_without_session_204(client, db):
    """Logging out when not logged in is a no-op."""
    db.execute(delete(AuthSession))
    db.flush()
    r = client.post("/logout")
    assert r.status_code == 204
