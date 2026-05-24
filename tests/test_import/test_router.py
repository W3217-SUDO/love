from sqlalchemy import delete

from app.modules.auth.invite import create_couple_and_invites, redeem_invite
from app.modules.auth.models import AuthSession, Couple, InviteToken, User
from app.modules.import_.models import ImportJob


def _login_alice(client, db, password="strongpassword"):
    db.execute(delete(AuthSession))
    db.execute(delete(ImportJob))
    db.execute(delete(InviteToken))
    db.execute(delete(Couple))
    db.execute(delete(User))
    db.flush()
    he_token, _ = create_couple_and_invites(db, he_name="Alice", she_name="Bob")
    db.flush()
    redeem_invite(db, token=he_token, plain_password=password)
    db.flush()
    user = db.query(User).filter_by(username="alice").one()
    response = client.post("/login", json={"username": "alice", "password": password})
    assert response.status_code == 200
    return user


def test_import_page_renders(client, db):
    _login_alice(client, db)

    response = client.get("/me/import", headers={"Accept": "text/html"})

    assert response.status_code == 200
    assert "导入数据" in response.text
    assert "Flo CSV" in response.text
    assert "Apple Health" in response.text


def test_import_upload_creates_successful_job(client, db):
    _login_alice(client, db)

    response = client.post(
        "/me/import",
        data={"source": "flo"},
        files={"file": ("flo.csv", b"date,type,value\n2026-05-01,period,start\n", "text/csv")},
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)
    job = db.query(ImportJob).one()
    assert job.status == "succeeded"


def test_import_upload_rejects_files_above_configured_limit(client, db, monkeypatch, tmp_path):
    from app import config

    _login_alice(client, db)
    settings = config.get_settings()
    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: type(
            "S",
            (),
            {**settings.model_dump(), "upload_dir": tmp_path, "max_import_upload_bytes": 8},
        )(),
    )

    response = client.post(
        "/me/import",
        data={"source": "flo"},
        files={"file": ("flo.csv", b"date,type,value\n", "text/csv")},
        follow_redirects=False,
    )

    assert response.status_code == 413
    assert db.query(ImportJob).count() == 0


def test_import_status_fragment_renders(client, db):
    user = _login_alice(client, db)
    job = ImportJob(
        source="flo",
        filename="flo.csv",
        status="succeeded",
        summary_json={"periods": 1},
        created_by_id=user.id,
    )
    db.add(job)
    db.flush()

    response = client.get(f"/me/import/_fragment/status/{job.id}", headers={"Accept": "text/html"})

    assert response.status_code == 200
    assert "成功" in response.text
    assert "flo.csv" in response.text
