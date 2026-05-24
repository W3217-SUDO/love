from datetime import date
from decimal import Decimal

from app.modules.auth.models import User
from app.modules.cycle.models import BbtReading, Period
from app.modules.daily_log.models import DailyTag
from app.modules.health.models import HealthMetric
from app.modules.import_ import service as import_service
from app.modules.import_.parsers import (
    ParsedBbt,
    ParsedHealthMetric,
    ParsedImport,
    ParsedPeriod,
    ParsedTag,
)
from app.modules.import_.service import (
    ImportFileTooLarge,
    apply_parsed_import,
    create_import_job,
    process_pending_import_jobs,
    run_import_job,
)


def _user(db, name="alice"):
    user = User(username=name, display_name=name.title(), role="she")
    db.add(user)
    db.flush()
    return user


def test_apply_parsed_import_upserts_without_duplicates(db):
    user = _user(db)
    parsed = ParsedImport(
        periods=[ParsedPeriod(start_date=date(2026, 5, 1))],
        tags=[ParsedTag(date=date(2026, 5, 1), tag_key="sym_cramps")],
        bbt_readings=[ParsedBbt(date=date(2026, 5, 2), temp_c=Decimal("36.52"))],
        health_metrics=[
            ParsedHealthMetric(
                date=date(2026, 5, 2),
                metric_type="resting_heart_rate",
                value=Decimal("61"),
                unit="bpm",
            ),
        ],
    )

    first = apply_parsed_import(db, user_id=user.id, parsed=parsed)
    second = apply_parsed_import(db, user_id=user.id, parsed=parsed)
    db.flush()

    assert first["periods"] == 1
    assert second["periods"] == 1
    assert db.query(Period).count() == 1
    assert db.query(DailyTag).count() == 1
    assert db.query(BbtReading).count() == 1
    assert db.query(HealthMetric).count() == 1


def test_apply_parsed_import_counts_unique_applied_rows(db):
    user = _user(db)
    parsed = ParsedImport(
        tags=[
            ParsedTag(date=date(2026, 5, 1), tag_key="sym_cramps"),
            ParsedTag(date=date(2026, 5, 1), tag_key="sym_cramps"),
        ],
        health_metrics=[
            ParsedHealthMetric(
                date=date(2026, 5, 2),
                metric_type="resting_heart_rate",
                value=Decimal("61"),
                unit="bpm",
            ),
            ParsedHealthMetric(
                date=date(2026, 5, 2),
                metric_type="resting_heart_rate",
                value=Decimal("62"),
                unit="bpm",
            ),
        ],
    )

    summary = apply_parsed_import(db, user_id=user.id, parsed=parsed)
    db.flush()

    assert summary["tags"] == 1
    assert summary["health_metrics"] == 1
    assert db.query(DailyTag).count() == 1
    assert db.query(HealthMetric).count() == 1


def test_create_import_job_rejects_payload_above_configured_limit(db, tmp_path, monkeypatch):
    from app import config

    settings = config.get_settings()
    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: type(
            "S",
            (),
            {**settings.model_dump(), "upload_dir": tmp_path, "max_import_upload_bytes": 8},
        )(),
    )
    user = _user(db)

    try:
        create_import_job(
            db,
            user_id=user.id,
            source="flo",
            filename="flo.csv",
            raw_bytes=b"date,type,value\n",
        )
    except ImportFileTooLarge as exc:
        assert "max 8" in str(exc)
    else:
        raise AssertionError("expected ImportFileTooLarge")

    assert db.query(Period).count() == 0


def test_create_import_job_persists_flo_csv_payload_and_run_marks_success(
    db,
    tmp_path,
    monkeypatch,
):
    from app import config

    settings = config.get_settings()
    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: type("S", (), {**settings.model_dump(), "upload_dir": tmp_path})(),
    )
    user = _user(db)
    raw = b"date,type,value\n2026-05-01,period,start\n2026-05-01,ovulation,positive\n"

    job = create_import_job(
        db,
        user_id=user.id,
        source="flo",
        filename="flo.csv",
        raw_bytes=raw,
    )

    assert job.status == "pending"
    assert job.stored_path is not None
    assert job.summary_json == {}
    assert db.query(Period).count() == 0

    run_import_job(db, job.id)

    assert job.status == "succeeded"
    assert job.summary_json["periods"] == 1
    assert db.query(Period).filter_by(user_id=user.id, start_date=date(2026, 5, 1)).count() == 1
    assert db.query(DailyTag).filter_by(tag_key="ovu_positive").count() == 1


def test_run_pending_import_jobs_processes_persisted_payload(db, tmp_path, monkeypatch):
    from app import config

    settings = config.get_settings()
    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: type("S", (), {**settings.model_dump(), "upload_dir": tmp_path})(),
    )
    user = _user(db)
    raw = b"date,type,value\n2026-05-03,period,start\n"
    job = create_import_job(
        db,
        user_id=user.id,
        source="flo",
        filename="flo.csv",
        raw_bytes=raw,
    )
    db.flush()

    processed = process_pending_import_jobs(db)

    assert processed == 1
    assert job.status == "succeeded"
    assert job.summary_json["periods"] == 1
    assert db.query(Period).filter_by(user_id=user.id, start_date=date(2026, 5, 3)).count() == 1


def test_run_import_job_marks_malformed_file_failed(db, tmp_path, monkeypatch):
    from app import config

    settings = config.get_settings()
    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: type("S", (), {**settings.model_dump(), "upload_dir": tmp_path})(),
    )
    user = _user(db)
    job = create_import_job(
        db,
        user_id=user.id,
        source="flo",
        filename="flo.csv",
        raw_bytes=b"when,kind,note\n2026-05-01,period,start\n",
    )

    run_import_job(db, job.id)

    assert job.status == "failed"
    assert "missing required columns" in job.error_message
    assert db.query(Period).count() == 0


def test_run_import_job_rolls_back_apply_failure(db, tmp_path, monkeypatch):
    from app import config

    settings = config.get_settings()
    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: type("S", (), {**settings.model_dump(), "upload_dir": tmp_path})(),
    )
    user = _user(db)
    raw = b"date,type,value\n2026-05-01,symptom,cramps\n2026-05-02,period,start\n"
    job = create_import_job(
        db,
        user_id=user.id,
        source="flo",
        filename="flo.csv",
        raw_bytes=raw,
    )

    def fail_after_tag(*args, **kwargs):
        raise RuntimeError("forced apply failure")

    monkeypatch.setattr(import_service, "log_period_start", fail_after_tag)

    run_import_job(db, job.id)

    assert job.status == "failed"
    assert "forced apply failure" in job.error_message
    assert db.query(DailyTag).count() == 0
    assert db.query(Period).count() == 0
