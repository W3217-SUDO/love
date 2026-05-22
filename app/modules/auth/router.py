"""Auth routes: bind, login, logout. JSON API for Phase B."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.config import get_settings as get_settings_for_router
from app.db import get_db
from app.errors import AppError, NotFound, ValidationFailed
from app.modules.auth.invite import (
    InviteAlreadyUsed,
    InviteExpired,
    InviteNotFound,
    redeem_invite,
)
from app.modules.auth.models import InviteToken, User
from app.modules.auth.passwords import InvalidHashError, verify_password
from app.modules.auth.schemas import (
    BindInfo,
    BindRequest,
    BindResponse,
    LoginRequest,
    LoginResponse,
    UserPublic,
)
from app.modules.auth.sessions import create_session, revoke_session


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


@router.post("/login", response_model=LoginResponse)
def post_login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    user = db.query(User).filter_by(username=payload.username).one_or_none()
    # Constant-time-ish: always verify against either real or empty hash
    # so timing of unknown-user vs wrong-password is similar.
    stored_hash = user.password_hash if user else ""
    try:
        ok = verify_password(payload.password, stored_hash or "")
    except InvalidHashError:
        ok = False
    if not user or not ok:
        raise AppError(
            "invalid username or password",
            code="invalid_credentials",
            http_status=401,
        )

    settings = get_settings_for_router()
    token = create_session(
        db,
        user_id=user.id,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()

    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_max_age_days * 86400,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    return LoginResponse(
        status="ok",
        user=UserPublic(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            role=user.role,
        ),
    )


@router.post("/logout", status_code=204)
def post_logout(
    response: Response,
    db: Session = Depends(get_db),
    cdsid: str | None = Cookie(default=None),
) -> Response:
    settings = get_settings_for_router()
    if cdsid:
        revoke_session(db, token=cdsid)
        db.commit()
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        samesite="lax",
        secure=settings.cookie_secure,
        httponly=True,
    )
    response.status_code = 204
    return response
