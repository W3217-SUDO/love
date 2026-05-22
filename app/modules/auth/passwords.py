"""Argon2id password hashing for the bind/login flow.

We use argon2-cffi with sensible defaults (the library's defaults follow
RFC 9106 recommended parameters for interactive logins). Hashes are stored as
PHC strings in `users.password_hash` (VARCHAR(255), fits comfortably).

The bind/login flow:
  bind  -> hash_password(plain) -> store
  login -> verify_password(plain, stored_hash) -> True/False

We treat empty stored_hash as "user has not bound yet" and return False from
verify -- never raising -- so the login endpoint can give a uniform
"invalid credentials" message without leaking which case applies.
"""
from argon2 import PasswordHasher
from argon2 import exceptions as argon2_exc

MIN_PASSWORD_LENGTH = 8

# Library defaults are tuned for interactive auth (~50ms on modern hardware).
# We pin them here so policy changes are visible in code review.
_hasher = PasswordHasher(
    time_cost=3,       # iterations
    memory_cost=64_000,  # 64 MiB
    parallelism=1,
    hash_len=32,
    salt_len=16,
)


class InvalidHashError(ValueError):
    """Raised when a stored hash is malformed (not 'wrong password')."""


def hash_password(plain: str) -> str:
    """Hash a plaintext password into an Argon2id PHC string."""
    if len(plain) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"password must be at least {MIN_PASSWORD_LENGTH} characters"
        )
    return _hasher.hash(plain)


def verify_password(plain: str, stored_hash: str) -> bool:
    """Return True iff plain matches stored_hash.

    Returns False for empty hashes (unbound user).
    Raises InvalidHashError if hash is malformed.
    """
    if not stored_hash:
        return False
    try:
        return _hasher.verify(stored_hash, plain)
    except argon2_exc.VerifyMismatchError:
        return False
    except argon2_exc.InvalidHashError as exc:
        raise InvalidHashError(str(exc)) from exc


def needs_rehash(stored_hash: str) -> bool:
    """True if the stored hash uses outdated parameters and should be re-hashed."""
    if not stored_hash:
        return False
    try:
        return _hasher.check_needs_rehash(stored_hash)
    except argon2_exc.InvalidHashError:
        return False
