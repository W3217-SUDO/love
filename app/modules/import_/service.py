from __future__ import annotations

from datetime import UTC, date, datetime
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
from app.modules.import_.parsers import (
    ImportParseError,
    ParsedImport,
    parse_apple_health_xml,
    parse_flo_csv,
)


class ImportError(Exception):
    pass


class UnsupportedImportSource(ImportError):
    pass


class ImportFileTooLarge(ImportError):
    pass


def create_import_job(
    db: Session,
    *,
    user_id: int,
    source: str,
    filename: str,
    raw_bytes: bytes,
) -> ImportJob:
    max_upload_bytes = config.get_settings().max_import_upload_bytes
    if len(raw_bytes) > max_upload_bytes:
        raise ImportFileTooLarge(f"file is {len(raw_bytes)} bytes; max {max_upload_bytes}")
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

    job.status = "running"
    job.started_at = datetime.now(UTC).replace(tzinfo=None)
    db.flush()
    try:
        raw_bytes = _read_stored_payload(job)
        parsed = _parse(job.source, raw_bytes)
        with db.begin_nested():
            summary = apply_parsed_import(db, user_id=job.created_by_id, parsed=parsed)
        summary["skipped"] = len(parsed.skipped)
        summary["unmapped"] = len(parsed.unmapped)
        job.summary_json = summary
        applied_total = _applied_total(summary)
        if parsed.skipped or parsed.unmapped:
            if applied_total == 0:
                raise ImportError("no importable records found")
            job.status = "partial"
        else:
            job.status = "succeeded"
        job.error_message = None
    except ImportParseError as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.summary_json = job.summary_json or {}
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
    applied_periods: set[date] = set()
    applied_tags: set[tuple[date, str]] = set()
    applied_bbt: set[date] = set()
    applied_metrics: set[tuple[date, str, str]] = set()

    for period in parsed.periods:
        try:
            log_period_start(db, user_id=user_id, start_date=period.start_date)
            applied_periods.add(period.start_date)
        except PeriodOverlapError:
            existing = db.execute(
                select(Period).where(
                    Period.user_id == user_id,
                    Period.start_date == period.start_date,
                ),
            ).scalar_one_or_none()
            if existing is not None:
                applied_periods.add(period.start_date)
            else:
                summary["skipped"] += 1
    summary["periods"] = len(applied_periods)

    for tag in parsed.tags:
        if not is_valid_tag(tag.tag_key):
            summary["skipped"] += 1
            continue
        entry = get_or_create_entry(db, user_id=user_id, date=tag.date)
        category = category_of(tag.tag_key)
        existing_tag = db.execute(
            select(DailyTag).where(
                DailyTag.entry_id == entry.id,
                DailyTag.category == category,
                DailyTag.tag_key == tag.tag_key,
            ),
        ).scalar_one_or_none()
        if existing_tag is None:
            db.add(
                DailyTag(
                    entry_id=entry.id,
                    category=category,
                    tag_key=tag.tag_key,
                    value=tag.value,
                ),
            )
        elif tag.value is not None:
            existing_tag.value = tag.value
        applied_tags.add((tag.date, tag.tag_key))
    summary["tags"] = len(applied_tags)

    for reading in parsed.bbt_readings:
        log_bbt(
            db,
            user_id=user_id,
            date=reading.date,
            temp_c=reading.temp_c,
            method=reading.method,
            notes=reading.notes,
        )
        applied_bbt.add(reading.date)
    summary["bbt_readings"] = len(applied_bbt)

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
            commit=False,
        )
        applied_metrics.add((metric.date, metric.metric_type, metric.source))
    summary["health_metrics"] = len(applied_metrics)

    db.flush()
    return summary


def _applied_total(summary: dict[str, int]) -> int:
    return (
        summary.get("periods", 0)
        + summary.get("tags", 0)
        + summary.get("bbt_readings", 0)
        + summary.get("health_metrics", 0)
    )


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
    max_upload_bytes = config.get_settings().max_import_upload_bytes
    if path.stat().st_size > max_upload_bytes:
        raise ImportFileTooLarge(f"file is {path.stat().st_size} bytes; max {max_upload_bytes}")
    return path.read_bytes()
