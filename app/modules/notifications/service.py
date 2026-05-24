from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.modules.notifications.models import PushSubscription

log = logging.getLogger(__name__)

MAX_FAILURES = 3


def save_subscription(
    db: Session,
    *,
    user_id: int,
    payload: dict[str, Any],
    user_agent: str | None = None,
) -> PushSubscription:
    endpoint = str(payload.get("endpoint") or "")
    keys = payload.get("keys")
    if not endpoint or not isinstance(keys, dict):
        raise ValueError("subscription payload must include endpoint and keys")

    row = db.query(PushSubscription).filter_by(endpoint=endpoint).one_or_none()
    if row is None:
        row = PushSubscription(
            user_id=user_id,
            endpoint=endpoint,
            keys_json=dict(keys),
            user_agent=user_agent,
        )
        db.add(row)
    else:
        row.user_id = user_id
        row.keys_json = dict(keys)
        row.user_agent = user_agent
        row.fail_count = 0
        row.disabled_at = None
    return row


def subscriptions_for_user(db: Session, *, user_id: int) -> list[PushSubscription]:
    return (
        db.query(PushSubscription)
        .filter(
            PushSubscription.user_id == user_id,
            PushSubscription.disabled_at.is_(None),
        )
        .all()
    )


def mark_subscription_failure(
    db: Session,
    subscription: PushSubscription,
    *,
    max_failures: int = MAX_FAILURES,
) -> PushSubscription:
    subscription.fail_count += 1
    if subscription.fail_count >= max_failures:
        subscription.disabled_at = datetime.utcnow()
    return subscription


def disable_subscription(db: Session, *, user_id: int, endpoint: str) -> bool:
    row = (
        db.query(PushSubscription)
        .filter_by(user_id=user_id, endpoint=endpoint)
        .one_or_none()
    )
    if row is None:
        return False
    row.disabled_at = datetime.utcnow()
    return True


def send_web_push(subscription: PushSubscription, payload: str) -> bool:
    settings = get_settings()
    if not settings.vapid_public_key or not settings.vapid_private_key:
        log.info("web push skipped: VAPID keys are not configured")
        return False

    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        log.warning("web push skipped: pywebpush is not installed")
        return False

    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": subscription.keys_json,
            },
            data=payload,
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject or "mailto:admin@example.com"},
        )
    except WebPushException:
        log.exception("web push failed for subscription %s", subscription.id)
        return False
    return True


def process_due_reminders(db: Session) -> int:
    """M2 placeholder: keep scheduler integration safe until reminder rules land."""
    _ = db
    return 0

