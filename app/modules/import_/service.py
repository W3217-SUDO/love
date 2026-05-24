from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cycle.models import Period
from app.modules.cycle.service import PeriodOverlapError, log_bbt, log_period_start
from app.modules.daily_log.catalog import category_of, is_valid_tag
from app.modules.daily_log.models import DailyTag
from app.modules.daily_log.service import get_or_create_entry
from app.modules.health.models import HealthMetric
from app.modules.import_.models import ImportJob
from app.modules.import_.parsers import ParsedImport, parse_apple_health_xml, parse_flo_csv

_RAW_BYTES_BY_JOB_ID: dict[int, bytes] = {}


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
    _RAW_BYTES_BY_JOB_ID[job.id] = raw_bytes
    run_import_job(db, job.id)
    return job


def run_import_job(db: Session, job_id: int) -> ImportJob:
    job = db.get(ImportJob, job_id)
    if job is None:
        raise ImportError(f"import job {job_id} not found")

    raw_bytes = _RAW_BYTES_BY_JOB_ID.get(job_id)
    if raw_bytes is None:
        return job

    job.status = "processing"
    job.started_at = datetime.now(UTC).replace(tzinfo=None)
    db.flush()
    try:
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
        _RAW_BYTES_BY_JOB_ID.pop(job_id, None)
        db.flush()
    return job


def run_pending_import_jobs(db: Session, *, limit: int = 10) -> int:
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
        if job.id not in _RAW_BYTES_BY_JOB_ID:
            continue
        run_import_job(db, job.id)
        processed += 1
    return processed


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
        _upsert_health_metric(
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


def _upsert_health_metric(
    db: Session,
    *,
    user_id: int,
    date,
    metric_type: str,
    value: Decimal,
    unit: str,
    source: str,
    meta_json: dict | None,
) -> HealthMetric:
    existing = db.execute(
        select(HealthMetric).where(
            HealthMetric.user_id == user_id,
            HealthMetric.date == date,
            HealthMetric.metric_type == metric_type,
            HealthMetric.source == source,
        ),
    ).scalar_one_or_none()
    if existing is not None:
        existing.value = value
        existing.unit = unit
        existing.meta_json = meta_json or {}
        return existing

    metric = HealthMetric(
        user_id=user_id,
        date=date,
        metric_type=metric_type,
        value=value,
        unit=unit,
        source=source,
        meta_json=meta_json or {},
    )
    db.add(metric)
    return metric
