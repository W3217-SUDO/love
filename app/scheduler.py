"""APScheduler in-process background jobs (backup, cleanup, etc.).

In dev (APP_ENV=dev or test), the scheduler is NOT started by default to
avoid surprise jobs hitting the DB while tests run. Production lifecycle
starts/stops it via app/main.py lifespan.
"""
from __future__ import annotations

import gzip
import logging
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.modules.import_.service import process_pending_import_jobs
from app.modules.media.models import Media
from app.modules.notifications.service import process_due_reminders

log = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _backup_dir(kind: str) -> Path:
    s = get_settings()
    p = Path(s.backup_dir) / kind
    p.mkdir(parents=True, exist_ok=True)
    return p


def job_backup_database() -> None:
    """mysqldump -> /data/backups/db/YYYYMMDD.sql.gz."""
    s = get_settings()
    # DATABASE_URL: mysql+pymysql://user:pwd@host[:port]/dbname?...
    import re
    m = re.match(
        r"mysql\+pymysql://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/([^?]+)",
        s.database_url,
    )
    if not m:
        log.error("backup_database: cannot parse DATABASE_URL")
        return
    user, pwd, host, port, dbname = (
        m.group(1),
        m.group(2),
        m.group(3),
        m.group(4) or "3306",
        m.group(5),
    )
    out_dir = _backup_dir("db")
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"{ts}.sql.gz"
    cmd = [
        "mysqldump", "--single-transaction",
        f"-h{host}", f"-P{port}", f"-u{user}", f"-p{pwd}",
        dbname,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=600)  # noqa: S603
        if proc.returncode != 0:
            log.error("backup_database failed: %s", proc.stderr.decode()[:500])
            return
        with gzip.open(out_path, "wb") as f:
            f.write(proc.stdout)
        log.info(
            "backup_database wrote %s (%d bytes)",
            out_path, out_path.stat().st_size,
        )
        _prune_old_files(out_dir, days=30)
    except Exception:
        log.exception("backup_database crashed")


def job_mirror_uploads() -> None:
    """Naive mirror of UPLOAD_DIR -> BACKUP_DIR/uploads-mirror."""
    s = get_settings()
    src = Path(s.upload_dir)
    dst = _backup_dir("uploads-mirror")
    if not src.exists():
        return
    try:
        for p in src.rglob("*"):
            if p.is_dir():
                continue
            rel = p.relative_to(src)
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists() or target.stat().st_mtime < p.stat().st_mtime:
                shutil.copy2(p, target)
        log.info("mirror_uploads OK src=%s -> dst=%s", src, dst)
    except Exception:
        log.exception("mirror_uploads crashed")


def job_cleanup_orphan_media() -> None:
    """Delete media rows + files older than 7 days that have no link from any consumer table.

    For M1, the only consumer is the daily_log domain (which doesn't have an
    attachments table yet). So this job is currently a no-op for "linked" media
    and only inspects rows. Once future tasks add attachments, the orphan rules
    expand here.
    """
    cutoff = datetime.utcnow() - timedelta(days=7)
    deleted = 0
    with SessionLocal() as db:
        rows = db.execute(
            select(Media).where(Media.created_at < cutoff),
        ).scalars().all()
        for _row in rows:
            # In M1, leave them - once attachments exist, check for references.
            pass
    log.info(
        "cleanup_orphan_media: %d candidates inspected, %d deleted",
        len(rows), deleted,
    )


def job_process_pending_imports() -> None:
    """Process persisted pending import jobs."""
    try:
        with SessionLocal() as db:
            processed = process_pending_import_jobs(db)
            if processed:
                db.commit()
        log.info("process_pending_imports: processed %d jobs", processed)
    except Exception:
        log.exception("process_pending_imports crashed")


def job_process_due_reminders() -> None:
    """Process web-push reminders without taking down other scheduler jobs."""
    try:
        with SessionLocal() as db:
            processed = process_due_reminders(db)
            if processed:
                db.commit()
        log.info("process_due_reminders: processed %d reminders", processed)
    except Exception:
        log.exception("process_due_reminders crashed")


def _prune_old_files(d: Path, *, days: int) -> None:
    cutoff = datetime.utcnow().timestamp() - days * 86400
    for p in d.iterdir():
        if p.is_file() and p.stat().st_mtime < cutoff:
            try:
                p.unlink()
            except Exception:
                log.exception("could not delete %s", p)


def start_scheduler() -> None:
    """Idempotent: starts the scheduler with the M1 job set."""
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    _scheduler.add_job(job_backup_database, "cron", hour=3, minute=0, id="backup_db")
    _scheduler.add_job(job_mirror_uploads, "cron", hour=3, minute=15, id="mirror_uploads")
    _scheduler.add_job(
        job_cleanup_orphan_media, "cron", hour=3, minute=30, id="cleanup_orphan_media",
    )
    _scheduler.add_job(
        job_process_pending_imports,
        "interval",
        minutes=10,
        id="process_pending_imports",
    )
    _scheduler.add_job(
        job_process_due_reminders,
        "interval",
        minutes=5,
        id="process_due_reminders",
    )
    _scheduler.start()
    log.info("scheduler started with %d jobs", len(_scheduler.get_jobs()))


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
