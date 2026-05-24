from datetime import date

import pytest
from sqlalchemy import delete

from app.modules.auth.invite import create_couple_and_invites
from app.modules.auth.models import Couple, InviteToken, User
from app.modules.media.models import Media
from app.modules.reports.service import (
    ReportForbidden,
    ReportNotFound,
    create_report,
    delete_report,
    get_report_for_user,
    list_reports_for_user,
    update_report,
)


def _seed(db):
    db.execute(delete(Media))
    db.execute(delete(InviteToken))
    db.execute(delete(Couple))
    db.execute(delete(User))
    db.flush()
    create_couple_and_invites(db, he_name="Alice", she_name="Bob")
    db.flush()
    alice = db.query(User).filter_by(username="alice").one()
    bob = db.query(User).filter_by(username="bob").one()
    return alice, bob


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


def test_create_report(db):
    alice, _ = _seed(db)
    media = _media(db, alice.id)

    report = create_report(
        db,
        owner_id=alice.id,
        date=date(2026, 5, 24),
        title="体检报告",
        report_type="checkup",
        notes="一切正常",
        visibility="private",
        media_id=media.id,
    )

    assert report.id is not None
    assert report.title == "体检报告"
    assert report.media_id == media.id


def test_update_report_owner_only(db):
    alice, bob = _seed(db)
    report = create_report(
        db,
        owner_id=alice.id,
        date=date(2026, 5, 24),
        title="旧标题",
    )
    db.flush()

    updated = update_report(
        db,
        report_id=report.id,
        user=alice,
        title="新标题",
        visibility="shared",
    )

    assert updated.title == "新标题"
    assert updated.visibility == "shared"
    with pytest.raises(ReportForbidden):
        update_report(db, report_id=report.id, user=bob, title="nope")


def test_delete_report_owner_only(db):
    alice, bob = _seed(db)
    report = create_report(
        db,
        owner_id=alice.id,
        date=date(2026, 5, 24),
        title="删除我",
    )
    db.flush()

    with pytest.raises(ReportForbidden):
        delete_report(db, report_id=report.id, user=bob)
    delete_report(db, report_id=report.id, user=alice)
    db.flush()

    with pytest.raises(ReportNotFound):
        get_report_for_user(db, report_id=report.id, user=alice)


def test_visibility_access_basics(db):
    alice, bob = _seed(db)
    private = create_report(
        db,
        owner_id=alice.id,
        date=date(2026, 5, 24),
        title="私密",
        visibility="private",
    )
    shared = create_report(
        db,
        owner_id=alice.id,
        date=date(2026, 5, 25),
        title="共享",
        visibility="shared",
    )
    db.flush()

    assert get_report_for_user(db, report_id=shared.id, user=bob).id == shared.id
    with pytest.raises(ReportForbidden):
        get_report_for_user(db, report_id=private.id, user=bob)

    bob_titles = {r.title for r in list_reports_for_user(db, user=bob)}
    assert "共享" in bob_titles
    assert "私密" not in bob_titles


def test_unknown_report_raises(db):
    alice, _ = _seed(db)
    with pytest.raises(ReportNotFound):
        get_report_for_user(db, report_id=99999, user=alice)
