import pytest
from sqlalchemy.exc import DatabaseError, IntegrityError

from app.modules.auth.models import User


def test_create_user(db):
    user = User(username="alice", display_name="Alice", role="she")
    db.add(user)
    db.flush()
    assert user.id is not None
    assert user.password_hash is None  # not yet bound
    assert user.created_at is not None


def test_username_must_be_unique(db):
    db.add(User(username="bob", display_name="Bob", role="he"))
    db.flush()
    db.add(User(username="bob", display_name="Robert", role="he"))
    with pytest.raises(IntegrityError):
        db.flush()


def test_role_check_constraint_rejects_invalid(db):
    # MariaDB raises CHECK violations as OperationalError (errno 4025),
    # not IntegrityError. Both inherit from DatabaseError.
    user = User(username="zed", display_name="Zed", role="invalid")
    db.add(user)
    with pytest.raises(DatabaseError):
        db.flush()


def test_two_users_with_different_roles(db):
    db.add(User(username="he1", display_name="He", role="he"))
    db.add(User(username="she1", display_name="She", role="she"))
    db.flush()  # should succeed
