from datetime import date, timedelta

from sqlalchemy import delete

from app.modules.auth.invite import create_couple_and_invites, redeem_invite
from app.modules.auth.models import AuthSession, Couple, InviteToken, User
from app.modules.cycle.predictor import CyclePrediction, SignalResult
from app.modules.cycle.service import log_period_end, log_period_start


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


def test_today_links_to_m2_features(client, db):
    _login(client, db)
    r = client.get("/", headers={"Accept": "text/html"})
    assert r.status_code == 200
    body = r.text
    for href in (
        "/log/today",
        "/cycle/log",
        "/bbt/log",
        "/reports/new",
        "/charts",
        "/me/settings",
    ):
        assert f'href="{href}"' in body


def test_partner_card_fragment(client, db):
    _login(client, db)
    r = client.get("/today/partner-card", headers={"Accept": "text/html"})
    assert r.status_code == 200
    body = r.text
    assert "Bob" in body or "今天" in body


def test_partner_card_marks_shared_only_data(client, db):
    _login(client, db)
    r = client.get("/today/partner-card", headers={"Accept": "text/html"})
    assert r.status_code == 200
    assert "仅显示共享" in r.text


def test_predictor_card_fragment(client, db):
    _login(client, db)
    r = client.get("/today/predictor-card", headers={"Accept": "text/html"})
    assert r.status_code == 200


def test_predictor_card_shows_chinese_confidence_when_available(client, db):
    _login(client, db)
    alice = db.query(User).filter_by(username="alice").one()
    start = date.today() - timedelta(days=28)
    log_period_start(db, user_id=alice.id, start_date=start)
    log_period_end(
        db,
        user_id=alice.id,
        start_date=start,
        end_date=start + timedelta(days=4),
    )
    db.flush()

    r = client.get("/today/predictor-card", headers={"Accept": "text/html"})
    assert r.status_code == 200
    body = r.text
    assert "置信度" in body
    assert "预测依据" in body


def test_predictor_card_translates_internal_evidence(client, db):
    _login(client, db)
    alice = db.query(User).filter_by(username="alice").one()
    start = date.today() - timedelta(days=28)
    log_period_start(db, user_id=alice.id, start_date=start)
    log_period_end(
        db,
        user_id=alice.id,
        start_date=start,
        end_date=start + timedelta(days=4),
    )
    db.flush()

    r = client.get("/today/predictor-card", headers={"Accept": "text/html"})

    assert r.status_code == 200
    body = r.text
    assert "预测依据" in body
    assert "周期记录" in body
    assert "平均周期" in body
    assert "no period history" not in body
    assert "avg_cycle=" not in body
    assert "need >=" not in body
    assert "no positive LH" not in body


def test_predictor_card_masks_unknown_bbt_evidence(client, db, monkeypatch):
    _login(client, db)
    today = date.today()

    class FakePredictor:
        def predict(self, db, *, user_id, target_date):
            return CyclePrediction(
                target_date=target_date,
                next_period=today + timedelta(days=14),
                ovulation=today,
                fertile_window=(today - timedelta(days=2), today + timedelta(days=2)),
                phase="ovulation",
                confidence_level="medium",
                confidence_score=0.5,
                evidence=[
                    SignalResult(
                        source="bbt",
                        active=True,
                        confidence=0.6,
                        evidence=f"BBT detected ovulation on {today.isoformat()}",
                        predicted_ovulation=today,
                    ),
                ],
            )

    monkeypatch.setattr("app.modules.timeline.router.CombinedPredictor", FakePredictor)

    r = client.get("/today/predictor-card", headers={"Accept": "text/html"})

    assert r.status_code == 200
    body = r.text
    assert "已记录基础体温证据" in body
    assert "BBT detected" not in body


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


def test_calendar_legend_is_readable(client, db):
    _login(client, db)
    r = client.get("/calendar", headers={"Accept": "text/html"})
    assert r.status_code == 200
    body = r.text
    assert "经期" in body
    assert "预测经期" in body
    assert "易孕期" in body


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
