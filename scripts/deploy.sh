#!/usr/bin/env bash
# Update Couple Diary on the production server.
# Run as root after pushing changes to the feature/m1 branch.
set -euo pipefail

APP_DIR="/opt/couple_diary"
DATA_DIR="/data"
APP_USER="couple"

cd "$APP_DIR"
ts=$(date +%Y%m%d-%H%M%S)

echo "== Pre-deploy DB dump =="
mkdir -p "$DATA_DIR/backups/pre-deploy"
mysqldump --single-transaction -uroot couple_diary | gzip > "$DATA_DIR/backups/pre-deploy/${ts}.sql.gz"

echo "== Pull latest =="
sudo -u "$APP_USER" git fetch origin
sudo -u "$APP_USER" git pull origin feature/m1

echo "== Reinstall deps =="
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install -e "$APP_DIR"

echo "== Apply migrations =="
sudo -u "$APP_USER" bash -c "cd $APP_DIR && set -a && . $APP_DIR/.env.production && set +a && $APP_DIR/.venv/bin/python -m alembic -c $APP_DIR/alembic.ini upgrade head"

echo "== Restart service =="
systemctl restart couple-diary

echo "== Wait for healthz =="
healthy=0
for _ in $(seq 1 30); do
    if curl -fsS http://127.0.0.1:8000/healthz | grep -q '"status":"ok"'; then
        healthy=1
        break
    fi
    sleep 1
done

if [ "$healthy" -ne 1 ]; then
    echo "ROLLBACK: /healthz failed"
    gunzip < "$DATA_DIR/backups/pre-deploy/${ts}.sql.gz" | mysql -uroot couple_diary
    sudo -u "$APP_USER" git reset --hard HEAD~1
    systemctl restart couple-diary
    exit 1
fi

echo "== Deploy OK =="
