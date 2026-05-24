from datetime import date

from sqlalchemy import delete

from app.modules.auth.invite import create_couple_and_invites, redeem_invite
from app.modules.auth.models import AuthSession, Couple, InviteToken, User
from app.modules.media.models import Media
from app.modules.reports.models import Report


def _login_alice(client, db):
    db.execute(delete(AuthSession))
    db.execute(delete(Report))
    db.execute(delete(Media))
    db.execute(delete(InviteToken))
    db.execute(delete(Couple))
    db.execute(delete(User))
    db.flush()
    he_tok, _ = create_couple_and_invites(db, he_name="Alice", she_name="Bob")
    db.flush()
    redeem_invite(db, token=he_tok, plain_password="strongpassword")
    db.flush()
    client.post("/login", json={"username": "alice", "password": "strongpassword"})
    return db.query(User).filter_by(username="alice").one()


def _media(db, owner_id: int) -> Media:
    row = Media(
        owner_id=owner_id,
        kind="pdf",
        sha256=f"{owner_id:064d}",
        mime="application/pdf",
        size_bytes=8,
        original_path=f"/tmp/{owner_id}.pdf",
    )
    db.add(row)
    db.flush()
    return row


def test_reports_page_renders(client, db):
    _login_alice(client, db)

    r = client.get("/reports", headers={"Accept": "text/html"})

    assert r.status_code == 200
    assert "报告" in r.text


def test_create_report_using_existing_media_id(client, db):
    alice = _login_alice(client, db)
    media = _media(db, alice.id)

    r = client.post(
        "/reports",
        data={
            "date": "2026-05-24",
            "title": "年度体检",
            "report_type": "checkup",
            "notes": "PDF 已上传",
            "visibility": "private",
            "media_id": str(media.id),
        },
        follow_redirects=False,
    )

    assert r.status_code in (302, 303, 307)
    report = db.query(Report).one()
    assert report.media_id == media.id
    assert "/reports/" in r.headers["location"]


def test_update_report_with_blank_media_id_clears_attachment(client, db):
    alice = _login_alice(client, db)
    media = _media(db, alice.id)
    report = Report(
        owner_id=alice.id,
        date=date(2026, 5, 24),
        title="年度体检",
        report_type="checkup",
        visibility="private",
        media_id=media.id,
    )
    db.add(report)
    db.flush()

    r = client.post(
        f"/reports/{report.id}",
        data={
            "date": "2026-05-24",
            "title": "年度体检",
            "report_type": "checkup",
            "notes": "",
            "visibility": "private",
            "media_id": "",
        },
        follow_redirects=False,
    )

    assert r.status_code in (302, 303, 307)
    db.refresh(report)
    assert report.media_id is None


def test_update_report_omitted_fields_preserve_existing_values(client, db):
    alice = _login_alice(client, db)
    media = _media(db, alice.id)
    report = Report(
        owner_id=alice.id,
        date=date(2026, 5, 24),
        title="骞村害浣撴",
        report_type="checkup",
        notes="keep notes",
        visibility="shared",
        media_id=media.id,
    )
    db.add(report)
    db.flush()

    r = client.post(
        f"/reports/{report.id}",
        data={"notes": "updated notes"},
        follow_redirects=False,
    )

    assert r.status_code in (302, 303, 307)
    db.refresh(report)
    assert report.date == date(2026, 5, 24)
    assert report.title == "骞村害浣撴"
    assert report.report_type == "checkup"
    assert report.notes == "updated notes"
    assert report.visibility == "shared"
    assert report.media_id == media.id


def test_update_report_blank_title_is_invalid(client, db):
    alice = _login_alice(client, db)
    report = Report(
        owner_id=alice.id,
        date=date(2026, 5, 24),
        title="骞村害浣撴",
        report_type="checkup",
        visibility="private",
    )
    db.add(report)
    db.flush()

    r = client.post(
        f"/reports/{report.id}",
        data={"title": ""},
        follow_redirects=False,
    )

    assert r.status_code == 422
    db.refresh(report)
    assert report.title == "骞村害浣撴"


def test_report_detail_renders_title(client, db):
    alice = _login_alice(client, db)
    report = Report(
        owner_id=alice.id,
        date=date(2026, 5, 24),
        title="年度体检",
        report_type="checkup",
        visibility="private",
    )
    db.add(report)
    db.flush()

    r = client.get(f"/reports/{report.id}", headers={"Accept": "text/html"})

    assert r.status_code == 200
    assert "年度体检" in r.text
