from fastapi import Depends
from sqlalchemy import delete

from app.deps import get_current_user
from app.modules.auth.invite import create_couple_and_invites, redeem_invite
from app.modules.auth.models import AuthSession, Couple, InviteToken, User


def _seed_bound(db, password="strongpassword"):
    db.execute(delete(AuthSession))
    db.execute(delete(InviteToken))
    db.execute(delete(Couple))
    db.execute(delete(User))
    db.flush()
    he_tok, _ = create_couple_and_invites(db, he_name="Alice", she_name="Bob")
    db.flush()
    redeem_invite(db, token=he_tok, plain_password=password)
    db.flush()


def test_protected_route_requires_cookie(client, db):
    """Without a session, dependency must 401."""
    from app.main import app

    @app.get("/_test_me")
    def me(user: User = Depends(get_current_user)) -> dict:
        return {"id": user.id, "username": user.username}

    try:
        r = client.get("/_test_me")
        assert r.status_code == 401
    finally:
        # Strip the test route
        app.router.routes = [r for r in app.router.routes if r.path != "/_test_me"]


def test_protected_route_with_valid_cookie_returns_user(client, db):
    from app.main import app

    @app.get("/_test_me2")
    def me(user: User = Depends(get_current_user)) -> dict:
        return {"id": user.id, "username": user.username}

    try:
        _seed_bound(db, password="strongpassword")
        login = client.post("/login", json={"username": "alice", "password": "strongpassword"})
        assert login.status_code == 200
        r = client.get("/_test_me2")
        assert r.status_code == 200
        body = r.json()
        assert body["username"] == "alice"
    finally:
        app.router.routes = [r for r in app.router.routes if r.path != "/_test_me2"]
