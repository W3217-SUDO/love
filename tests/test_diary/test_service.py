
import pytest
from sqlalchemy import delete

from app.modules.auth.invite import create_couple_and_invites
from app.modules.auth.models import Couple, InviteToken, User
from app.modules.diary.service import (
    DiaryForbidden,
    DiaryNotFound,
    create_entry,
    delete_entry,
    get_entry,
    list_visible_entries,
    update_entry,
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


def test_create_entry(db):
    alice, _ = _seed(db)
    e = create_entry(db, author_id=alice.id, body="hello")
    db.flush()
    assert e.id is not None
    assert e.visibility == "shared"


def test_get_entry_author_can_see(db):
    alice, _ = _seed(db)
    e = create_entry(db, author_id=alice.id, body="hi")
    db.flush()
    got = get_entry(db, entry_id=e.id, requester_id=alice.id)
    assert got.id == e.id


def test_get_entry_partner_can_see_shared(db):
    alice, bob = _seed(db)
    e = create_entry(db, author_id=alice.id, body="hi", visibility="shared")
    db.flush()
    got = get_entry(db, entry_id=e.id, requester_id=bob.id)
    assert got.id == e.id


def test_get_entry_partner_cannot_see_private(db):
    alice, bob = _seed(db)
    e = create_entry(db, author_id=alice.id, body="hi", visibility="private")
    db.flush()
    with pytest.raises(DiaryForbidden):
        get_entry(db, entry_id=e.id, requester_id=bob.id)


def test_get_entry_unknown_raises(db):
    alice, _ = _seed(db)
    with pytest.raises(DiaryNotFound):
        get_entry(db, entry_id=99999, requester_id=alice.id)


def test_update_entry_only_author(db):
    alice, bob = _seed(db)
    e = create_entry(db, author_id=alice.id, body="hi")
    db.flush()
    updated = update_entry(db, entry_id=e.id, requester_id=alice.id, body="new")
    db.flush()
    assert updated.body == "new"
    with pytest.raises(DiaryForbidden):
        update_entry(db, entry_id=e.id, requester_id=bob.id, body="hack")


def test_delete_entry_only_author(db):
    alice, bob = _seed(db)
    e = create_entry(db, author_id=alice.id, body="hi")
    db.flush()
    with pytest.raises(DiaryForbidden):
        delete_entry(db, entry_id=e.id, requester_id=bob.id)
    delete_entry(db, entry_id=e.id, requester_id=alice.id)
    db.flush()


def test_list_visible_excludes_partner_private(db):
    alice, bob = _seed(db)
    create_entry(db, author_id=alice.id, body="public", visibility="shared")
    create_entry(db, author_id=alice.id, body="secret", visibility="private")
    create_entry(db, author_id=bob.id, body="bob entry")
    db.flush()
    bob_view = list_visible_entries(db, requester_id=bob.id)
    bodies = [e.body for e in bob_view]
    assert "public" in bodies
    assert "bob entry" in bodies
    assert "secret" not in bodies


def test_list_visible_includes_own_private(db):
    alice, _ = _seed(db)
    create_entry(db, author_id=alice.id, body="self-private", visibility="private")
    db.flush()
    own = list_visible_entries(db, requester_id=alice.id)
    assert any(e.body == "self-private" for e in own)
