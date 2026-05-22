"""Auth routes: bind, login, logout. JSON API for Phase B."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError, NotFound, ValidationFailed
from app.modules.auth.invite import (
    InviteAlreadyUsed,
    InviteExpired,
    InviteNotFound,
    redeem_invite,
)
from app.modules.auth.models import InviteToken, User
from app.modules.auth.schemas import BindInfo, BindRequest, BindResponse, UserPublic


class InviteExpiredError(AppError):
    http_status = status.HTTP_410_GONE
    code = "expired"


class InviteAlreadyUsedError(AppError):
    http_status = status.HTTP_409_CONFLICT
    code = "already_used"


router = APIRouter(tags=["auth"])


@router.get("/bind", response_model=BindInfo)
def get_bind_info(
    token: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> BindInfo:
    row = db.query(InviteToken).filter_by(token=token).one_or_none()
    if row is None:
        raise NotFound("invite token not found")
    if row.used_at is not None:
        raise InviteAlreadyUsedError("invite token has already been used")
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise InviteExpiredError("invite token has expired")
    user = db.query(User).filter_by(id=row.user_id).one()
    return BindInfo(
        token=token,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
    )


@router.post("/bind", response_model=BindResponse)
def post_bind(
    payload: BindRequest,
    db: Session = Depends(get_db),
) -> BindResponse:
    try:
        user = redeem_invite(
            db, token=payload.token, plain_password=payload.password,
        )
        db.commit()
    except InviteNotFound as exc:
        raise NotFound(str(exc)) from exc
    except InviteAlreadyUsed as exc:
        raise InviteAlreadyUsedError(str(exc)) from exc
    except InviteExpired as exc:
        raise InviteExpiredError(str(exc)) from exc
    except ValueError as exc:  # password too short etc.
        raise ValidationFailed(str(exc)) from exc

    return BindResponse(
        status="ok",
        user=UserPublic(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            role=user.role,
        ),
    )
