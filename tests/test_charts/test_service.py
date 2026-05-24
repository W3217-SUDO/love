from datetime import date
from decimal import Decimal

from app.modules.auth.models import User
from app.modules.cycle.service import log_bbt, log_period_end, log_period_start
from app.modules.daily_log.service import toggle_tag
from app.modules.health.service import MetricType, upsert_metric


def _user(db, name="alice"):
    user = User(username=name, display_name=name.title(), role="she")
    db.add(user)
    db.flush()
    return user


def test_build_bbt_series_orders_points_by_date_ascending(db):
    from app.modules.charts.service import build_bbt_series

    user = _user(db)
    for day, temp in [
        (date(2026, 5, 3), "36.61"),
        (date(2026, 5, 1), "36.42"),
        (date(2026, 5, 2), "36.50"),
    ]:
        log_bbt(db, user_id=user.id, date=day, temp_c=Decimal(temp))
        db.flush()

    series = build_bbt_series(db, user.id)

    assert series["kind"] == "bbt"
    assert series["points"] == [
        {"date": "2026-05-01", "value": 36.42},
        {"date": "2026-05-02", "value": 36.5},
        {"date": "2026-05-03", "value": 36.61},
    ]


def test_build_cycle_series_single_period_has_no_cycle_length(db):
    from app.modules.charts.service import build_cycle_series

    user = _user(db)
    log_period_start(db, user_id=user.id, start_date=date(2026, 5, 1))
    log_period_end(
        db,
        user_id=user.id,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 5),
    )
    db.flush()

    series = build_cycle_series(db, user.id)

    assert series == {"kind": "cycle", "points": []}


def test_build_cycle_series_uses_days_between_period_starts(db):
    from app.modules.charts.service import build_cycle_series

    user = _user(db)
    log_period_start(db, user_id=user.id, start_date=date(2026, 5, 1))
    log_period_end(
        db,
        user_id=user.id,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 5),
    )
    log_period_start(db, user_id=user.id, start_date=date(2026, 5, 29))
    db.flush()

    series = build_cycle_series(db, user.id)

    assert series == {
        "kind": "cycle",
        "points": [{"date": "2026-05-01", "value": 28}],
    }


def test_build_tag_frequency_orders_ties_by_tag_key(db):
    from app.modules.charts.service import build_tag_frequency

    user = _user(db)
    toggle_tag(db, user_id=user.id, date=date(2026, 5, 1), tag_key="mood_happy")
    toggle_tag(db, user_id=user.id, date=date(2026, 5, 2), tag_key="mood_calm")
    db.flush()

    series = build_tag_frequency(db, user.id, "mood")

    assert series == {
        "kind": "tags",
        "category": "mood",
        "points": [
            {"tag": "mood_calm", "count": 1},
            {"tag": "mood_happy", "count": 1},
        ],
    }


def test_build_health_series_serializes_decimal_values_and_dates(db):
    from app.modules.charts.service import build_health_series

    user = _user(db)
    upsert_metric(
        db,
        user_id=user.id,
        date=date(2026, 5, 1),
        metric_type=MetricType.RESTING_HEART_RATE,
        value=Decimal("62.50"),
        unit="bpm",
        source="watch",
    )

    series = build_health_series(db, user.id, MetricType.RESTING_HEART_RATE)

    assert series == {
        "kind": "health",
        "metric_type": "resting_heart_rate",
        "points": [
            {
                "date": "2026-05-01",
                "value": 62.5,
                "unit": "bpm",
                "source": "watch",
            },
        ],
    }
