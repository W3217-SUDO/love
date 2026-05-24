from sqlalchemy import delete

from app.modules.auth.invite import create_couple_and_invites, redeem_invite
from app.modules.auth.models import AuthSession, Couple, InviteToken, User
from app.modules.settings.models import UserSettings
from app.modules.settings.service import ensure_settings


def _login(client, db, password="strongpassword"):
    db.execute(delete(AuthSession))
    db.execute(delete(UserSettings))
    db.execute(delete(InviteToken))
    db.execute(delete(Couple))
    db.execute(delete(User))
    db.flush()
    he_token, _ = create_couple_and_invites(db, he_name="Alice", she_name="Bob")
    db.flush()
    redeem_invite(db, token=he_token, plain_password=password)
    db.flush()
    client.post("/login", json={"username": "alice", "password": password})
    return db.query(User).filter_by(username="alice").one()


def test_get_settings_page_renders(client, db):
    _login(client, db)

    response = client.get("/me/settings", headers={"Accept": "text/html"})

    assert response.status_code == 200
    assert "设置" in response.text
    assert "隐私可见性" in response.text


def test_post_visibility_updates_setting(client, db):
    user = _login(client, db)

    response = client.post(
        "/me/settings/visibility",
        data={"data_type": "diary", "visibility": "shared"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/me/settings"
    settings = ensure_settings(db, user.id)
    assert settings.visibility["diary"] == "shared"
