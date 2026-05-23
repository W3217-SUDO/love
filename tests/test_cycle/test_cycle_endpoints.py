"""End-to-end tests for /cycle/* and /bbt/* endpoints."""

from sqlalchemy import delete

from app.modules.auth.invite import create_couple_and_invites, redeem_invite
from app.modules.auth.models import AuthSession, Couple, InviteToken, User
from app.modules.cycle.models import BbtReading, Period


def _login_alice(client, db, password="strongpassword"):
    """Wipe state, create couple, redeem alice's token, login and return her user_id."""
    db.execute(delete(AuthSession))
    db.execute(delete(BbtReading))
    db.execute(delete(Period))
    db.execute(delete(InviteToken))
    db.execute(delete(Couple))
    db.execute(delete(User))
    db.flush()
    he_tok, _ = create_couple_and_invites(db, he_name="Alice", she_name="Bob")
    db.flush()
    redeem_invite(db, token=he_tok, plain_password=password)
    db.flush()
    alice = db.query(User).filter_by(username="alice").one()

    r = client.post("/login", json={"username": "alice", "password": password})
    assert r.status_code == 200
    return alice.id


def test_unauthenticated_endpoints_401(client, db):
    r = client.post("/cycle/log/start", json={"start_date": "2026-05-01"})
    assert r.status_code == 401


def test_log_period_start(client, db):
    _login_alice(client, db)
    r = client.post("/cycle/log/start", json={"start_date": "2026-05-01"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["start_date"] == "2026-05-01"
    assert body["end_date"] is None
    assert body["id"]


def test_log_period_start_then_end(client, db):
    _login_alice(client, db)
    r1 = client.post("/cycle/log/start", json={"start_date": "2026-05-01"})
    assert r1.status_code == 200
    r2 = client.post(
        "/cycle/log/end",
        json={"start_date": "2026-05-01", "end_date": "2026-05-05"},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["end_date"] == "2026-05-05"


def test_log_period_end_unknown_404(client, db):
    _login_alice(client, db)
    r = client.post(
        "/cycle/log/end",
        json={"start_date": "2026-05-01", "end_date": "2026-05-05"},
    )
    assert r.status_code == 404


def test_log_period_overlap_409(client, db):
    _login_alice(client, db)
    client.post("/cycle/log/start", json={"start_date": "2026-05-01"})
    r = client.post("/cycle/log/start", json={"start_date": "2026-05-10"})
    assert r.status_code == 409


def test_list_periods_desc(client, db):
    _login_alice(client, db)
    client.post("/cycle/log/start", json={"start_date": "2026-03-01"})
    client.post(
        "/cycle/log/end",
        json={"start_date": "2026-03-01", "end_date": "2026-03-05"},
    )
    client.post("/cycle/log/start", json={"start_date": "2026-04-01"})
    client.post(
        "/cycle/log/end",
        json={"start_date": "2026-04-01", "end_date": "2026-04-05"},
    )
    client.post("/cycle/log/start", json={"start_date": "2026-05-01"})
    r = client.get("/cycle/periods")
    assert r.status_code == 200
    body = r.json()
    assert [p["start_date"] for p in body] == [
        "2026-05-01", "2026-04-01", "2026-03-01",
    ]


def test_log_bbt_inserts(client, db):
    _login_alice(client, db)
    r = client.post(
        "/bbt/log",
        json={"date": "2026-05-10", "temp_c": "36.55", "method": "oral"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["temp_c"] == "36.55"
    assert body["method"] == "oral"


def test_log_bbt_invalid_temp_422(client, db):
    _login_alice(client, db)
    r = client.post("/bbt/log", json={"date": "2026-05-10", "temp_c": "42.00"})
    assert r.status_code == 422


def test_log_bbt_invalid_method_422(client, db):
    _login_alice(client, db)
    r = client.post(
        "/bbt/log",
        json={"date": "2026-05-10", "temp_c": "36.55", "method": "garbage"},
    )
    assert r.status_code == 422


def test_log_bbt_upsert(client, db):
    _login_alice(client, db)
    r1 = client.post(
        "/bbt/log",
        json={"date": "2026-05-10", "temp_c": "36.55"},
    )
    assert r1.status_code == 200
    r2 = client.post(
        "/bbt/log",
        json={"date": "2026-05-10", "temp_c": "36.70", "method": "oral"},
    )
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]
    assert r2.json()["temp_c"] == "36.70"


def test_list_bbt_with_date_filter(client, db):
    _login_alice(client, db)
    for d in ["2026-05-01", "2026-05-05", "2026-05-10"]:
        client.post("/bbt/log", json={"date": d, "temp_c": "36.50"})
    r = client.get("/bbt?start=2026-05-04&end=2026-05-08")
    assert r.status_code == 200
    body = r.json()
    assert [row["date"] for row in body] == ["2026-05-05"]


def test_prediction_with_no_data_unknown(client, db):
    _login_alice(client, db)
    r = client.get("/cycle/prediction?date=2026-05-22")
    assert r.status_code == 200
    body = r.json()
    assert body["phase"] == "unknown"
    assert body["confidence_level"] == "low"


def test_prediction_with_calendar_data(client, db):
    _login_alice(client, db)
    client.post("/cycle/log/start", json={"start_date": "2026-04-01"})
    client.post(
        "/cycle/log/end",
        json={"start_date": "2026-04-01", "end_date": "2026-04-05"},
    )
    client.post("/cycle/log/start", json={"start_date": "2026-04-29"})
    client.post(
        "/cycle/log/end",
        json={"start_date": "2026-04-29", "end_date": "2026-05-03"},
    )
    r = client.get("/cycle/prediction?date=2026-05-10")
    assert r.status_code == 200
    body = r.json()
    assert body["next_period"] == "2026-05-27"
    assert body["ovulation"] == "2026-05-13"
    assert body["fertile_window"]["start"] == "2026-05-08"
    assert body["fertile_window"]["end"] == "2026-05-14"
    assert body["phase"] == "fertile"
    assert len(body["evidence"]) >= 1
