from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config import get_settings as get_settings_for_router
from app.db import get_db
from app.deps import get_current_user
from app.errors import ValidationFailed
from app.modules.auth.models import User
from app.modules.notifications.service import disable_subscription, save_subscription

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/vapid-public-key")
def vapid_public_key() -> dict[str, str]:
    return {"publicKey": get_settings_for_router().vapid_public_key or ""}


@router.post("/subscriptions")
async def create_subscription(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    body = await request.json()
    if not isinstance(body, dict):
        raise ValidationFailed("subscription payload must be a JSON object")
    try:
        save_subscription(
            db,
            user_id=user.id,
            payload=body,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise ValidationFailed(str(exc)) from exc
    db.commit()
    return {"status": "ok"}


@router.post("/subscriptions/disable")
async def disable_current_subscription(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    body: Any = await request.json()
    endpoint = body.get("endpoint") if isinstance(body, dict) else None
    if not endpoint:
        raise ValidationFailed("endpoint is required")
    disable_subscription(db, user_id=user.id, endpoint=str(endpoint))
    db.commit()
    return {"status": "ok"}

