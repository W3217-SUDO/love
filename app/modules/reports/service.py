"""Report CRUD service with private/shared visibility guards."""
from datetime import date as date_t

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.auth.models import Couple, User
from app.modules.media.models import Media
from app.modules.reports.models import Report


class ReportError(Exception):
    pass


class ReportNotFound(ReportError):
    pass


class ReportForbidden(ReportError):
    pass


def _partner_of(db: Session, user_id: int) -> int | None:
    couple = db.execute(
        select(Couple).where(
            or_(Couple.user_a_id == user_id, Couple.user_b_id == user_id),
        ),
    ).scalar_one_or_none()
    if couple is None:
        return None
    return couple.user_b_id if couple.user_a_id == user_id else couple.user_a_id


def _can_access(db: Session, report: Report, user: User) -> bool:
    if report.owner_id == user.id:
        return True
    return report.visibility == "shared" and _partner_of(db, report.owner_id) == user.id


def _validate_visibility(visibility: str) -> str:
    if visibility not in ("private", "shared"):
        raise ValueError(f"invalid visibility: {visibility!r}")
    return visibility


def _validate_media(db: Session, *, media_id: int | None, owner_id: int) -> int | None:
    if media_id is None:
        return None
    media = db.execute(select(Media).where(Media.id == media_id)).scalar_one_or_none()
    if media is None:
        raise ReportNotFound(f"media {media_id} not found")
    if media.owner_id != owner_id:
        raise ReportForbidden("media owner mismatch")
    return media_id


def create_report(
    db: Session,
    *,
    owner_id: int,
    date: date_t,
    title: str,
    report_type: str | None = "general",
    notes: str | None = None,
    visibility: str = "private",
    media_id: int | None = None,
) -> Report:
    if not title or not title.strip():
        raise ValueError("title cannot be empty")
    report = Report(
        owner_id=owner_id,
        date=date,
        title=title.strip(),
        report_type=(report_type or "general").strip() or "general",
        notes=notes,
        visibility=_validate_visibility(visibility),
        media_id=_validate_media(db, media_id=media_id, owner_id=owner_id),
    )
    db.add(report)
    db.flush()
    return report


def get_report_for_user(db: Session, *, report_id: int, user: User) -> Report:
    report = db.execute(
        select(Report).where(Report.id == report_id),
    ).scalar_one_or_none()
    if report is None:
        raise ReportNotFound(f"report {report_id} not found")
    if not _can_access(db, report, user):
        raise ReportForbidden("you do not have access to this report")
    return report


def update_report(
    db: Session,
    *,
    report_id: int,
    user: User,
    date: date_t | None = None,
    title: str | None = None,
    report_type: str | None = None,
    notes: str | None = None,
    visibility: str | None = None,
    media_id: int | None = None,
) -> Report:
    report = db.execute(
        select(Report).where(Report.id == report_id),
    ).scalar_one_or_none()
    if report is None:
        raise ReportNotFound(f"report {report_id} not found")
    if report.owner_id != user.id:
        raise ReportForbidden("only the owner may edit this report")
    if date is not None:
        report.date = date
    if title is not None:
        if not title.strip():
            raise ValueError("title cannot be empty")
        report.title = title.strip()
    if report_type is not None:
        report.report_type = report_type.strip() or "general"
    if notes is not None:
        report.notes = notes
    if visibility is not None:
        report.visibility = _validate_visibility(visibility)
    if media_id is not None:
        report.media_id = _validate_media(db, media_id=media_id, owner_id=user.id)
    return report


def delete_report(db: Session, *, report_id: int, user: User) -> None:
    report = db.execute(
        select(Report).where(Report.id == report_id),
    ).scalar_one_or_none()
    if report is None:
        raise ReportNotFound(f"report {report_id} not found")
    if report.owner_id != user.id:
        raise ReportForbidden("only the owner may delete this report")
    db.delete(report)


def list_reports_for_user(
    db: Session,
    *,
    user: User,
    limit: int = 50,
    offset: int = 0,
) -> list[Report]:
    partner_id = _partner_of(db, user.id)
    if partner_id is None:
        stmt = select(Report).where(Report.owner_id == user.id)
    else:
        stmt = select(Report).where(
            or_(
                Report.owner_id == user.id,
                ((Report.owner_id == partner_id) & (Report.visibility == "shared")),
            ),
        )
    rows = db.execute(
        stmt.order_by(Report.date.desc(), Report.created_at.desc())
        .limit(limit)
        .offset(offset),
    ).scalars().all()
    return list(rows)
