# Couple Diary Runbook (M2)

## Quick checks

```bash
systemctl status couple-diary
journalctl -u couple-diary -n 100 --no-pager
curl -k https://150.158.3.104/healthz
```

## M2 smoke checks

After login, verify these routes render without a server error:

```bash
curl -k https://150.158.3.104/login
curl -k https://150.158.3.104/healthz
```

Manual browser checks:

- `/log/today` shows Today cards and quick actions.
- `/calendar` and `/cycle/log` still allow cycle entry.
- `/charts` renders trend cards.
- `/reports` allows report list/create/detail flows.
- `/me/import` accepts Flo CSV and Apple Health XML uploads.
- `/me/settings` saves visibility, notification, and push preferences.

## Restart

```bash
systemctl restart couple-diary
```

## Disk full

1. Check: `df -h /`
2. Prune old backups: `find /data/backups/db -mtime +14 -delete`
3. Prune old logs: `find /var/log/couple_diary -mtime +30 -delete`

## Restore from backup

```bash
# Pick a backup (UTC timestamp):
ls /data/backups/db/

# Restore it:
gunzip < /data/backups/db/20260522-030000.sql.gz | mysql -uroot couple_diary
```

## Add a new invite (after a token expires or is lost)

The current model only supports one bonded couple. To re-issue a token, you'd
need to first wipe state - best left as a manual operation:

```bash
mysql -uroot couple_diary <<SQL
DELETE FROM sessions; DELETE FROM invite_tokens; DELETE FROM couples; DELETE FROM users;
SQL
sudo -u couple /opt/couple_diary/.venv/bin/python -m app.cli init-couple --he <name> --she <partner>
```

## Deploy a code update

The production deploy script pulls `origin/feature/m1`. Merge and push the M2
branch into `feature/m1` before running this on the server.

```bash
cd /opt/couple_diary && bash scripts/deploy.sh
```

If `/healthz` fails post-deploy, the script auto-rolls back the DB dump and
checks out HEAD~1, then restarts.

## M2 production config

Required existing values:

- `APP_ENV=production`
- `COOKIE_SECURE=true`
- `DATABASE_URL=mysql+pymysql://...`
- `UPLOAD_DIR=/data/uploads`
- `BACKUP_DIR=/data/backups`
- `LOG_DIR=/var/log/couple_diary`

Required for Web Push:

```env
VAPID_PUBLIC_KEY=...
VAPID_PRIVATE_KEY=...
VAPID_SUBJECT=mailto:you@example.com
```

If VAPID values are empty, the app still runs, but browser push subscription
will remain unavailable.

Upload limits used by M2:

- `MAX_IMAGE_UPLOAD_BYTES=10485760`
- `MAX_PDF_UPLOAD_BYTES=20971520`
- `MAX_IMPORT_UPLOAD_BYTES=52428800`

## View scheduler activity

```bash
journalctl -u couple-diary | grep -E "scheduler|backup_database|mirror_uploads|cleanup_orphan_media"
```

M2 also runs pending import processing and reminder checks from the application
scheduler. Check `journalctl -u couple-diary` for `process_pending_import_jobs`
and notification logs when debugging those flows.

Jobs (Asia/Shanghai):
- 03:00 daily — `backup_db` (mysqldump → `/data/backups/db/`)
- 03:15 daily — `mirror_uploads` (sync uploads → `/data/backups/uploads-mirror/`)
- 03:30 daily — `cleanup_orphan_media`
