
from sqlalchemy import delete

from app.modules.auth.invite import create_couple_and_invites, redeem_invite
from app.modules.auth.models import AuthSession, Couple, InviteToken, User
from app.modules.daily_log.models import DailyEntry, DailyTag


def _login_alice(client, db, password="strongpassword"):
    db.execute(delete(AuthSession))
    db.execute(delete(DailyTag))
    db.execute(delete(DailyEntry))
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


def test_unauthenticated_log_redirects_or_401(client, db):
    r = client.get("/log/today", follow_redirects=False)
    assert r.status_code in (302, 401)  # either redirect to /login or 401


def test_log_today_redirects_to_dated_url(client, db):
    _login_alice(client, db)
    r = client.get("/log/today", follow_redirects=False)
    assert r.status_code in (302, 303, 307)
    location = r.headers.get("location", "")
    assert location.startswith("/log/")
    assert location != "/log/today"


def test_log_date_page_renders(client, db):
    _login_alice(client, db)
    r = client.get("/log/2026-05-22", headers={"Accept": "text/html"})
    assert r.status_code == 200
    body = r.text
    assert "今天的标签" in body or "2026-05-22" in body
    # All Flo categories present
    assert "心情" in body
    assert "性行为" in body or "性欲" in body
    # Some tags rendered
    assert "mood_happy" in body or "快乐" in body


def test_log_date_json_view(client, db):
    _login_alice(client, db)
    # First, log a tag via toggle
    client.post("/log/2026-05-22/tag/mood_happy/toggle")
    r = client.get("/log/2026-05-22", headers={"Accept": "application/json"})
    assert r.status_code == 200
    body = r.json()
    assert "tags" in body
    keys = [t["tag_key"] for t in body["tags"]]
    assert "mood_happy" in keys


def test_toggle_tag_activates(client, db):
    _login_alice(client, db)
    r = client.post(
        "/log/2026-05-22/tag/mood_happy/toggle",
        headers={"Accept": "application/json"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["active"] is True
    assert body["tag_key"] == "mood_happy"


def test_toggle_tag_deactivates_on_second_call(client, db):
    _login_alice(client, db)
    client.post(
        "/log/2026-05-22/tag/mood_happy/toggle",
        headers={"Accept": "application/json"},
    )
    r2 = client.post(
        "/log/2026-05-22/tag/mood_happy/toggle",
        headers={"Accept": "application/json"},
    )
    assert r2.status_code == 200
    assert r2.json()["active"] is False


def test_toggle_unknown_tag_404(client, db):
    _login_alice(client, db)
    r = client.post(
        "/log/2026-05-22/tag/not_a_real_tag/toggle",
        headers={"Accept": "application/json"},
    )
    assert r.status_code == 404


def test_toggle_returns_html_fragment_on_html_accept(client, db):
    _login_alice(client, db)
    r = client.post(
        "/log/2026-05-22/tag/mood_happy/toggle",
        headers={"Accept": "text/html"},
    )
    assert r.status_code == 200
    body = r.text
    assert "pill" in body
    assert 'aria-pressed="true"' in body
    assert "mood_happy" in body
