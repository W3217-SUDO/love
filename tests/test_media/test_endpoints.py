import io

from PIL import Image
from sqlalchemy import delete

from app.modules.auth.invite import create_couple_and_invites, redeem_invite
from app.modules.auth.models import AuthSession, Couple, InviteToken, User
from app.modules.media.models import Media


def _login(client, db, password="strongpassword"):
    db.execute(delete(AuthSession))
    db.execute(delete(Media))
    db.execute(delete(InviteToken))
    db.execute(delete(Couple))
    db.execute(delete(User))
    db.flush()
    he_tok, _ = create_couple_and_invites(db, he_name="Alice", she_name="Bob")
    db.flush()
    redeem_invite(db, token=he_tok, plain_password=password)
    db.flush()
    client.post("/login", json={"username": "alice", "password": password})


def _png_bytes(size=(100, 80)) -> bytes:
    img = Image.new("RGB", size, (255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_upload_returns_media_metadata(client, db, tmp_path, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr("app.config.get_settings", lambda: type(
        "S", (), {**get_settings().model_dump(), "upload_dir": tmp_path})())
    _login(client, db)
    files = {"file": ("test.png", _png_bytes(), "image/png")}
    r = client.post("/media/upload", files=files)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"]
    assert body["kind"] == "image"
    assert body["width"] == 100
    assert "thumb_url" in body
    assert "preview_url" in body


def test_upload_requires_auth(client, db):
    db.execute(delete(AuthSession))
    db.flush()
    files = {"file": ("test.png", _png_bytes(), "image/png")}
    r = client.post("/media/upload", files=files)
    assert r.status_code == 401


def test_serve_with_cookie_auth(client, db, tmp_path, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr("app.config.get_settings", lambda: type(
        "S", (), {**get_settings().model_dump(), "upload_dir": tmp_path})())
    _login(client, db)
    r = client.post("/media/upload", files={"file": ("t.png", _png_bytes(), "image/png")})
    media_id = r.json()["id"]
    r2 = client.get(f"/media/{media_id}")
    assert r2.status_code == 200
    assert r2.headers["content-type"] == "image/webp"


def test_serve_with_signed_url_no_cookie(client, db, tmp_path, monkeypatch):
    from app.config import get_settings
    from app.modules.media.signing import sign_media_url
    monkeypatch.setattr("app.config.get_settings", lambda: type(
        "S", (), {**get_settings().model_dump(), "upload_dir": tmp_path})())
    _login(client, db)
    r = client.post("/media/upload", files={"file": ("t.png", _png_bytes(), "image/png")})
    media_id = r.json()["id"]
    # Drop the cookie
    client.cookies.clear()
    # Use signed URL
    q = sign_media_url(media_id)
    r2 = client.get(f"/media/{media_id}?{q}")
    assert r2.status_code == 200


def test_serve_without_auth_and_no_signature_403(client, db, tmp_path, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr("app.config.get_settings", lambda: type(
        "S", (), {**get_settings().model_dump(), "upload_dir": tmp_path})())
    _login(client, db)
    r = client.post("/media/upload", files={"file": ("t.png", _png_bytes(), "image/png")})
    media_id = r.json()["id"]
    client.cookies.clear()
    r2 = client.get(f"/media/{media_id}")
    assert r2.status_code == 401  # no cookie + no signature


def test_serve_unknown_404(client, db):
    _login(client, db)
    r = client.get("/media/999999")
    assert r.status_code == 404
