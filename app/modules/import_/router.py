from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.db import get_db
from app.deps import get_current_user
from app.errors import FileTooLarge, NotFound, ValidationFailed
from app.modules.auth.models import User
from app.modules.import_.models import ImportJob
from app.modules.import_.service import create_import_job, run_import_job
from app.templating import templates

router = APIRouter(tags=["import"])
READ_CHUNK_BYTES = 1024 * 1024


@router.get("/me/import", response_class=HTMLResponse)
def import_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    jobs = _list_jobs(db, user.id)
    return templates.TemplateResponse(
        request=request,
        name="pages/import.html",
        context={"active": "me", "jobs": jobs},
    )


@router.post("/me/import")
async def import_upload(
    source: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RedirectResponse:
    if source not in {"flo", "apple_health"}:
        raise ValidationFailed("unsupported import source")
    max_upload_bytes = config.get_settings().max_import_upload_bytes
    raw = await _read_upload_with_limit(file, max_upload_bytes=max_upload_bytes)
    if not raw:
        raise ValidationFailed("empty import file")
    filename = file.filename or "upload"
    job = create_import_job(
        db,
        user_id=user.id,
        source=source,
        filename=filename,
        raw_bytes=raw,
    )
    run_import_job(db, job.id)
    db.commit()
    return RedirectResponse(url="/me/import", status_code=303)


async def _read_upload_with_limit(file: UploadFile, *, max_upload_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(READ_CHUNK_BYTES):
        total += len(chunk)
        if total > max_upload_bytes:
            raise FileTooLarge(f"file is {total} bytes; max {max_upload_bytes}")
        chunks.append(chunk)
    return b"".join(chunks)


@router.get("/me/import/_fragment/status/{job_id}", response_class=HTMLResponse)
def import_status_fragment(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    job = db.get(ImportJob, job_id)
    if job is None or job.created_by_id != user.id:
        raise NotFound("import job not found")
    return templates.TemplateResponse(
        request=request,
        name="fragments/import_status.html",
        context={"job": job},
    )


def _list_jobs(db: Session, user_id: int) -> list[ImportJob]:
    return list(
        db.execute(
            select(ImportJob)
            .where(ImportJob.created_by_id == user_id)
            .order_by(ImportJob.created_at.desc(), ImportJob.id.desc())
            .limit(20),
        ).scalars(),
    )
