from types import SimpleNamespace

from sqlalchemy import delete

from app.modules.auth.invite import create_couple_and_invites, redeem_invite
from app.modules.auth.models import AuthSession, Couple, InviteToken, User
from app.modules.notifications.models import PushSubscription


def _login(client, db, password="strongpassword"):
    db.execute(delete(PushSubscription))
    db.execute(delete(AuthSession))
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


def test_vapid_public_key_endpoint_returns_configured_key(client, db, monkeypatch):
    from app.modules.notifications import router

    _login(client, db)

    monkeypatch.setattr(
        router,
        "get_settings_for_router",
        lambda: SimpleNamespace(vapid_public_key="public-test-key"),
    )

    response = client.get("/notifications/vapid-public-key")

    assert response.status_code == 200
    assert response.json() == {"publicKey": "public-test-key"}


def test_vapid_public_key_requires_current_user(client):
    response = client.get("/notifications/vapid-public-key")

    assert response.status_code == 401


def test_vapid_public_key_returns_empty_when_unconfigured_for_current_user(
    client,
    db,
    monkeypatch,
):
    from app.modules.notifications import router

    _login(client, db)
    monkeypatch.setattr(
        router,
        "get_settings_for_router",
        lambda: SimpleNamespace(vapid_public_key=None),
    )

    response = client.get("/notifications/vapid-public-key")

    assert response.status_code == 200
    assert response.json() == {"publicKey": ""}


def test_post_subscription_saves_for_current_user(client, db):
    user = _login(client, db)
    payload = {
        "endpoint": "https://push.example.test/router",
        "keys": {
            "p256dh": "p256dh-key",
            "auth": "auth-secret",
        },
    }

    response = client.post(
        "/notifications/subscriptions",
        json=payload,
        headers={"User-Agent": "pytest-browser"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    row = db.query(PushSubscription).filter_by(user_id=user.id).one()
    assert row.endpoint == payload["endpoint"]
    assert row.keys_json == payload["keys"]
    assert row.user_agent == "pytest-browser"


def test_disable_subscription_requires_current_user(client):
    response = client.post(
        "/notifications/subscriptions/disable",
        json={"endpoint": "https://push.example.test/router"},
    )

    assert response.status_code == 401


def test_disable_subscription_disables_current_users_endpoint_only(client, db):
    user = _login(client, db)
    other = User(username="carol", display_name="Carol", role="she")
    db.add(other)
    db.flush()
    endpoint = "https://push.example.test/shared"
    payload = {
        "endpoint": endpoint,
        "keys": {
            "p256dh": "p256dh-key",
            "auth": "auth-secret",
        },
    }
    client.post("/notifications/subscriptions", json=payload)
    own_subscription = db.query(PushSubscription).filter_by(user_id=user.id).one()
    other_subscription = PushSubscription(
        user_id=other.id,
        endpoint="https://push.example.test/other",
        keys_json=payload["keys"],
    )
    db.add(other_subscription)
    db.flush()

    response = client.post(
        "/notifications/subscriptions/disable",
        json={"endpoint": endpoint},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert own_subscription.disabled_at is not None
    assert other_subscription.disabled_at is None
