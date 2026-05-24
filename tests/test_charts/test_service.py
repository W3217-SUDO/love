from datetime import date
from decimal import Decimal

from app.modules.auth.models import User
from app.modules.cycle.service import log_bbt


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
