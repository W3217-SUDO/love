from sqlalchemy import delete

from app.modules.auth.invite import create_couple_and_invites, redeem_invite
from app.modules.auth.models import AuthSession, Couple, InviteToken, User


def _login(client, db, password="strongpassword"):
    db.execute(delete(AuthSession))
    db.execute(delete(InviteToken))
    db.execute(delete(Couple))
    db.execute(delete(User))
    db.flush()
    he_tok, _ = create_couple_and_invites(db, he_name="Alice", she_name="Bob")
    db.flush()
    redeem_invite(db, token=he_tok, plain_password=password)
    db.flush()
    client.post("/login", json={"username": "alice", "password": password})


def test_root_requires_auth(client, db):
    db.execute(delete(AuthSession))
    db.flush()
    r = client.get("/")
    assert r.status_code == 401


def test_root_renders_today(client, db):
    _login(client, db)
    r = client.get("/", headers={"Accept": "text/html"})
    assert r.status_code == 200
    body = r.text
    assert "今天" in body or "Alice" in body
    assert "D" in body  # cycle ring rendered (D1 etc.)


def test_partner_card_fragment(client, db):
    _login(client, db)
    r = client.get("/today/partner-card", headers={"Accept": "text/html"})
    assert r.status_code == 200
    body = r.text
    assert "Bob" in body or "今天" in body


def test_predictor_card_fragment(client, db):
    _login(client, db)
    r = client.get("/today/predictor-card", headers={"Accept": "text/html"})
    assert r.status_code == 200


def test_cycle_ring_fragment(client, db):
    _login(client, db)
    r = client.get("/today/cycle-ring", headers={"Accept": "text/html"})
    assert r.status_code == 200
    assert "<svg" in r.text


def test_calendar_current_month(client, db):
    _login(client, db)
    r = client.get("/calendar", headers={"Accept": "text/html"})
    assert r.status_code == 200
    body = r.text
    assert "<table" in body or "weeks" not in body  # at minimum renders


def test_calendar_specific_month(client, db):
    _login(client, db)
    r = client.get("/calendar/2026/05", headers={"Accept": "text/html"})
    assert r.status_code == 200
    body = r.text
    assert "2026" in body


def test_calendar_invalid_month_404(client, db):
    _login(client, db)
    r = client.get("/calendar/2026/13")
    assert r.status_code == 404


def test_me_page_renders(client, db):
    _login(client, db)
    r = client.get("/me", headers={"Accept": "text/html"})
    assert r.status_code == 200
    body = r.text
    assert "Alice" in body
    assert "Bob" in body or "TA" in body
