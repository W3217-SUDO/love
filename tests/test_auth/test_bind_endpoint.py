from sqlalchemy import delete

from app.modules.auth.invite import create_couple_and_invites
from app.modules.auth.models import Couple, InviteToken, User


def _seed(db):
    """Wipe + seed via the invite service. Returns (he_token, she_token)."""
    db.execute(delete(InviteToken))
    db.execute(delete(Couple))
    db.execute(delete(User))
    db.flush()
    he_tok, she_tok = create_couple_and_invites(db, he_name="Alice", she_name="Bob")
    db.flush()
    return he_tok, she_tok


def test_get_bind_valid_token_returns_user_info(client, db):
    he_tok, _ = _seed(db)
    r = client.get(f"/bind?token={he_tok}")
    assert r.status_code == 200
    body = r.json()
    assert body["token"] == he_tok
    assert body["username"] == "alice"
    assert body["role"] == "he"
    assert body["display_name"] == "Alice"


def test_get_bind_unknown_token_404(client, db):
    _seed(db)
    r = client.get("/bind?token=nonexistent")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_post_bind_sets_password_and_returns_user(client, db):
    he_tok, _ = _seed(db)
    r = client.post("/bind", json={"token": he_tok, "password": "strongpassword"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["user"]["username"] == "alice"
    assert body["user"]["role"] == "he"
    # Token should now be consumed
    r2 = client.get(f"/bind?token={he_tok}")
    assert r2.status_code == 409  # already used


def test_post_bind_already_used_409(client, db):
    he_tok, _ = _seed(db)
    r1 = client.post("/bind", json={"token": he_tok, "password": "strongpassword"})
    assert r1.status_code == 200
    r2 = client.post("/bind", json={"token": he_tok, "password": "differentpassword"})
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "already_used"


def test_post_bind_short_password_422(client, db):
    he_tok, _ = _seed(db)
    r = client.post("/bind", json={"token": he_tok, "password": "short"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_failed"


def test_post_bind_unknown_token_404(client, db):
    _seed(db)
    r = client.post("/bind", json={"token": "nope", "password": "longenough"})
    assert r.status_code == 404
