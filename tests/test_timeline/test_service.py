from datetime import date

from sqlalchemy import delete

from app.modules.auth.invite import create_couple_and_invites
from app.modules.auth.models import Couple, InviteToken, User
from app.modules.cycle.service import log_period_end, log_period_start
from app.modules.daily_log.service import toggle_tag
from app.modules.settings.service import Visibility, ensure_settings, set_visibility
from app.modules.timeline.service import (
    build_today_snapshot,
    days_together,
    find_partner,
)


def _seed(db):
    db.execute(delete(InviteToken))
    db.execute(delete(Couple))
    db.execute(delete(User))
    db.flush()
    create_couple_and_invites(db, he_name="Alice", she_name="Bob")
    db.flush()


def test_find_partner_returns_the_other_user(db):
    _seed(db)
    alice = db.query(User).filter_by(username="alice").one()
    bob = db.query(User).filter_by(username="bob").one()
    assert find_partner(db, alice.id).id == bob.id
    assert find_partner(db, bob.id).id == alice.id


def test_find_partner_none_when_unbound(db):
    db.execute(delete(InviteToken))
    db.execute(delete(Couple))
    db.execute(delete(User))
    db.flush()
    u = User(username="lonely", display_name="Lonely", role="he")
    db.add(u)
    db.flush()
    assert find_partner(db, u.id) is None


def test_days_together_returns_int(db):
    _seed(db)
    alice = db.query(User).filter_by(username="alice").one()
    d = days_together(db, alice.id)
    assert d is not None
    assert d >= 0


def test_build_today_snapshot_minimal(db):
    _seed(db)
    alice = db.query(User).filter_by(username="alice").one()
    snap = build_today_snapshot(db, user=alice, target_date=date(2026, 5, 22))
    assert snap.user.id == alice.id
    assert snap.date == date(2026, 5, 22)
    assert snap.active_tags == []
    assert snap.partner is not None
    assert snap.partner.username == "bob"


def test_build_today_snapshot_with_tags_and_period(db):
    _seed(db)
    alice = db.query(User).filter_by(username="alice").one()
    log_period_start(db, user_id=alice.id, start_date=date(2026, 5, 1))
    db.flush()
    log_period_end(db, user_id=alice.id, start_date=date(2026, 5, 1), end_date=date(2026, 5, 5))
    db.flush()
    toggle_tag(db, user_id=alice.id, date=date(2026, 5, 22), tag_key="mood_happy")
    db.flush()
    snap = build_today_snapshot(db, user=alice, target_date=date(2026, 5, 22))
    assert any(t.tag_key == "mood_happy" for t in snap.active_tags)


def test_build_today_snapshot_hides_private_partner_daily_log_and_cycle(db):
    _seed(db)
    alice = db.query(User).filter_by(username="alice").one()
    bob = db.query(User).filter_by(username="bob").one()
    settings = ensure_settings(db, bob.id)
    set_visibility(db, settings, "daily_log", Visibility.PRIVATE)
    set_visibility(db, settings, "cycle", Visibility.PRIVATE)
    log_period_start(db, user_id=bob.id, start_date=date(2026, 5, 1))
    log_period_end(db, user_id=bob.id, start_date=date(2026, 5, 1), end_date=date(2026, 5, 5))
    toggle_tag(db, user_id=bob.id, date=date(2026, 5, 22), tag_key="mood_happy")
    db.flush()

    snap = build_today_snapshot(db, user=alice, target_date=date(2026, 5, 22))

    assert snap.partner is not None
    assert snap.partner.id == bob.id
    assert snap.partner_phase is None
    assert snap.partner_tags == []


def test_build_today_snapshot_shows_partner_defaults_when_shared(db):
    _seed(db)
    alice = db.query(User).filter_by(username="alice").one()
    bob = db.query(User).filter_by(username="bob").one()
    log_period_start(db, user_id=bob.id, start_date=date(2026, 5, 1))
    log_period_end(db, user_id=bob.id, start_date=date(2026, 5, 1), end_date=date(2026, 5, 5))
    toggle_tag(db, user_id=bob.id, date=date(2026, 5, 22), tag_key="mood_happy")
    db.flush()

    snap = build_today_snapshot(db, user=alice, target_date=date(2026, 5, 22))

    assert snap.partner is not None
    assert snap.partner_phase is not None
    assert any(t.tag_key == "mood_happy" for t in snap.partner_tags)
