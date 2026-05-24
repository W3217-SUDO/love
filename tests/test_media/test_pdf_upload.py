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


def _png_bytes(size=(10, 10)) -> bytes:
    img = Image.new("RGB", size, (0, 128, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_upload_pdf_returns_pdf_kind(client, db, tmp_path, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: type("S", (), {**get_settings().model_dump(), "upload_dir": tmp_path})(),
    )
    _login(client, db)
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"

    r = client.post(
        "/media/upload",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
    )

    assert r.status_code == 200, r.text
    assert r.json()["kind"] == "pdf"


def test_serve_pdf_original_uses_pdf_content_type(client, db, tmp_path, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: type("S", (), {**get_settings().model_dump(), "upload_dir": tmp_path})(),
    )
    _login(client, db)
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    upload = client.post(
        "/media/upload",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text

    response = client.get(f"/media/{upload.json()['id']}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_pdf_upload_uses_pdf_specific_size_limit(client, db, tmp_path, monkeypatch):
    from app.config import get_settings

    base = get_settings().model_dump()
    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: type(
            "S",
            (),
            {
                **base,
                "upload_dir": tmp_path,
                "max_image_upload_bytes": 10 * 1024,
                "max_pdf_upload_bytes": 16,
            },
        )(),
    )
    _login(client, db)

    pdf_response = client.post(
        "/media/upload",
        files={
            "file": (
                "report.pdf",
                b"%PDF-1.4\n" + (b"x" * 32) + b"\n%%EOF\n",
                "application/pdf",
            ),
        },
    )
    image_response = client.post(
        "/media/upload",
        files={"file": ("photo.png", _png_bytes(), "image/png")},
    )

    assert pdf_response.status_code == 413
    assert pdf_response.json()["error"]["code"] == "file_too_large"
    assert "max 16" in pdf_response.json()["error"]["message"]
    assert image_response.status_code == 200, image_response.text
    assert image_response.json()["kind"] == "image"


def test_pdf_dedup_does_not_satisfy_image_upload(client, db, tmp_path, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: type("S", (), {**get_settings().model_dump(), "upload_dir": tmp_path})(),
    )
    _login(client, db)
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    pdf_response = client.post(
        "/media/upload",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
    )
    assert pdf_response.status_code == 200, pdf_response.text

    image_response = client.post(
        "/media/upload",
        files={"file": ("report.png", pdf_bytes, "image/png")},
    )

    assert image_response.status_code == 422
