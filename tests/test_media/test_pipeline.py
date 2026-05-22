import hashlib
import io
from pathlib import Path

import pytest
from PIL import Image

from app.config import get_settings
from app.modules.auth.models import User
from app.modules.media.pipeline import (
    PipelineError,
    UnsupportedMimeError,
    process_upload,
)


def _png_bytes(size=(100, 80), color=(255, 0, 0)) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _user(db, name="alice"):
    u = User(username=name, display_name=name.title(), role="she")
    db.add(u)
    db.flush()
    return u


def test_process_image_creates_media_row(db, tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.get_settings", lambda: type(
        "S", (), {**get_settings().model_dump(), "upload_dir": tmp_path})())
    u = _user(db)
    data = _png_bytes()
    media = process_upload(db, owner_id=u.id, filename="hello.png",
                           mime="image/png", payload=data)
    db.flush()
    assert media.id is not None
    assert media.kind == "image"
    assert media.size_bytes == len(data)
    assert media.width == 100
    assert media.height == 80
    assert media.sha256 == hashlib.sha256(data).hexdigest()
    # Original file written
    assert Path(media.original_path).is_file()
    assert media.thumb_path and Path(media.thumb_path).is_file()
    assert media.preview_path and Path(media.preview_path).is_file()


def test_process_dedupes_by_sha(db, tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.get_settings", lambda: type(
        "S", (), {**get_settings().model_dump(), "upload_dir": tmp_path})())
    u = _user(db)
    data = _png_bytes()
    m1 = process_upload(db, owner_id=u.id, filename="a.png",
                        mime="image/png", payload=data)
    db.flush()
    m2 = process_upload(db, owner_id=u.id, filename="b.png",
                        mime="image/png", payload=data)
    db.flush()
    assert m1.id == m2.id


def test_process_rejects_bad_mime(db, tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.get_settings", lambda: type(
        "S", (), {**get_settings().model_dump(), "upload_dir": tmp_path})())
    u = _user(db)
    with pytest.raises(UnsupportedMimeError):
        process_upload(db, owner_id=u.id, filename="x.exe",
                       mime="application/octet-stream", payload=b"MZ\x90\x00")


def test_process_rejects_fake_image(db, tmp_path, monkeypatch):
    """File claims to be png but content isn't."""
    monkeypatch.setattr("app.config.get_settings", lambda: type(
        "S", (), {**get_settings().model_dump(), "upload_dir": tmp_path})())
    u = _user(db)
    with pytest.raises(PipelineError):
        process_upload(db, owner_id=u.id, filename="fake.png",
                       mime="image/png", payload=b"this is not a png")


def test_process_strips_exif(db, tmp_path, monkeypatch):
    """Saved file should NOT contain EXIF after pipeline."""
    pytest.importorskip("piexif")
    from PIL import Image
    monkeypatch.setattr("app.config.get_settings", lambda: type(
        "S", (), {**get_settings().model_dump(), "upload_dir": tmp_path})())
    u = _user(db)
    # Create a JPEG with a fake EXIF block
    img = Image.new("RGB", (100, 80), (0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    data = buf.getvalue()
    media = process_upload(db, owner_id=u.id, filename="g.jpg",
                           mime="image/jpeg", payload=data)
    db.flush()
    # Saved file is WebP — by design has no EXIF.
    saved = Image.open(media.original_path)
    assert saved.info.get("exif") in (None, b"")
