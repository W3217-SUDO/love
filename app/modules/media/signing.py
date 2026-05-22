"""HMAC-signed URL helpers for media serving without cookie auth."""
from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import parse_qs, urlencode

from app.config import get_settings


class InvalidSignature(Exception):
    """Raised when a signed URL is malformed, expired, or tampered with."""


def _key() -> bytes:
    return get_settings().secret_key.encode("utf-8")


def sign_media_url(media_id: int, *, ttl_seconds: int = 86400) -> str:
    """Return a query-string fragment like 'k=42&e=1234567890&s=<hex>'."""
    expires = int(time.time()) + ttl_seconds
    payload = f"{media_id}|{expires}".encode()
    sig = hmac.new(_key(), payload, hashlib.sha256).hexdigest()
    return urlencode({"k": media_id, "e": expires, "s": sig})


def verify_media_url(query: str) -> int:
    """Return the media_id if the HMAC + ttl are valid; otherwise raise."""
    try:
        parsed = parse_qs(query, keep_blank_values=False, strict_parsing=False)
        media_id = int(parsed["k"][0])
        expires = int(parsed["e"][0])
        sig = parsed["s"][0]
    except (KeyError, ValueError, TypeError, IndexError) as exc:
        raise InvalidSignature("bad URL format") from exc
    if expires < time.time():
        raise InvalidSignature("expired")
    expected = hmac.new(
        _key(), f"{media_id}|{expires}".encode(), hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise InvalidSignature("bad signature")
    return media_id
