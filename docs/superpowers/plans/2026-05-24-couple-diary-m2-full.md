# Couple Diary M2 Full Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the M2 full Flo-like release: polished mobile UI, settings, charts, import, health metrics, reports/PDF, push reminders, and production deployment.

**Architecture:** Keep the current FastAPI + Jinja2 + SQLAlchemy module style. Add focused modules for settings, health, charts, reports, import, and notifications; keep cross-module access behind service functions. Ship in small commits with tests before implementation.

**Tech Stack:** FastAPI, Jinja2, HTMX-style fragments, SQLAlchemy, Alembic, MariaDB, APScheduler, Pillow, PyMySQL, pytest, ruff, mypy.

---

## Scope Check

The M2 spec intentionally covers several independent subsystems. Implement it as
one release, but execute it as eight independent batches. Each batch must pass
its own tests and commit before moving to the next batch.

Batch order:

1. Frontend foundation and Chinese text repair.
2. Settings and privacy.
3. Health metrics and predictor evidence.
4. Charts.
5. Reports and PDF media.
6. Import center.
7. Web Push and reminders.
8. Integration, deployment, and production smoke tests.

## File Structure

Create these modules:

- `app/modules/settings/models.py`: user settings, visibility defaults, notification preferences.
- `app/modules/settings/service.py`: settings creation, updates, visibility decisions.
- `app/modules/settings/router.py`: `/me/settings`, settings form posts, export entry point.
- `app/modules/health/models.py`: health metric rows.
- `app/modules/health/service.py`: health metric upsert/list helpers.
- `app/modules/health/router.py`: health metric API where needed by charts/import.
- `app/modules/charts/service.py`: chart series builders.
- `app/modules/charts/router.py`: `/charts` pages and JSON endpoints.
- `app/modules/reports/models.py`: report metadata linked to media.
- `app/modules/reports/service.py`: report CRUD and visibility.
- `app/modules/reports/router.py`: `/reports` HTML routes.
- `app/modules/import_/models.py`: import job status and summary.
- `app/modules/import_/parsers.py`: Flo CSV and Apple Health XML parsers.
- `app/modules/import_/service.py`: job lifecycle and idempotent writes.
- `app/modules/import_/router.py`: upload page and status fragments.
- `app/modules/notifications/models.py`: push subscriptions and reminder preferences if not stored in settings.
- `app/modules/notifications/service.py`: subscription handling, reminder decision, push send wrapper.
- `app/modules/notifications/router.py`: subscription endpoints.

Modify these existing files:

- `app/main.py`: include new routers.
- `app/scheduler.py`: schedule import job processing and reminder checks.
- `app/config.py`: add upload/import/push settings.
- `pyproject.toml`: add required libraries for XML parsing and Web Push.
- `app/modules/media/pipeline.py`: accept PDFs with configured limits.
- `app/modules/media/router.py`: serve PDF previews/downloads safely.
- `app/modules/cycle/predictor/*`: add mucus and health evidence.
- `app/modules/timeline/service.py`: include health/report/chart summaries.
- `app/modules/timeline/router.py`: pass enhanced dashboard context.
- `app/modules/daily_log/catalog.py`: repair Chinese labels and add predictor-friendly tag constants.
- `app/templates/**/*.html`: repair Chinese and polish mobile pages.
- `app/static/css/theme.css`: reusable page, card, chart, form, and status styles.
- `app/static/js/app.js`: save feedback, confirm dialogs, notification subscription helper.
- `app/static/sw.js`: push notification handler.
- `alembic/versions/*.py`: migrations for M2 tables and columns.

Create tests:

- `tests/test_settings/*`
- `tests/test_health/*`
- `tests/test_charts/*`
- `tests/test_reports/*`
- `tests/test_import/*`
- `tests/test_notifications/*`
- New UI regression tests in `tests/test_ui/*`

---

### Task 1: Frontend Foundation And Chinese Repair

**Files:**
- Modify: `app/templates/base.html`
- Modify: `app/templates/components/nav.html`
- Modify: `app/templates/pages/today.html`
- Modify: `app/templates/pages/log_sheet.html`
- Modify: `app/templates/pages/calendar.html`
- Modify: `app/templates/pages/cycle_log.html`
- Modify: `app/templates/pages/bbt_log.html`
- Modify: `app/modules/daily_log/catalog.py`
- Modify: `app/static/css/theme.css`
- Modify: `app/static/js/app.js`
- Modify: `README.md`
- Test: `tests/test_ui/test_chinese_text.py`
- Test: `tests/test_daily_log/test_catalog.py`

- [ ] **Step 1: Write failing UI text tests**

Create `tests/test_ui/test_chinese_text.py`:

```python
from app.modules.daily_log.catalog import CATEGORIES, TAG_BY_KEY


def test_daily_catalog_has_readable_chinese_labels():
    labels = [category.label for category in CATEGORIES]
    assert "心情" in labels
    assert "症状" in labels
    assert "排卵测试" in labels
    assert TAG_BY_KEY["mood_happy"].label == "开心"
    assert TAG_BY_KEY["ovu_positive"].label == "阳性"


def test_today_page_uses_readable_chinese(client, logged_in_user):
    response = client.get("/")
    assert response.status_code == 200
    assert "今天" in response.text
    assert "快捷记录" in response.text
    assert "今天的标签" in response.text
    assert "浠婂ぉ" not in response.text


def test_bottom_nav_uses_readable_chinese(client, logged_in_user):
    response = client.get("/")
    assert response.status_code == 200
    for text in ["今天", "日历", "记录", "经期", "体温", "我们"]:
        assert text in response.text
    assert "馃" not in response.text
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_ui/test_chinese_text.py tests/test_daily_log/test_catalog.py -v
```

Expected: at least `test_daily_catalog_has_readable_chinese_labels` and
`test_today_page_uses_readable_chinese` fail because existing labels are
mojibake.

- [ ] **Step 3: Repair the daily tag catalog**

Replace `CATEGORIES` and `TAGS` in `app/modules/daily_log/catalog.py` with
readable UTF-8 Chinese labels. Keep existing tag keys stable. Use this category
set:

```python
CATEGORIES: tuple[Category, ...] = (
    Category(key="sex", label="亲密与性欲", order=10),
    Category(key="mood", label="心情", order=20),
    Category(key="symptoms", label="症状", order=30),
    Category(key="discharge", label="分泌物", order=40),
    Category(key="digestion", label="消化", order=50),
    Category(key="ovulation", label="排卵测试", order=60),
    Category(key="other", label="生活", order=70),
)
```

Keep keys such as `ovu_positive`, `disch_egg_white`, and `mood_happy` unchanged
because existing rows reference them.

- [ ] **Step 4: Repair core templates**

Update templates so the visible text contains readable Chinese:

- `today.html`: title "今天", subtitle greeting, "快捷记录", "今日标签", "基础体温".
- `log_sheet.html`: title "今天的记录", subtitle "点击标签会自动保存".
- `calendar.html`: title "日历", weekdays "日 一 二 三 四 五 六", legend "经期 / 预测经期 / 易孕期".
- `nav.html`: labels "今天 / 日历 / 记录 / 经期 / 体温 / 我们".
- `cycle_log.html`: form labels for start/end date and delete actions.
- `bbt_log.html`: form labels for temperature/date/time/method/delete actions.

- [ ] **Step 5: Add reusable frontend states**

Extend `app/static/css/theme.css` with these classes:

```css
.page-header { margin-bottom: var(--space-4); }
.page-title { font-size: 28px; font-weight: 750; margin: 0 0 var(--space-1); }
.action-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-3); }
.empty-state { color: var(--color-text-soft); padding: var(--space-4); border: 1px dashed var(--color-border); border-radius: var(--radius-md); background: var(--color-surface-alt); }
.save-state { font-size: 13px; color: var(--color-text-soft); min-height: 20px; }
.danger { color: var(--color-error); }
.btn-danger { background: var(--color-error); color: #fff; }
@media (max-width: 420px) { .action-grid { grid-template-columns: 1fr; } }
```

- [ ] **Step 6: Add frontend confirmation helper**

In `app/static/js/app.js`, add a delegated submit guard:

```javascript
document.addEventListener("submit", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) return;
  const message = form.dataset.confirm;
  if (message && !window.confirm(message)) {
    event.preventDefault();
  }
});
```

- [ ] **Step 7: Run focused tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_ui/test_chinese_text.py tests/test_daily_log/test_catalog.py tests/test_timeline tests/test_cycle -v
```

Expected: all selected tests pass.

- [ ] **Step 8: Commit**

Run:

```powershell
git add app/templates app/modules/daily_log/catalog.py app/static/css/theme.css app/static/js/app.js README.md tests/test_ui/test_chinese_text.py tests/test_daily_log/test_catalog.py
git commit -m "fix(ui): repair chinese text and mobile states"
```

---

### Task 2: Settings And Privacy Module

**Files:**
- Create: `app/modules/settings/__init__.py`
- Create: `app/modules/settings/models.py`
- Create: `app/modules/settings/service.py`
- Create: `app/modules/settings/router.py`
- Create: `app/templates/pages/settings.html`
- Create: `alembic/versions/0009_user_settings.py`
- Modify: `app/main.py`
- Modify: `app/templates/pages/me.html`
- Test: `tests/test_settings/test_models.py`
- Test: `tests/test_settings/test_service.py`
- Test: `tests/test_settings/test_router.py`

- [ ] **Step 1: Write failing model and service tests**

Create `tests/test_settings/test_service.py`:

```python
from app.modules.settings.service import (
    DATA_TYPES,
    Visibility,
    can_partner_view,
    ensure_settings,
    set_visibility,
)


def test_ensure_settings_creates_defaults(db, user):
    settings = ensure_settings(db, user_id=user.id)
    assert settings.user_id == user.id
    assert settings.theme == "system"
    assert settings.visibility["diary"] == "private"
    assert settings.visibility["cycle"] == "shared"


def test_set_visibility_persists_known_type(db, user):
    settings = ensure_settings(db, user_id=user.id)
    set_visibility(db, settings=settings, data_type="diary", visibility=Visibility.SHARED)
    db.refresh(settings)
    assert settings.visibility["diary"] == "shared"


def test_set_visibility_rejects_unknown_type(db, user):
    settings = ensure_settings(db, user_id=user.id)
    try:
        set_visibility(db, settings=settings, data_type="unknown", visibility=Visibility.SHARED)
    except ValueError as exc:
        assert "unknown data type" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_can_partner_view_uses_default_visibility(db, user):
    settings = ensure_settings(db, user_id=user.id)
    assert can_partner_view(settings, "cycle") is True
    assert can_partner_view(settings, "diary") is False
    assert set(DATA_TYPES) >= {"diary", "daily_log", "cycle", "bbt", "trip", "report", "health"}
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_settings/test_service.py -v
```

Expected: import error because `app.modules.settings` does not exist.

- [ ] **Step 3: Add settings model**

Create `app/modules/settings/models.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    theme: Mapped[str] = mapped_column(String(16), nullable=False, default="system")
    visibility: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    notification_prefs: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

- [ ] **Step 4: Add settings service**

Create `app/modules/settings/service.py`:

```python
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.settings.models import UserSettings


class Visibility(StrEnum):
    PRIVATE = "private"
    SHARED = "shared"


DATA_TYPES = ("diary", "daily_log", "cycle", "bbt", "trip", "report", "health")

DEFAULT_VISIBILITY: dict[str, str] = {
    "diary": Visibility.PRIVATE.value,
    "daily_log": Visibility.SHARED.value,
    "cycle": Visibility.SHARED.value,
    "bbt": Visibility.PRIVATE.value,
    "trip": Visibility.SHARED.value,
    "report": Visibility.PRIVATE.value,
    "health": Visibility.PRIVATE.value,
}

DEFAULT_NOTIFICATION_PREFS: dict[str, object] = {
    "daily_record": {"enabled": False, "time": "21:00"},
    "period": {"enabled": False, "days_before": 2},
    "fertile_window": {"enabled": False, "days_before": 1},
    "bbt": {"enabled": False, "time": "07:30"},
    "partner_activity": {"enabled": False},
}


def ensure_settings(db: Session, *, user_id: int) -> UserSettings:
    settings = db.scalar(select(UserSettings).where(UserSettings.user_id == user_id))
    if settings:
        changed = False
        visibility = dict(settings.visibility)
        for key, value in DEFAULT_VISIBILITY.items():
            if key not in visibility:
                visibility[key] = value
                changed = True
        prefs = dict(settings.notification_prefs)
        for key, value in DEFAULT_NOTIFICATION_PREFS.items():
            if key not in prefs:
                prefs[key] = value
                changed = True
        if changed:
            settings.visibility = visibility
            settings.notification_prefs = prefs
            db.commit()
            db.refresh(settings)
        return settings

    settings = UserSettings(
        user_id=user_id,
        theme="system",
        visibility=dict(DEFAULT_VISIBILITY),
        notification_prefs=dict(DEFAULT_NOTIFICATION_PREFS),
    )
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def set_visibility(
    db: Session,
    *,
    settings: UserSettings,
    data_type: str,
    visibility: Visibility,
) -> UserSettings:
    if data_type not in DATA_TYPES:
        raise ValueError(f"unknown data type: {data_type}")
    values = dict(settings.visibility)
    values[data_type] = visibility.value
    settings.visibility = values
    db.commit()
    db.refresh(settings)
    return settings


def can_partner_view(settings: UserSettings, data_type: str) -> bool:
    return settings.visibility.get(data_type) == Visibility.SHARED.value
```

- [ ] **Step 5: Add Alembic migration**

Create `alembic/versions/0009_user_settings.py` with `down_revision = "0008_trip_tables"` and a `user_settings` table matching the model. Use JSON columns for MariaDB.

- [ ] **Step 6: Add settings router and page tests**

Create `tests/test_settings/test_router.py`:

```python
from app.modules.settings.service import ensure_settings


def test_get_settings_page(client, logged_in_user):
    response = client.get("/me/settings")
    assert response.status_code == 200
    assert "设置" in response.text
    assert "隐私可见性" in response.text


def test_post_visibility_updates_setting(client, db, logged_in_user):
    response = client.post(
        "/me/settings/visibility",
        data={"data_type": "diary", "visibility": "shared"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    settings = ensure_settings(db, user_id=logged_in_user.id)
    assert settings.visibility["diary"] == "shared"
```

- [ ] **Step 7: Implement settings router**

Create `app/modules/settings/router.py`:

```python
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user
from app.modules.auth.models import User
from app.modules.settings.service import DATA_TYPES, Visibility, ensure_settings, set_visibility
from app.templating import templates

router = APIRouter(tags=["settings"])

LABELS = {
    "diary": "日记",
    "daily_log": "每日记录",
    "cycle": "经期",
    "bbt": "基础体温",
    "trip": "旅行相册",
    "report": "报告",
    "health": "健康指标",
}


@router.get("/me/settings", response_class=HTMLResponse)
def settings_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> HTMLResponse:
    settings = ensure_settings(db, user_id=user.id)
    return templates.TemplateResponse(
        request,
        "pages/settings.html",
        {
            "user": user,
            "settings": settings,
            "data_types": DATA_TYPES,
            "labels": LABELS,
            "active": "me",
        },
    )


@router.post("/me/settings/visibility")
def update_visibility(
    data_type: str = Form(...),
    visibility: Visibility = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> RedirectResponse:
    settings = ensure_settings(db, user_id=user.id)
    set_visibility(db, settings=settings, data_type=data_type, visibility=visibility)
    return RedirectResponse("/me/settings", status_code=303)
```

- [ ] **Step 8: Register router and template**

Modify `app/main.py`:

```python
from app.modules.settings.router import router as settings_router

app.include_router(settings_router)
```

Create `app/templates/pages/settings.html` with readable Chinese headings,
visibility selectors, theme section, reminder section, and data section links to
`/me/import`, `/charts`, and `/reports`.

- [ ] **Step 9: Run focused settings tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_settings -v
```

Expected: all settings tests pass.

- [ ] **Step 10: Commit**

Run:

```powershell
git add app/modules/settings app/templates/pages/settings.html app/templates/pages/me.html app/main.py alembic/versions/0009_user_settings.py tests/test_settings
git commit -m "feat(settings): add privacy and settings center"
```

---

### Task 3: Health Metrics And Predictor Evidence

**Files:**
- Create: `app/modules/health/__init__.py`
- Create: `app/modules/health/models.py`
- Create: `app/modules/health/service.py`
- Create: `alembic/versions/0010_health_metrics.py`
- Create: `app/modules/cycle/predictor/mucus.py`
- Create: `app/modules/cycle/predictor/health.py`
- Modify: `app/modules/cycle/predictor/combined.py`
- Modify: `app/modules/cycle/predictor/__init__.py`
- Test: `tests/test_health/test_service.py`
- Test: `tests/test_cycle/test_predictor_mucus.py`
- Test: `tests/test_cycle/test_predictor_health.py`

- [ ] **Step 1: Write failing health service tests**

Create `tests/test_health/test_service.py`:

```python
from datetime import date
from decimal import Decimal

from app.modules.health.service import MetricType, list_metrics, upsert_metric


def test_upsert_metric_creates_and_updates(db, user):
    first = upsert_metric(
        db,
        user_id=user.id,
        date=date(2026, 5, 24),
        metric_type=MetricType.RESTING_HEART_RATE,
        value=Decimal("62"),
        unit="bpm",
        source="manual",
    )
    second = upsert_metric(
        db,
        user_id=user.id,
        date=date(2026, 5, 24),
        metric_type=MetricType.RESTING_HEART_RATE,
        value=Decimal("60"),
        unit="bpm",
        source="manual",
    )
    assert first.id == second.id
    assert second.value == Decimal("60")


def test_list_metrics_filters_by_type(db, user):
    upsert_metric(
        db,
        user_id=user.id,
        date=date(2026, 5, 24),
        metric_type=MetricType.HRV,
        value=Decimal("45"),
        unit="ms",
        source="manual",
    )
    rows = list_metrics(db, user_id=user.id, metric_type=MetricType.HRV)
    assert len(rows) == 1
    assert rows[0].unit == "ms"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_health/test_service.py -v
```

Expected: import error because the health module does not exist.

- [ ] **Step 3: Add health model and migration**

Create `HealthMetric` with fields `id`, `user_id`, `date`, `metric_type`,
`value`, `unit`, `source`, `meta_json`, `created_at`, `updated_at`. Add unique
constraint on `user_id`, `date`, `metric_type`, `source`. Migration
`0010_health_metrics.py` uses `down_revision = "0009_user_settings"`.

- [ ] **Step 4: Add health service**

Create `MetricType` as `StrEnum` with values `resting_heart_rate`, `hrv`,
`sleep_duration`, `sleep_quality`, and `weight`. Implement `upsert_metric` and
`list_metrics` using SQLAlchemy `select`.

- [ ] **Step 5: Write predictor tests**

Create `tests/test_cycle/test_predictor_mucus.py`:

```python
from datetime import date

from app.modules.daily_log.service import toggle_tag
from app.modules.cycle.predictor.mucus import MucusSignal


def test_mucus_signal_detects_egg_white_discharge(db, user):
    toggle_tag(db, user_id=user.id, entry_date=date(2026, 5, 24), tag_key="disch_egg_white")
    result = MucusSignal().evaluate(db, user_id=user.id, target_date=date(2026, 5, 24))
    assert result is not None
    assert result.label == "接近排卵"
    assert result.confidence >= 0.55
```

Create `tests/test_cycle/test_predictor_health.py`:

```python
from datetime import date
from decimal import Decimal

from app.modules.health.service import MetricType, upsert_metric
from app.modules.cycle.predictor.health import HealthMetricSignal


def test_health_signal_uses_rhr_and_hrv_as_helper_evidence(db, user):
    upsert_metric(
        db,
        user_id=user.id,
        date=date(2026, 5, 24),
        metric_type=MetricType.RESTING_HEART_RATE,
        value=Decimal("68"),
        unit="bpm",
        source="manual",
    )
    result = HealthMetricSignal().evaluate(db, user_id=user.id, target_date=date(2026, 5, 24))
    assert result is not None
    assert "静息心率" in result.evidence
    assert result.confidence <= 0.35
```

- [ ] **Step 6: Implement signals and include them in CombinedPredictor**

`MucusSignal` reads daily tags for `disch_egg_white` and returns helper evidence.
`HealthMetricSignal` reads recent health metrics and returns low-confidence
evidence. Add both to `CombinedPredictor` after Calendar, BBT, and LH so they do
not override stronger signals.

- [ ] **Step 7: Run focused tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_health tests/test_cycle/test_predictor_mucus.py tests/test_cycle/test_predictor_health.py tests/test_cycle/test_predictor_combined.py -v
```

Expected: all selected tests pass.

- [ ] **Step 8: Commit**

Run:

```powershell
git add app/modules/health app/modules/cycle/predictor alembic/versions/0010_health_metrics.py tests/test_health tests/test_cycle/test_predictor_mucus.py tests/test_cycle/test_predictor_health.py
git commit -m "feat(health): add metrics and predictor evidence"
```

---

### Task 4: Charts Center

**Files:**
- Create: `app/modules/charts/__init__.py`
- Create: `app/modules/charts/service.py`
- Create: `app/modules/charts/router.py`
- Create: `app/templates/pages/charts.html`
- Create: `app/templates/fragments/line_chart.html`
- Modify: `app/main.py`
- Modify: `app/templates/components/nav.html`
- Test: `tests/test_charts/test_service.py`
- Test: `tests/test_charts/test_router.py`

- [ ] **Step 1: Write failing chart tests**

Create `tests/test_charts/test_service.py`:

```python
from datetime import date
from decimal import Decimal

from app.modules.charts.service import build_bbt_series
from app.modules.cycle.service import log_bbt


def test_build_bbt_series_orders_points(db, user):
    log_bbt(db, user_id=user.id, reading_date=date(2026, 5, 24), temp_c=Decimal("36.50"))
    log_bbt(db, user_id=user.id, reading_date=date(2026, 5, 23), temp_c=Decimal("36.40"))
    series = build_bbt_series(db, user_id=user.id)
    assert [point["date"] for point in series["points"]] == ["2026-05-23", "2026-05-24"]
```

Create `tests/test_charts/test_router.py`:

```python
def test_charts_page_renders(client, logged_in_user):
    response = client.get("/charts")
    assert response.status_code == 200
    assert "趋势" in response.text
    assert "基础体温" in response.text


def test_bbt_chart_json(client, logged_in_user):
    response = client.get("/charts/bbt.json")
    assert response.status_code == 200
    assert response.json()["kind"] == "bbt"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_charts -v
```

Expected: import/404 failures because chart module does not exist.

- [ ] **Step 3: Implement chart service**

Create service functions:

- `build_bbt_series(db, user_id) -> dict`
- `build_cycle_series(db, user_id) -> dict`
- `build_tag_frequency(db, user_id, category) -> dict`
- `build_health_series(db, user_id, metric_type) -> dict`

Each returns `{"kind": "...", "points": [...]}` and returns empty `points` when
there is no data.

- [ ] **Step 4: Implement chart router and templates**

Add routes:

- `GET /charts`
- `GET /charts/bbt.json`
- `GET /charts/cycle.json`
- `GET /charts/tags/{category}.json`
- `GET /charts/health/{metric_type}.json`

Use server-rendered summary cards on `/charts`; JSON endpoints power future
interactive charts.

- [ ] **Step 5: Run chart tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_charts tests/test_ui/test_base_layout.py -v
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit**

Run:

```powershell
git add app/modules/charts app/templates/pages/charts.html app/templates/fragments/line_chart.html app/templates/components/nav.html app/main.py tests/test_charts
git commit -m "feat(charts): add trend center and json series"
```

---

### Task 5: Reports And PDF Uploads

**Files:**
- Create: `app/modules/reports/__init__.py`
- Create: `app/modules/reports/models.py`
- Create: `app/modules/reports/service.py`
- Create: `app/modules/reports/router.py`
- Create: `app/templates/pages/report_list.html`
- Create: `app/templates/pages/report_edit.html`
- Create: `app/templates/pages/report_detail.html`
- Create: `alembic/versions/0011_reports.py`
- Modify: `app/modules/media/pipeline.py`
- Modify: `app/modules/media/router.py`
- Modify: `app/main.py`
- Test: `tests/test_reports/test_service.py`
- Test: `tests/test_reports/test_router.py`
- Test: `tests/test_media/test_pdf_upload.py`

- [ ] **Step 1: Write failing report and PDF tests**

Create `tests/test_media/test_pdf_upload.py`:

```python
import io


def test_pdf_upload_is_accepted(client, logged_in_user):
    pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
    response = client.post(
        "/media/upload",
        files={"file": ("report.pdf", io.BytesIO(pdf), "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["kind"] == "pdf"
```

Create report service tests for create/list/update/delete and partner visibility.

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_media/test_pdf_upload.py tests/test_reports -v
```

Expected: PDF upload rejected and report module missing.

- [ ] **Step 3: Extend media pipeline for PDF**

Allow `application/pdf` with a separate size limit from settings. Store original
path, `kind="pdf"`, width/height as `None`, and no thumbnail requirement.

- [ ] **Step 4: Add reports model and migration**

Create `Report` table with `id`, `owner_id`, `date`, `title`, `report_type`,
`notes`, `visibility`, `media_id`, `created_at`, `updated_at`. Migration
`0011_reports.py` uses `down_revision = "0010_health_metrics"`.

- [ ] **Step 5: Implement report service and router**

Service supports `create_report`, `update_report`, `delete_report`,
`get_report_for_user`, and `list_reports_for_user`. Router supports:

- `GET /reports`
- `GET /reports/new`
- `POST /reports`
- `GET /reports/{report_id}`
- `GET /reports/{report_id}/edit`
- `POST /reports/{report_id}`
- `POST /reports/{report_id}/delete`

- [ ] **Step 6: Run focused tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_reports tests/test_media -v
```

Expected: all selected tests pass, with existing image upload behavior preserved.

- [ ] **Step 7: Commit**

Run:

```powershell
git add app/modules/reports app/modules/media app/templates/pages/report_*.html app/main.py alembic/versions/0011_reports.py tests/test_reports tests/test_media/test_pdf_upload.py
git commit -m "feat(reports): add pdf reports"
```

---

### Task 6: Import Center

**Files:**
- Create: `app/modules/import_/__init__.py`
- Create: `app/modules/import_/models.py`
- Create: `app/modules/import_/parsers.py`
- Create: `app/modules/import_/service.py`
- Create: `app/modules/import_/router.py`
- Create: `app/templates/pages/import.html`
- Create: `app/templates/fragments/import_status.html`
- Create: `alembic/versions/0012_import_jobs.py`
- Modify: `app/main.py`
- Modify: `app/scheduler.py`
- Test: `tests/test_import/test_parsers.py`
- Test: `tests/test_import/test_service.py`
- Test: `tests/test_import/test_router.py`

- [ ] **Step 1: Write failing parser tests**

Create `tests/test_import/test_parsers.py`:

```python
from app.modules.import_.parsers import parse_apple_health_xml, parse_flo_csv


def test_parse_flo_csv_period_and_symptom_rows():
    csv_text = "date,type,value\n2026-05-01,period,start\n2026-05-02,symptom,cramps\n"
    parsed = parse_flo_csv(csv_text.encode("utf-8"))
    assert parsed.periods[0].start_date.isoformat() == "2026-05-01"
    assert parsed.tags[0].tag_key == "sym_cramps"


def test_parse_apple_health_menstrual_flow():
    xml = b'''<?xml version="1.0" encoding="UTF-8"?>
    <HealthData>
      <Record type="HKCategoryTypeIdentifierMenstrualFlow"
              startDate="2026-05-01 08:00:00 +0800"
              endDate="2026-05-01 08:00:00 +0800"
              value="HKCategoryValueMenstrualFlowMedium" />
    </HealthData>'''
    parsed = parse_apple_health_xml(xml)
    assert parsed.periods[0].start_date.isoformat() == "2026-05-01"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_import/test_parsers.py -v
```

Expected: import module missing.

- [ ] **Step 3: Add import model and parsed DTOs**

Create `ImportJob` with `source`, `filename`, `status`, `summary_json`,
`error_message`, `created_by_id`, `created_at`, `updated_at`, `started_at`,
`finished_at`. Create parser dataclasses `ParsedImport`, `ParsedPeriod`,
`ParsedTag`, `ParsedBbt`, and `ParsedHealthMetric`.

- [ ] **Step 4: Implement parsers**

Implement:

- `parse_flo_csv(raw: bytes) -> ParsedImport`
- `parse_apple_health_xml(raw: bytes) -> ParsedImport`

The Flo parser accepts the simple three-column fixture and maps:

- `period,start` -> period start.
- `symptom,cramps` -> `sym_cramps`.
- `ovulation,positive` -> `ovu_positive`.

The Apple parser handles menstrual flow, sexual activity, BBT, resting heart
rate, HRV, and sleep records.

- [ ] **Step 5: Implement idempotent import service**

Service functions:

- `create_import_job(db, user_id, source, filename, raw_bytes)`.
- `run_import_job(db, job_id)`.
- `apply_parsed_import(db, user_id, parsed)`.

`apply_parsed_import` upserts through existing cycle, daily_log, BBT, and health
services and returns counts.

- [ ] **Step 6: Implement router and scheduler hook**

Routes:

- `GET /me/import`
- `POST /me/import`
- `GET /me/import/_fragment/status/{job_id}`

Scheduler scans pending jobs and calls `run_import_job`.

- [ ] **Step 7: Run import tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_import tests/test_cycle tests/test_daily_log tests/test_health -v
```

Expected: import tests pass and existing data services still pass.

- [ ] **Step 8: Commit**

Run:

```powershell
git add app/modules/import_ app/templates/pages/import.html app/templates/fragments/import_status.html app/main.py app/scheduler.py alembic/versions/0012_import_jobs.py tests/test_import
git commit -m "feat(import): add flo and apple health import center"
```

---

### Task 7: Web Push And Reminders

**Files:**
- Create: `app/modules/notifications/__init__.py`
- Create: `app/modules/notifications/models.py`
- Create: `app/modules/notifications/service.py`
- Create: `app/modules/notifications/router.py`
- Create: `alembic/versions/0013_push_subscriptions.py`
- Modify: `app/static/sw.js`
- Modify: `app/static/js/app.js`
- Modify: `app/templates/pages/settings.html`
- Modify: `app/scheduler.py`
- Modify: `app/config.py`
- Modify: `pyproject.toml`
- Test: `tests/test_notifications/test_service.py`
- Test: `tests/test_notifications/test_router.py`

- [ ] **Step 1: Write failing notification tests**

Create `tests/test_notifications/test_service.py`:

```python
from app.modules.notifications.service import save_subscription, subscriptions_for_user


def test_save_subscription_upserts_endpoint(db, user):
    payload = {
        "endpoint": "https://push.example/sub/1",
        "keys": {"p256dh": "abc", "auth": "def"},
    }
    first = save_subscription(db, user_id=user.id, payload=payload, user_agent="pytest")
    second = save_subscription(db, user_id=user.id, payload=payload, user_agent="pytest")
    assert first.id == second.id
    assert len(subscriptions_for_user(db, user_id=user.id)) == 1
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_notifications -v
```

Expected: notification module missing.

- [ ] **Step 3: Add dependency and config**

Add `pywebpush>=2.0` to `pyproject.toml`. Add VAPID public/private key settings
to `app/config.py`. Keep the existing CLI VAPID command compatible.

- [ ] **Step 4: Add push subscription model and migration**

Create `PushSubscription` with `user_id`, `endpoint`, `keys_json`,
`user_agent`, `fail_count`, `disabled_at`, and timestamps. Unique endpoint.
Migration `0013_push_subscriptions.py` uses `down_revision = "0012_import_jobs"`.

- [ ] **Step 5: Implement notification service and router**

Routes:

- `GET /notifications/vapid-public-key`
- `POST /notifications/subscriptions`
- `POST /notifications/subscriptions/disable`

Service handles subscription upsert, invalid subscription marking, due reminder
selection, and a send wrapper that can be monkeypatched in tests.

- [ ] **Step 6: Update service worker and browser JS**

`sw.js` listens for `push` and `notificationclick`. `app.js` includes a helper
that reads the public key, requests permission, registers the subscription, and
posts it to the backend from the settings page button.

- [ ] **Step 7: Run notification tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_notifications tests/test_ui/test_service_worker.py -v
```

Expected: all selected tests pass.

- [ ] **Step 8: Commit**

Run:

```powershell
git add app/modules/notifications app/static/sw.js app/static/js/app.js app/templates/pages/settings.html app/scheduler.py app/config.py pyproject.toml alembic/versions/0013_push_subscriptions.py tests/test_notifications
git commit -m "feat(notifications): add pwa push reminders"
```

---

### Task 8: Today, Calendar, And Cross-Module Integration

**Files:**
- Modify: `app/modules/timeline/service.py`
- Modify: `app/modules/timeline/router.py`
- Modify: `app/templates/pages/today.html`
- Modify: `app/templates/pages/calendar.html`
- Modify: `app/templates/fragments/predictor_card.html`
- Modify: `app/templates/fragments/partner_card.html`
- Modify: `app/templates/fragments/cycle_ring.html`
- Test: `tests/test_timeline/test_service.py`
- Test: `tests/test_timeline/test_endpoints.py`
- Test: `tests/test_ui/test_base_layout.py`

- [ ] **Step 1: Write failing integration tests**

Extend timeline tests:

```python
def test_today_page_links_to_m2_features(client, logged_in_user):
    response = client.get("/")
    assert response.status_code == 200
    for href in ["/log/today", "/cycle/log", "/bbt/log", "/reports/new", "/charts", "/me/settings"]:
        assert href in response.text


def test_calendar_page_has_readable_legend(client, logged_in_user):
    response = client.get("/calendar")
    assert response.status_code == 200
    assert "经期" in response.text
    assert "预测经期" in response.text
    assert "易孕期" in response.text
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_timeline tests/test_ui/test_base_layout.py -v
```

Expected: links to reports/charts/settings may fail before integration markup.

- [ ] **Step 3: Update today view model**

Enhance `TodaySnapshot` with optional fields for report count, chart summaries,
health summary, and readable prediction evidence. Keep existing fields and
fragment routes stable.

- [ ] **Step 4: Update templates**

Add quick actions for daily log, period, BBT, report upload, charts, and
settings. Make partner card clearly show shared-only data. Make predictor card
show confidence and evidence in Chinese.

- [ ] **Step 5: Run integration tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_timeline tests/test_ui tests/test_charts tests/test_reports -v
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit**

Run:

```powershell
git add app/modules/timeline app/templates/pages/today.html app/templates/pages/calendar.html app/templates/fragments tests/test_timeline tests/test_ui
git commit -m "feat(timeline): integrate m2 dashboard actions"
```

---

### Task 9: Full Verification And Deployment

**Files:**
- Modify: `docs/runbook.md`
- Modify: `README.md`

- [ ] **Step 1: Run lint**

Run:

```powershell
.venv\Scripts\python.exe -m ruff check app tests alembic
```

Expected: `All checks passed!`

- [ ] **Step 2: Run type checks**

Run:

```powershell
.venv\Scripts\python.exe -m mypy app
```

Expected: `Success: no issues found in ... source files`

- [ ] **Step 3: Run pytest groups sequentially**

Run these commands one at a time because the shared MariaDB test database is not
parallel-safe:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_auth -v
.venv\Scripts\python.exe -m pytest tests/test_cycle -v
.venv\Scripts\python.exe -m pytest tests/test_daily_log tests/test_health -v
.venv\Scripts\python.exe -m pytest tests/test_media tests/test_reports -v
.venv\Scripts\python.exe -m pytest tests/test_diary tests/test_trip -v
.venv\Scripts\python.exe -m pytest tests/test_timeline tests/test_ui -v
.venv\Scripts\python.exe -m pytest tests/test_settings tests/test_charts tests/test_import tests/test_notifications -v
```

Expected: all groups pass. The existing optional `piexif` skip is acceptable if
it remains the only skip.

- [ ] **Step 4: Run migrations locally**

Run:

```powershell
.venv\Scripts\alembic.exe upgrade head
```

Expected: migration completes without error and tables through
`push_subscriptions` exist.

- [ ] **Step 5: Update docs**

Update `README.md` and `docs/runbook.md` with:

- M2 feature list.
- Import file formats.
- Push notification setup.
- PDF report upload notes.
- Sequential test guidance.

- [ ] **Step 6: Commit docs and verification fixes**

Run:

```powershell
git add README.md docs/runbook.md
git commit -m "docs: update m2 runbook"
```

- [ ] **Step 7: Deploy**

Run:

```powershell
git push origin feature/m1
bash scripts/deploy.sh
```

Expected: deploy script migrates, restarts service, and `/healthz` returns OK.

- [ ] **Step 8: Production smoke test**

Run:

```powershell
curl.exe -k https://150.158.3.104/healthz
curl.exe -k https://150.158.3.104/login
```

Then manually verify in browser:

- Login page renders Chinese correctly.
- Today page renders and quick actions work.
- Daily log toggles a tag and persists.
- Calendar renders period legend.
- Settings page saves visibility.
- Charts page loads.
- Reports page accepts a small PDF.
- Import page creates a job for a sample file.
- Push settings show supported/unsupported state without crashing.

- [ ] **Step 9: Final commit or tag**

If deployment smoke passes, create a release tag:

```powershell
git tag m2-full-2026-05-24
git push origin m2-full-2026-05-24
```

---

## Self-Review Notes

Spec coverage:

- Frontend repair: Task 1 and Task 8.
- Today and Daily Log: Task 1 and Task 8.
- Cycle, BBT, Calendar: Task 1, Task 3, Task 4, Task 8.
- Settings: Task 2.
- Charts: Task 4.
- Import: Task 6.
- Health metrics and predictor evidence: Task 3.
- Reports/PDF: Task 5.
- Web Push: Task 7.
- Testing and deployment: Task 9.

Execution constraints:

- Use TDD inside each task.
- Commit after each task.
- Run database tests sequentially.
- Do not deploy until ruff, mypy, and the targeted pytest groups pass.
