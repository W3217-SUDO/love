from sqlalchemy import delete

from app.modules.auth.invite import create_couple_and_invites
from app.modules.auth.models import AuthSession, Couple, InviteToken, User


def _seed(db):
    db.execute(delete(AuthSession))
    db.execute(delete(InviteToken))
    db.execute(delete(Couple))
    db.execute(delete(User))
    db.flush()
    he_tok, _ = create_couple_and_invites(db, he_name="Alice", she_name="Bob")
    db.flush()
    return he_tok


def test_bind_page_html_with_token(client, db):
    tok = _seed(db)
    r = client.get(f"/bind?token={tok}", headers={"Accept": "text/html"})
    assert r.status_code == 200
    body = r.text
    assert "Alice" in body  # display_name shown
    assert tok in body  # token preserved in hidden field
    assert 'name="password"' in body
    assert "<html" in body.lower()


def test_bind_page_unknown_token_html_renders_error(client, db):
    _seed(db)
    r = client.get("/bind?token=nonexistent", headers={"Accept": "text/html"})
    assert r.status_code == 404
    body = r.text
    # Even error responses render HTML for HTML clients
    assert "<html" in body.lower() or "not found" in body.lower()


def test_bind_page_still_returns_json_for_json_clients(client, db):
    tok = _seed(db)
    r = client.get(f"/bind?token={tok}")  # default Accept */* → keep JSON for backcompat
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")


def test_bind_post_html_renders_success(client, db):
    tok = _seed(db)
    r = client.post(
        "/bind",
        data={"token": tok, "password": "strongpassword"},  # form-encoded
        headers={"Accept": "text/html"},
    )
    assert r.status_code == 200
    body = r.text
    assert "Alice" in body
    assert "成功" in body or "success" in body.lower() or "ok" in body.lower()
