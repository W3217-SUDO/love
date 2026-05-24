from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.modules.cycle.models import Period
from app.modules.cycle.service import PeriodOverlapError, log_bbt, log_period_start
from app.modules.daily_log.catalog import category_of, is_valid_tag
from app.modules.daily_log.models import DailyTag
from app.modules.daily_log.service import get_or_create_entry
from app.modules.health.service import upsert_metric
from app.modules.import_.models import ImportJob
from app.modules.import_.parsers import ParsedImport, parse_apple_health_xml, parse_flo_csv


class ImportError(Exception):
    pass


class UnsupportedImportSource(ImportError):
    pass


def create_import_job(
    db: Session,
    *,
    user_id: int,
    source: str,
    filename: str,
    raw_bytes: bytes,
) -> ImportJob:
    job = ImportJob(
        source=source,
        filename=filename[:255] or "upload",
        status="pending",
        summary_json={},
        created_by_id=user_id,
    )
    db.add(job)
    db.flush()
    job.stored_path = str(_store_import_payload(job=job, raw_bytes=raw_bytes))
    db.flush()
    return job


def run_import_job(db: Session, job_id: int) -> ImportJob:
    job = db.get(ImportJob, job_id)
    if job is None:
        raise ImportError(f"import job {job_id} not found")

    job.status = "processing"
    job.started_at = datetime.now(UTC).replace(tzinfo=None)
    db.flush()
    try:
        raw_bytes = _read_stored_payload(job)
        parsed = _parse(job.source, raw_bytes)
        summary = apply_parsed_import(db, user_id=job.created_by_id, parsed=parsed)
        summary["skipped"] = len(parsed.skipped)
        summary["unmapped"] = len(parsed.unmapped)
        job.summary_json = summary
        job.status = "success"
        job.error_message = None
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.summary_json = job.summary_json or {}
    finally:
        job.finished_at = datetime.now(UTC).replace(tzinfo=None)
        db.flush()
    return job


def process_pending_import_jobs(db: Session, *, limit: int = 10) -> int:
    jobs = list(
        db.execute(
            select(ImportJob)
            .where(ImportJob.status == "pending")
            .order_by(ImportJob.created_at.asc(), ImportJob.id.asc())
            .limit(limit),
        ).scalars(),
    )
    processed = 0
    for job in jobs:
        run_import_job(db, job.id)
        processed += 1
    return processed


def run_pending_import_jobs(db: Session, *, limit: int = 10) -> int:
    return process_pending_import_jobs(db, limit=limit)


def apply_parsed_import(db: Session, *, user_id: int, parsed: ParsedImport) -> dict[str, int]:
    summary = {
        "periods": 0,
        "tags": 0,
        "bbt_readings": 0,
        "health_metrics": 0,
        "skipped": len(parsed.skipped),
    }

    for period in parsed.periods:
        try:
            log_period_start(db, user_id=user_id, start_date=period.start_date)
            summary["periods"] += 1
        except PeriodOverlapError:
            existing = db.execute(
                select(Period).where(
                    Period.user_id == user_id,
                    Period.start_date == period.start_date,
                ),
            ).scalar_one_or_none()
            if existing is not None:
                summary["periods"] += 1
            else:
                summary["skipped"] += 1

    for tag in parsed.tags:
        if not is_valid_tag(tag.tag_key):
            summary["skipped"] += 1
            continue
        entry = get_or_create_entry(db, user_id=user_id, date=tag.date)
        category = category_of(tag.tag_key)
        existing = db.execute(
            select(DailyTag).where(
                DailyTag.entry_id == entry.id,
                DailyTag.category == category,
                DailyTag.tag_key == tag.tag_key,
            ),
        ).scalar_one_or_none()
        if existing is None:
            db.add(
                DailyTag(
                    entry_id=entry.id,
                    category=category,
                    tag_key=tag.tag_key,
                    value=tag.value,
                ),
            )
        elif tag.value is not None:
            existing.value = tag.value
        summary["tags"] += 1

    for reading in parsed.bbt_readings:
        log_bbt(
            db,
            user_id=user_id,
            date=reading.date,
            temp_c=reading.temp_c,
            method=reading.method,
            notes=reading.notes,
        )
        summary["bbt_readings"] += 1

    for metric in parsed.health_metrics:
        upsert_metric(
            db,
            user_id=user_id,
            date=metric.date,
            metric_type=metric.metric_type,
            value=metric.value,
            unit=metric.unit,
            source=metric.source,
            meta_json=metric.meta_json,
        )
        summary["health_metrics"] += 1

    db.flush()
    return summary


def _parse(source: str, raw_bytes: bytes) -> ParsedImport:
    normalized = source.strip().lower()
    if normalized in {"flo", "flo_csv"}:
        return parse_flo_csv(raw_bytes)
    if normalized in {"apple_health", "apple", "health"}:
        return parse_apple_health_xml(raw_bytes)
    raise UnsupportedImportSource(f"unsupported import source: {source}")


def _store_import_payload(*, job: ImportJob, raw_bytes: bytes) -> Path:
    upload_dir = Path(config.get_settings().upload_dir)
    import_dir = upload_dir / "imports"
    import_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(job.filename).suffix[:16] or ".bin"
    path = import_dir / f"{job.id}-{uuid4().hex}{suffix}"
    path.write_bytes(raw_bytes)
    return path


def _read_stored_payload(job: ImportJob) -> bytes:
    if not job.stored_path:
        raise ImportError(f"import job {job.id} has no stored payload")
    path = Path(job.stored_path)
    if not path.is_file():
        raise ImportError(f"import job {job.id} payload not found")
    return path.read_bytes()
