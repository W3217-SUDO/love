from datetime import date
from decimal import Decimal

from app.modules.auth.models import User
from app.modules.cycle.models import BbtReading, Period
from app.modules.daily_log.models import DailyTag
from app.modules.health.models import HealthMetric
from app.modules.import_.parsers import (
    ParsedBbt,
    ParsedHealthMetric,
    ParsedImport,
    ParsedPeriod,
    ParsedTag,
)
from app.modules.import_.service import apply_parsed_import, create_import_job


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


def test_create_import_job_runs_flo_csv_and_marks_success(db):
    user = _user(db)
    raw = b"date,type,value\n2026-05-01,period,start\n2026-05-01,ovulation,positive\n"

    job = create_import_job(
        db,
        user_id=user.id,
        source="flo",
        filename="flo.csv",
        raw_bytes=raw,
    )

    assert job.status == "success"
    assert job.summary_json["periods"] == 1
    assert db.query(Period).filter_by(user_id=user.id, start_date=date(2026, 5, 1)).count() == 1
    assert db.query(DailyTag).filter_by(tag_key="ovu_positive").count() == 1
