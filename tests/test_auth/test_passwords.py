import pytest

from app.modules.auth.passwords import (
    InvalidHashError,
    hash_password,
    needs_rehash,
    verify_password,
)


def test_hash_returns_argon2id_phc_string():
    h = hash_password("hunter2-strong-passphrase")
    # Argon2id PHC strings start with $argon2id$
    assert h.startswith("$argon2id$")
    # Hashes are reasonably long (>= 80 chars in practice)
    assert len(h) >= 80


def test_hashes_are_unique_per_call():
    h1 = hash_password("samepassword")
    h2 = hash_password("samepassword")
    assert h1 != h2  # random salt each time


def test_verify_correct_password():
    pwd = "correct horse battery staple"
    h = hash_password(pwd)
    assert verify_password(pwd, h) is True


def test_verify_wrong_password():
    h = hash_password("right-password")
    assert verify_password("wrong-password", h) is False


def test_verify_with_garbage_hash_raises():
    with pytest.raises(InvalidHashError):
        verify_password("anything", "not-a-real-hash")


def test_verify_with_empty_hash_returns_false():
    # Empty string is gracefully False (matches "unbound user" case)
    assert verify_password("anything", "") is False


def test_needs_rehash_for_valid_hash_is_false():
    h = hash_password("xxxxxxxx")
    assert needs_rehash(h) is False


def test_minimum_password_length_enforced():
    with pytest.raises(ValueError):
        hash_password("short")  # < 8 chars
