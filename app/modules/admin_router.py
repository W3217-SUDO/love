"""Admin tools — account switching for the male partner (role=he) to view the female side."""
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.errors import Forbidden, NotFound
from app.modules.auth.models import User
from app.modules.auth.sessions import create_session, revoke_session

router = APIRouter(tags=["admin"])


@router.get("/admin/login-as/{user_id}")
def login_as(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Switch the cdsid cookie to a session for `user_id`.

    Restricted: the caller must currently have role=he (the male partner = admin).
    The target user must exist. Old session is revoked.

    UX: one click in the browser → become the other account. Useful for the male
    partner to preview what the female side sees while debugging UX.
    """
    # Allow symmetric switching: anyone in the closed 2-person system can
    # switch to the other user (or no-op when target == self).
    if current.id == user_id:
        return RedirectResponse(url="/", status_code=303)

    target = db.query(User).filter_by(id=user_id).one_or_none()
    if target is None:
        raise NotFound(f"user {user_id} not found")

    # revoke old session
    old = request.cookies.get(get_settings().session_cookie_name)
    if old:
        try:
            revoke_session(db, token=old)
        except Exception:
            pass

    new_token = create_session(
        db, user_id=target.id,
        ip=(request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()

    settings = get_settings()
    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie(
        key=settings.session_cookie_name,
        value=new_token,
        max_age=settings.session_max_age_days * 86400,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    return resp


@router.get("/admin/whoami")
def whoami(current: User = Depends(get_current_user)):
    """Quick sanity check: who am I currently logged in as?"""
    return {
        "id": current.id,
        "username": current.username,
        "display_name": current.display_name,
        "role": current.role,
    }
