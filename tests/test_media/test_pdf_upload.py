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
