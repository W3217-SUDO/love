from sqlalchemy import delete

from app.modules.auth.invite import create_couple_and_invites, redeem_invite
from app.modules.auth.models import AuthSession, Couple, InviteToken, User


def _login(client, db):
    password = "strongpassword"
    db.execute(delete(AuthSession))
    db.execute(delete(InviteToken))
    db.execute(delete(Couple))
    db.execute(delete(User))
    db.flush()
    he_token, _ = create_couple_and_invites(db, he_name="Alice", she_name="Bob")
    db.flush()
    redeem_invite(db, token=he_token, plain_password=password)
    db.flush()
    client.post("/login", json={"username": "alice", "password": password})


def test_charts_page_renders_trend_center(client, db):
    _login(client, db)

    response = client.get("/charts", headers={"Accept": "text/html"})

    assert response.status_code == 200
    assert "趋势" in response.text
    assert "基础体温" in response.text


def test_bbt_json_returns_bbt_series(client, db):
    _login(client, db)

    response = client.get("/charts/bbt.json")

    assert response.status_code == 200
    assert response.json()["kind"] == "bbt"
