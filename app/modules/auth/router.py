"""Auth routes: bind, login, logout. JSON API + HTML pages for Phase B."""
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, Query, Request, Response, status
from fastapi.responses import HTMLResponse
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
    BindResponse,
    LoginRequest,
    LoginResponse,
    UserPublic,
)
from app.modules.auth.sessions import create_session, revoke_session
from app.rate_limit import limiter
from app.templating import templates
from app.util.http import wants_html


class InviteExpiredError(AppError):
    http_status = status.HTTP_410_GONE
    code = "expired"


class InviteAlreadyUsedError(AppError):
    http_status = status.HTTP_409_CONFLICT
    code = "already_used"


router = APIRouter(tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
def get_login(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request, name="pages/login.html", context={},
    )


@router.get("/bind")
def get_bind_info(
    request: Request,
    token: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    row = db.query(InviteToken).filter_by(token=token).one_or_none()
    if row is None:
        if wants_html(request):
            return templates.TemplateResponse(
                request=request, name="pages/login.html",
                context={"error": "invite token not found"},
                status_code=404,
            )
        raise NotFound("invite token not found")
    if row.used_at is not None:
        if wants_html(request):
            return templates.TemplateResponse(
                request=request, name="pages/login.html",
                context={"error": "invite token already used"},
                status_code=409,
            )
        raise InviteAlreadyUsedError("invite token has already been used")
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        if wants_html(request):
            return templates.TemplateResponse(
                request=request, name="pages/login.html",
                context={"error": "invite token expired"},
                status_code=410,
            )
        raise InviteExpiredError("invite token has expired")
    user = db.query(User).filter_by(id=row.user_id).one()
    if wants_html(request):
        return templates.TemplateResponse(
            request=request, name="pages/bind.html",
            context={
                "token": token,
                "username": user.username,
                "display_name": user.display_name,
                "role": user.role,
            },
        )
    return BindInfo(
        token=token,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
    )


@router.post("/bind")
async def post_bind(
    request: Request,
    db: Session = Depends(get_db),
):
    # Accept either JSON body or form-encoded body.
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        body = await request.json()
        token = body.get("token", "") if isinstance(body, dict) else ""
        password = body.get("password", "") if isinstance(body, dict) else ""
    else:
        form = await request.form()
        token = form.get("token", "")
        password = form.get("password", "")

    if not token or not password or len(password) < 8:
        if wants_html(request):
            return templates.TemplateResponse(
                request=request, name="pages/login.html",
                context={"error": "invalid token or password too short"},
                status_code=422,
            )
        raise ValidationFailed("invalid token or password too short")

    try:
        user = redeem_invite(db, token=token, plain_password=password)
        db.commit()
    except InviteNotFound as exc:
        if wants_html(request):
            return templates.TemplateResponse(
                request=request, name="pages/login.html",
                context={"error": str(exc)},
                status_code=404,
            )
        raise NotFound(str(exc)) from exc
    except InviteAlreadyUsed as exc:
        if wants_html(request):
            return templates.TemplateResponse(
                request=request, name="pages/login.html",
                context={"error": str(exc)},
                status_code=409,
            )
        raise InviteAlreadyUsedError(str(exc)) from exc
    except InviteExpired as exc:
        if wants_html(request):
            return templates.TemplateResponse(
                request=request, name="pages/login.html",
                context={"error": str(exc)},
                status_code=410,
            )
        raise InviteExpiredError(str(exc)) from exc
    except ValueError as exc:
        if wants_html(request):
            return templates.TemplateResponse(
                request=request, name="pages/login.html",
                context={"error": str(exc)},
                status_code=422,
            )
        raise ValidationFailed(str(exc)) from exc

    if wants_html(request):
        return templates.TemplateResponse(
            request=request, name="pages/bind_success.html",
            context={"display_name": user.display_name},
        )
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
@limiter.limit("20/5 minutes")
def post_login(
    request: Request,
    response: Response,
    payload: LoginRequest,
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
