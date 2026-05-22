from sqlalchemy import delete

from app.modules.auth.invite import create_couple_and_invites, redeem_invite
from app.modules.auth.models import AuthSession, Couple, InviteToken, User
from app.modules.trip.models import Trip


def _login_alice(client, db):
    db.execute(delete(AuthSession))
    db.execute(delete(Trip))
    db.execute(delete(InviteToken))
    db.execute(delete(Couple))
    db.execute(delete(User))
    db.flush()
    he_tok, _ = create_couple_and_invites(db, he_name="Alice", she_name="Bob")
    db.flush()
    redeem_invite(db, token=he_tok, plain_password="strongpassword")
    db.flush()
    client.post("/login", json={"username": "alice", "password": "strongpassword"})


def test_trip_list_requires_auth(client, db):
    db.execute(delete(AuthSession))
    db.flush()
    r = client.get("/trip")
    assert r.status_code in (401, 303)  # 401 JSON or 303 redirect to login


def test_trip_list_renders(client, db):
    _login_alice(client, db)
    r = client.get("/trip", headers={"Accept": "text/html"})
    assert r.status_code == 200
    assert "旅行" in r.text


def test_trip_create_via_form(client, db):
    _login_alice(client, db)
    r = client.post(
        "/trip",
        data={"title": "Tokyo", "start_date": "2026-05-01"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303, 307)
    assert "/trip/" in r.headers["location"]


def test_trip_detail_renders(client, db):
    _login_alice(client, db)
    client.post("/trip", data={"title": "Kyoto", "start_date": "2026-05-01"})
    t = db.query(Trip).one()
    r = client.get(f"/trip/{t.id}", headers={"Accept": "text/html"})
    assert r.status_code == 200
    assert "Kyoto" in r.text


def test_trip_update(client, db):
    _login_alice(client, db)
    client.post("/trip", data={"title": "old", "start_date": "2026-05-01"})
    t = db.query(Trip).one()
    r = client.post(
        f"/trip/{t.id}",
        data={"title": "new", "start_date": "2026-05-01"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303, 307)


def test_trip_delete(client, db):
    _login_alice(client, db)
    client.post("/trip", data={"title": "X", "start_date": "2026-05-01"})
    t = db.query(Trip).one()
    r = client.post(f"/trip/{t.id}/delete", follow_redirects=False)
    assert r.status_code in (302, 303, 307)
    assert db.query(Trip).count() == 0


def test_trip_unknown_404(client, db):
    _login_alice(client, db)
    r = client.get("/trip/99999", headers={"Accept": "text/html"})
    assert r.status_code == 404
