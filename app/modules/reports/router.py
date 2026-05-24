"""Report HTTP endpoints."""
from datetime import date as date_t

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import Forbidden, NotFound, ValidationFailed
from app.modules.auth.models import User
from app.modules.media.signing import sign_media_url
from app.modules.reports.service import (
    ReportForbidden,
    ReportNotFound,
    create_report,
    delete_report,
    get_report_for_user,
    list_reports_for_user,
    update_report,
)
from app.templating import templates
from app.util.http import wants_html

router = APIRouter(tags=["reports"])


def _form_str(value: object, default: str | None = None) -> str | None:
    return value if isinstance(value, str) else default


def _parse_date(value: str | None) -> date_t:
    return date_t.fromisoformat(value) if value else date_t.today()


def _parse_media_id(value: str | None) -> int | None:
    if not value:
        return None
    return int(value)


def _download_url(media_id: int | None) -> str | None:
    if media_id is None:
        return None
    return f"/media/{media_id}?{sign_media_url(media_id)}"


@router.get("/reports")
def report_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reports = list_reports_for_user(db, user=user)
    if wants_html(request):
        return templates.TemplateResponse(
            request=request,
            name="pages/report_list.html",
            context={"reports": reports, "active": "reports"},
        )
    return [
        {
            "id": report.id,
            "date": report.date.isoformat(),
            "title": report.title,
            "report_type": report.report_type,
            "visibility": report.visibility,
            "media_id": report.media_id,
        }
        for report in reports
    ]


@router.get("/reports/new")
def report_new(
    request: Request,
    user: User = Depends(get_current_user),
):
    return templates.TemplateResponse(
        request=request,
        name="pages/report_edit.html",
        context={"report": None, "active": "reports"},
    )


@router.post("/reports")
async def report_create(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    form = await request.form()
    try:
        report = create_report(
            db,
            owner_id=user.id,
            date=_parse_date(_form_str(form.get("date"))),
            title=_form_str(form.get("title"), "") or "",
            report_type=_form_str(form.get("report_type")) or "general",
            notes=_form_str(form.get("notes")) or None,
            visibility=_form_str(form.get("visibility")) or "private",
            media_id=_parse_media_id(_form_str(form.get("media_id"))),
        )
        db.commit()
    except ReportNotFound as exc:
        raise NotFound(str(exc)) from exc
    except ReportForbidden as exc:
        raise Forbidden(str(exc)) from exc
    except (ValueError, TypeError) as exc:
        raise ValidationFailed(str(exc)) from exc
    return RedirectResponse(url=f"/reports/{report.id}", status_code=303)


@router.get("/reports/{report_id}")
def report_detail(
    report_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        report = get_report_for_user(db, report_id=report_id, user=user)
    except ReportNotFound as exc:
        raise NotFound(str(exc)) from exc
    except ReportForbidden as exc:
        raise Forbidden(str(exc)) from exc
    return templates.TemplateResponse(
        request=request,
        name="pages/report_detail.html",
        context={
            "report": report,
            "download_url": _download_url(report.media_id),
            "is_owner": report.owner_id == user.id,
            "active": "reports",
        },
    )


@router.get("/reports/{report_id}/edit")
def report_edit_get(
    report_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        report = get_report_for_user(db, report_id=report_id, user=user)
    except ReportNotFound as exc:
        raise NotFound(str(exc)) from exc
    except ReportForbidden as exc:
        raise Forbidden(str(exc)) from exc
    if report.owner_id != user.id:
        raise Forbidden("only the owner may edit this report")
    return templates.TemplateResponse(
        request=request,
        name="pages/report_edit.html",
        context={"report": report, "active": "reports"},
    )


@router.post("/reports/{report_id}")
async def report_update(
    report_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    form = await request.form()
    try:
        report = update_report(
            db,
            report_id=report_id,
            user=user,
            date=_parse_date(_form_str(form.get("date"))),
            title=_form_str(form.get("title")) or None,
            report_type=_form_str(form.get("report_type")) or "general",
            notes=_form_str(form.get("notes")) or "",
            visibility=_form_str(form.get("visibility")) or "private",
            media_id=_parse_media_id(_form_str(form.get("media_id"))),
        )
        db.commit()
    except ReportNotFound as exc:
        raise NotFound(str(exc)) from exc
    except ReportForbidden as exc:
        raise Forbidden(str(exc)) from exc
    except (ValueError, TypeError) as exc:
        raise ValidationFailed(str(exc)) from exc
    return RedirectResponse(url=f"/reports/{report.id}", status_code=303)


@router.post("/reports/{report_id}/delete")
def report_delete(
    report_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        delete_report(db, report_id=report_id, user=user)
        db.commit()
    except ReportNotFound as exc:
        raise NotFound(str(exc)) from exc
    except ReportForbidden as exc:
        raise Forbidden(str(exc)) from exc
    return RedirectResponse(url="/reports", status_code=303)
