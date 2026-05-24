from app.modules.auth.models import User
from app.modules.notifications.service import save_subscription, subscriptions_for_user


def test_save_subscription_upserts_endpoint_for_user(db):
    user = User(username="alice", display_name="Alice", role="he")
    db.add(user)
    db.flush()
    payload = {
        "endpoint": "https://push.example.test/subscription/1",
        "keys": {
            "p256dh": "p256dh-key",
            "auth": "auth-secret",
        },
    }

    first = save_subscription(db, user_id=user.id, payload=payload, user_agent="first-agent")
    second = save_subscription(db, user_id=user.id, payload=payload, user_agent="second-agent")
    db.flush()

    subscriptions = subscriptions_for_user(db, user_id=user.id)
    assert first.id == second.id
    assert len(subscriptions) == 1
    assert subscriptions[0].endpoint == payload["endpoint"]
    assert subscriptions[0].keys_json == payload["keys"]
    assert subscriptions[0].user_agent == "second-agent"


def test_scheduler_reminder_job_isolates_failures(monkeypatch):
    import app.scheduler as scheduler

    def fail(_db):
        raise RuntimeError("boom")

    monkeypatch.setattr(scheduler, "process_due_reminders", fail)

    scheduler.job_process_due_reminders()
