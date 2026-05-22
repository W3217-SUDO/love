# Couple Diary Runbook (M1)

## Quick checks

```bash
systemctl status couple-diary
journalctl -u couple-diary -n 100 --no-pager
curl -k https://150.158.3.104/healthz
```

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

```bash
cd /opt/couple_diary && bash scripts/deploy.sh
```

If `/healthz` fails post-deploy, the script auto-rolls back the DB dump and
checks out HEAD~1, then restarts.

## View scheduler activity

```bash
journalctl -u couple-diary | grep -E "scheduler|backup_database|mirror_uploads|cleanup_orphan_media"
```

Jobs (Asia/Shanghai):
- 03:00 daily — `backup_db` (mysqldump → `/data/backups/db/`)
- 03:15 daily — `mirror_uploads` (sync uploads → `/data/backups/uploads-mirror/`)
- 03:30 daily — `cleanup_orphan_media`
