# Couple Diary M2 Full Design

## Goal

M2 turns the current working M1 app into a complete Flo-like two-person health
and life diary that is convenient for daily use on mobile.

The release should feel complete to a normal user:

- Chinese text renders correctly across all pages.
- Every navigation item leads to a useful page.
- Daily recording, cycle tracking, charts, settings, import, reports, and
  reminders are discoverable from the UI.
- Existing diary, trip, media, cycle, BBT, and daily-log features remain stable.
- The production deployment can be updated with migrations and verified by
  automated tests plus a manual smoke checklist.

## Existing Baseline

The app already has these foundations:

- Invite-only two-user auth, password setup, sessions, and admin login-as.
- Today page, partner card, predictor card, cycle ring, and calendar view.
- Period logging, BBT logging, BBT deletion, period deletion, and prediction
  services using Calendar, BBT, and LH signals.
- Flo-style daily tags with categories and toggle persistence.
- Diary entries with visibility and media attachments.
- Trip albums with shared visibility, cover photos, and media attachments.
- Image upload pipeline, thumbnails, previews, and authenticated media serving.
- PWA manifest and service worker.
- Scheduler, backups, cleanup task, systemd/nginx deployment scripts.
- Tests for auth, cycle, daily log, media, diary, trip, timeline, and UI.

M2 should build on these modules instead of replacing them.

## Scope

### Frontend Completion

Fix and polish the UI before adding deeper features:

- Repair mojibake/garbled Chinese in templates, tag catalog, README, and user
  facing copy.
- Keep the app mobile-first, with the bottom navigation as the primary control.
- Use consistent page headers, action buttons, empty states, destructive action
  confirmations, and saved/error feedback.
- Make all major pages usable on phone-width screens without overflow.
- Add a small set of reusable template fragments for page headers, empty states,
  section cards, flash messages, and inline form errors.
- Keep visual style close to Flo: warm, soft, health-oriented, but not an exact
  copy of Flo assets or protected UI.

### Today

Upgrade `/` into the central daily dashboard:

- Show cycle day, predicted phase, next period, fertile window, and prediction
  confidence in plain Chinese.
- Show a compact "record today" action cluster for daily tags, period, BBT,
  reports, and notes.
- Show today's selected tags grouped by category.
- Show recent BBT/trend summary when enough data exists.
- Show partner shared activity without exposing private diary content.
- Keep HTMX fragment endpoints for partner/predictor/cycle-ring refreshes.

### Daily Log

Improve `/log/today` and `/log/{date}`:

- Fix all category/tag labels.
- Keep tags as stable Python catalog constants.
- Add notes editing with visible save state.
- Add record date navigation: previous day, today, next day.
- Add clearer category order: period/sex/libido, mood, symptoms, discharge,
  digestion, ovulation test, lifestyle.
- Keep toggle endpoints idempotent and fast.
- Map discharge and ovulation tags into predictor inputs.

### Cycle, BBT, Calendar

Improve cycle tracking:

- Keep period start/end API and HTML forms.
- Add better empty states and validation errors.
- Add delete confirmation for period and BBT records.
- Add cycle settings UI for average cycle length, period length, and prediction
  mode.
- Calendar should display actual period, predicted period, fertile window, and
  selected day summaries.
- BBT page should show recent readings plus a lightweight line chart.

### Settings Center

Add a full `/me/settings` module:

- Profile: display name, avatar URL, role display.
- Couple: anniversary and days together.
- Visibility: per data type default visibility for diary, daily log, cycle,
  BBT, trip, report, health metrics.
- Theme: system/light/soft pink mode, stored per user.
- Notifications: enable push, choose reminder types and times.
- Data: export all data, view import jobs, start import.

Settings should be represented by a `user_settings` table. Sensitive settings
should be scoped by `user_id`, and partner visibility must be enforced in
services, not only templates.

### Charts Center

Add `/charts` pages and JSON endpoints:

- BBT line chart with ovulation markers.
- Cycle length and period length trend.
- Symptom frequency by week/month.
- Mood trend by week/month.
- Intimacy trend as private/shared according to visibility.
- Health metrics trend for RHR, HRV, and sleep when available.

Use simple server-rendered pages and JSON data endpoints. The frontend may use a
small charting library if already acceptable for the stack; otherwise use
progressive SVG/HTML charts for the first version.

### Import Center

Add `/me/import`:

- Accept Flo CSV exports and Apple Health export files.
- Store import jobs with status, source, filename, summary, error message, and
  timestamps.
- Parse uploads asynchronously through scheduler-driven or request-triggered
  workers.
- Make imports idempotent:
  - Periods upsert by user and start date.
  - Daily tags upsert by date/category/tag.
  - Health metrics upsert by user/date/type.
- Show progress/status with a fragment endpoint.
- Return a summary: created, updated, skipped, failed.

Apple Health support should start with practical records:

- Menstrual flow -> periods.
- Sexual activity -> daily tags.
- Basal body temperature -> BBT readings.
- Resting heart rate -> health metrics.
- HRV -> health metrics.
- Sleep analysis -> health metrics.

Flo CSV support should be tolerant of common column naming differences and
report unmapped columns instead of failing the entire job.

### Health Metrics And Prediction

Add a `health_metrics` table:

- `user_id`, `date`, `metric_type`, `value`, `unit`, `source`, `meta_json`.
- Unique key on `user_id`, `date`, `metric_type`, `source`.

Supported metric types:

- resting heart rate.
- HRV.
- sleep duration.
- sleep quality/deep sleep where available.
- weight can be accepted but does not need prediction logic in M2.

Extend prediction with:

- Mucus/discharge signal from daily tags.
- RHR/HRV support as low-confidence helper evidence.
- Existing Calendar, BBT, and LH signals remain the main predictors.

Prediction output should include readable evidence so users know why the app is
making a suggestion.

### Reports And PDFs

Extend media/report handling:

- Allow PDF uploads within configured size limits.
- Generate or store preview metadata where possible.
- Add `reports` table for date, title, report type, notes, owner, visibility,
  and media attachment.
- Add `/reports` list/detail/create/edit/delete.
- Reports can be linked from Today and Calendar selected-day summaries.

PDF content extraction is optional for M2. Uploading, preview/download, metadata,
and visibility are required.

### Web Push And Reminders

Add basic PWA push reminders:

- Store push subscriptions per user/device.
- Generate or load VAPID keys from settings.
- Let users choose reminder types:
  - Daily record reminder.
  - Upcoming period reminder.
  - Fertile window reminder.
  - BBT morning reminder.
  - Partner activity reminder.
- Scheduler sends due notifications.
- If push is unsupported, show a clear fallback message.

Reminder delivery failures should mark subscriptions invalid after repeated
failures, without crashing the scheduler.

## Architecture

Use the existing FastAPI/Jinja/SQLAlchemy module pattern.

New modules:

- `app/modules/settings`
- `app/modules/charts`
- `app/modules/import_`
- `app/modules/health`
- `app/modules/reports`
- `app/modules/notifications`

Each module should own:

- `models.py` if it stores data.
- `service.py` for business rules.
- `router.py` for HTML/API routes.
- `schemas.py` when API responses are structured.
- tests under `tests/test_<module>`.

Cross-module calls should go through service functions. Routers should not
directly query another module's tables except for simple current-user loading.

## Data Flow

Daily user flow:

1. User opens `/`.
2. Today service gathers cycle, daily tags, BBT, health metrics, reports, and
   partner shared summary.
3. User taps a quick action.
4. The target page saves through its own service.
5. Today fragments can refresh without a full page reload.

Import flow:

1. User uploads a file from `/me/import`.
2. Import job is created as `pending`.
3. Worker marks job `running`, parses into normalized rows, and upserts data.
4. Job ends as `succeeded`, `partial`, or `failed`.
5. UI polls the status fragment.

Notification flow:

1. User enables push from settings.
2. Browser subscription is stored.
3. Scheduler evaluates reminder rules.
4. Notification service sends due pushes and records failures.

## Privacy And Access

The app is for a fixed couple, but privacy still matters.

- Users can always see their own data.
- Partner can only see data whose visibility is shared or whose data type is
  configured as shared by default.
- Diary, reports, intimacy tags, and health metrics must default conservatively.
- Visibility checks must live in services.
- Media access must continue using authenticated/signed serving.

## Error Handling

- Validation errors should return user-readable Chinese messages in HTML pages.
- Import failures should be job-scoped and visible in the import center.
- Unsupported file formats should fail cleanly without storing partial rows.
- Push failures should not break request handlers or the scheduler.
- Chart endpoints should return empty series instead of crashing when no data
  exists.

## Testing

M2 requires tests before implementation for each module:

- Settings model/service/router tests.
- Chart service and JSON endpoint tests.
- Import parser tests using small sample Flo CSV and Apple Health XML fixtures.
- Import idempotency tests.
- Health metric model/service tests.
- Predictor tests for mucus and health-metric evidence.
- Report model/service/router tests.
- PDF upload acceptance/rejection tests.
- Notification subscription and scheduler decision tests.
- UI tests for main pages rendering Chinese text and navigation.
- Regression tests for existing auth, cycle, daily_log, media, diary, trip, and
  timeline behavior.

Verification before deployment:

- `ruff check app tests alembic`
- `mypy app`
- Targeted pytest groups for new modules.
- Existing regression pytest groups.
- Manual smoke test on production after deploy.

## Deployment

Deployment should remain compatible with the existing script and server setup:

- Add Alembic migrations for all new tables and columns.
- Install any new dependencies through `pyproject.toml`.
- Keep production health check at `/healthz`.
- Deploy with script, wait for health check, then run public HTTPS smoke checks.
- Verify login page, Today, Log, Calendar, Settings, Charts, Import, Reports,
  and media access.

## Out Of Scope

M2 will not attempt to provide medical diagnosis. Predictions should be presented
as estimates with evidence, not medical certainty.

M2 will not clone Flo's proprietary UI or assets. It will use a similar
mobile-first health diary interaction model with original styling.

M2 will not require native iOS/Android apps. PWA support remains the delivery
model.
