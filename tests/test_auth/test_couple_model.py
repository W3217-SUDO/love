import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

from app.modules.auth.models import Couple, User


def _make_pair(db):
    he = User(username="he", display_name="He", role="he")
    she = User(username="she", display_name="She", role="she")
    db.add_all([he, she])
    db.flush()
    return he, she


def test_create_couple(db):
    he, she = _make_pair(db)
    couple = Couple(user_a_id=he.id, user_b_id=she.id)
    db.add(couple)
    db.flush()
    assert couple.id is not None
    assert couple.bonded_at is None  # not bonded yet
    assert couple.created_at is not None


def test_user_a_and_b_must_differ(db):
    he, _ = _make_pair(db)
    db.add(Couple(user_a_id=he.id, user_b_id=he.id))
    # MariaDB raises CHECK violations as OperationalError; accept both.
    with pytest.raises((IntegrityError, OperationalError)):
        db.flush()


def test_user_a_and_b_unique_pair(db):
    """An identical (user_a, user_b) pair cannot be inserted twice."""
    he, she = _make_pair(db)
    db.add(Couple(user_a_id=he.id, user_b_id=she.id))
    db.flush()
    db.add(Couple(user_a_id=he.id, user_b_id=she.id))
    with pytest.raises(IntegrityError):
        db.flush()
