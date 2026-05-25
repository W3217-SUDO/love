# Couple Diary

Private two-person web app for tracking cycle, intimacy, mood, health signals,
reports, and shared memories.

See [design spec](docs/superpowers/specs/2026-05-22-couple-diary-design.md),
[M1 plan](docs/superpowers/plans/2026-05-22-couple-diary-m1.md), and
[M2 plan](docs/superpowers/plans/2026-05-24-couple-diary-m2-full.md).

## M2 feature set

- Mobile-first Chinese UI with Today, calendar, daily log, cycle, BBT, diary,
  trip, report, chart, import, and settings entry points.
- Privacy-aware partner dashboard. Diary, reports, health metrics, daily log,
  BBT, trips, and cycle data each have separate visibility controls.
- Flo-style cycle support using period history, mucus, LH/ovulation tests, BBT,
  and health metrics as prediction evidence.
- Trend center at `/charts` with cycle, BBT, symptom, mood, and health series.
- Report center at `/reports` with PDF/image attachments and signed media URLs.
- Import center at `/me/import` for Flo CSV and Apple Health XML imports, with
  resumable job status and idempotent writes.
- PWA push reminders using browser Push API, VAPID keys, service worker push
  handlers, and a disable control in settings.

## Dev setup

```bash
python -m venv .venv
.venv/Scripts/activate  # Windows
# source .venv/bin/activate  # Linux
pip install -e ".[dev]"
cp .env.example .env  # then edit
alembic upgrade head
pytest
uvicorn app.main:app --reload
```

For a production-like local database, update `.env` to use the SSH tunnel port:

```env
DATABASE_URL=mysql+pymysql://couple:devpwd@127.0.0.1:13306/couple_diary?charset=utf8mb4
DATABASE_TEST_URL=mysql+pymysql://couple:devpwd@127.0.0.1:13306/couple_diary_test?charset=utf8mb4
```

## Dev DB access (SSH tunnel)

Production MariaDB binds to `127.0.0.1` only. For dev against the prod-style DB
on `150.158.3.104`, start a local SSH tunnel before running tests or the app:

```bash
ssh -i <path-to-private-key>/tencent_cloud -fN -L 13306:127.0.0.1:3306 \
    -o ServerAliveInterval=30 root@150.158.3.104
```

Then point your `.env` at `127.0.0.1:13306`. Check the tunnel is alive with
`netstat -an | findstr 13306` on Windows or `ss -tlnp | grep 13306` on Linux.

If your network sits behind a VPN/CGNAT (e.g., 198.18.0.x routes), direct TCP
to 3306 will be silently dropped, so the tunnel is required.

## Verification

Use sequential test groups when running against the shared MariaDB test database.
The schema reset is intentionally simple and concurrent pytest runs can collide.

```bash
ruff check app tests alembic
mypy app
alembic upgrade head

pytest tests/test_healthz.py tests/test_config.py -q
pytest tests/test_auth -q
pytest tests/test_cycle -q
pytest tests/test_daily_log tests/test_health -q
pytest tests/test_media tests/test_reports -q
pytest tests/test_diary tests/test_trip -q
pytest tests/test_settings -q
pytest tests/test_charts -q
pytest tests/test_import -q
pytest tests/test_notifications -q
pytest tests/test_ui -q
pytest tests/test_timeline -q
```

If the remote MariaDB reset fails during timeline tests, rerun only the timeline
group with an isolated local SQLite test URL and record that fallback in the
deployment notes.

## Production notes

`scripts/deploy.sh` deploys the current production branch by pulling
`origin/feature/m1` on the server. Merge M2 into `feature/m1` and push before
running the deploy script.

For Web Push, set these in `/opt/couple_diary/.env.production` before enabling
browser notifications:

```env
VAPID_PUBLIC_KEY=...
VAPID_PRIVATE_KEY=...
VAPID_SUBJECT=mailto:you@example.com
```
