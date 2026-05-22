import time

import pytest

from app.modules.media.signing import (
    InvalidSignature,
    sign_media_url,
    verify_media_url,
)


def test_sign_and_verify_roundtrip():
    q = sign_media_url(42, ttl_seconds=60)
    assert verify_media_url(q) == 42


def test_verify_rejects_tampered_id():
    q = sign_media_url(42)
    # Tamper with k= part
    tampered = q.replace("k=42", "k=43")
    with pytest.raises(InvalidSignature):
        verify_media_url(tampered)


def test_verify_rejects_expired(monkeypatch):
    q = sign_media_url(42, ttl_seconds=1)
    # Force time forward
    real = time.time
    monkeypatch.setattr(time, "time", lambda: real() + 10)
    with pytest.raises(InvalidSignature):
        verify_media_url(q)


def test_verify_rejects_bad_format():
    with pytest.raises(InvalidSignature):
        verify_media_url("not-a-valid-query")
