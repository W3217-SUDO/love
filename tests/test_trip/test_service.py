from datetime import date

import pytest
from sqlalchemy import delete

from app.modules.auth.invite import create_couple_and_invites
from app.modules.auth.models import Couple, InviteToken, User
from app.modules.trip.service import (
    TripForbidden,
    TripNotFound,
    create_trip,
    delete_trip,
    get_trip,
    list_trips,
    update_trip,
)


def _seed(db):
    db.execute(delete(InviteToken))
    db.execute(delete(Couple))
    db.execute(delete(User))
    db.flush()
    create_couple_and_invites(db, he_name="Alice", she_name="Bob")
    db.flush()
    alice = db.query(User).filter_by(username="alice").one()
    bob = db.query(User).filter_by(username="bob").one()
    return alice, bob


def test_create_trip(db):
    alice, _ = _seed(db)
    t = create_trip(db, creator_id=alice.id, title="Tokyo", start_date=date(2026, 5, 1))
    db.flush()
    assert t.id is not None
    assert t.title == "Tokyo"


def test_create_trip_empty_title_raises(db):
    alice, _ = _seed(db)
    with pytest.raises(ValueError):
        create_trip(db, creator_id=alice.id, title="   ")


def test_end_before_start_raises(db):
    alice, _ = _seed(db)
    with pytest.raises(ValueError):
        create_trip(
            db, creator_id=alice.id, title="X",
            start_date=date(2026, 5, 10), end_date=date(2026, 5, 1),
        )


def test_partner_can_see_trip(db):
    alice, bob = _seed(db)
    t = create_trip(db, creator_id=alice.id, title="X")
    db.flush()
    got = get_trip(db, trip_id=t.id, requester_id=bob.id)
    assert got.id == t.id


def test_outsider_cannot_see_trip(db):
    alice, _ = _seed(db)
    outsider = User(username="zoe", display_name="Zoe", role="she")
    db.add(outsider)
    db.flush()
    t = create_trip(db, creator_id=alice.id, title="X")
    db.flush()
    with pytest.raises(TripForbidden):
        get_trip(db, trip_id=t.id, requester_id=outsider.id)


def test_partner_can_update_trip(db):
    alice, bob = _seed(db)
    t = create_trip(db, creator_id=alice.id, title="X")
    db.flush()
    updated = update_trip(db, trip_id=t.id, requester_id=bob.id, title="Y")
    db.flush()
    assert updated.title == "Y"


def test_only_creator_can_delete(db):
    alice, bob = _seed(db)
    t = create_trip(db, creator_id=alice.id, title="X")
    db.flush()
    with pytest.raises(TripForbidden):
        delete_trip(db, trip_id=t.id, requester_id=bob.id)
    delete_trip(db, trip_id=t.id, requester_id=alice.id)
    db.flush()


def test_list_includes_both_partners_trips(db):
    alice, bob = _seed(db)
    create_trip(db, creator_id=alice.id, title="Alice trip", start_date=date(2026, 5, 1))
    create_trip(db, creator_id=bob.id, title="Bob trip", start_date=date(2026, 5, 10))
    db.flush()
    rows = list_trips(db, requester_id=alice.id)
    titles = {r.title for r in rows}
    assert "Alice trip" in titles
    assert "Bob trip" in titles


def test_get_trip_unknown_raises(db):
    alice, _ = _seed(db)
    with pytest.raises(TripNotFound):
        get_trip(db, trip_id=9999, requester_id=alice.id)
