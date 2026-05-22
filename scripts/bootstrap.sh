#!/usr/bin/env bash
# Couple Diary first-time server bootstrap.
# Idempotent: safe to re-run.
#
# Run as root on the production server.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/W3217-SUDO/love.git}"
APP_DIR="/opt/couple_diary"
DATA_DIR="/data"
LOG_DIR="/var/log/couple_diary"
APP_USER="couple"

echo "== 1. Create system user =="
if ! id -u "$APP_USER" >/dev/null 2>&1; then
    useradd -r -s /usr/sbin/nologin "$APP_USER"
fi

echo "== 2. Create directories =="
mkdir -p "$APP_DIR" "$DATA_DIR/uploads" "$DATA_DIR/backups/db" "$DATA_DIR/backups/uploads-mirror" "$DATA_DIR/backups/pre-deploy" "$LOG_DIR"
chmod 700 "$DATA_DIR/uploads" "$DATA_DIR/backups"

echo "== 3. Install OS packages =="
# OpenCloudOS's dnf.conf excludes nginx/httpd by default. Use --disableexcludes
# to bypass that policy for just this install (does NOT modify dnf.conf).
dnf install -y --disableexcludes=all python3 python3-pip nginx nginx-core nginx-filesystem openssl gcc gcc-c++ python3-devel git

echo "== 4. Clone or update repo =="
if [ ! -d "$APP_DIR/.git" ]; then
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
    git checkout feature/m1
else
    cd "$APP_DIR"
    git fetch origin
    git checkout feature/m1
    git pull origin feature/m1
fi

echo "== 5. Create venv and install deps =="
PYTHON_BIN="$(command -v python3.11 || command -v python3)"
"$PYTHON_BIN" -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -e "$APP_DIR"

echo "== 6. Generate self-signed cert =="
mkdir -p /etc/nginx/ssl
if [ ! -f /etc/nginx/ssl/couple.crt ]; then
    openssl req -x509 -newkey rsa:4096 -nodes \
        -keyout /etc/nginx/ssl/couple.key \
        -out /etc/nginx/ssl/couple.crt \
        -days 365 -subj "/CN=150.158.3.104"
    chmod 600 /etc/nginx/ssl/couple.key
fi

echo "== 7. Harden MariaDB =="
HARDEN_CONF=/etc/my.cnf.d/couple-bind.cnf
cp "$APP_DIR/deploy/my-cnf-hardening.cnf" "$HARDEN_CONF"
systemctl restart mariadb

echo "== 8. Set up DB and user =="
MYSQL_PWD="${MYSQL_APP_PWD:-couple-prod-pwd-CHANGE-ME}"
mysql -uroot <<SQL
CREATE DATABASE IF NOT EXISTS couple_diary CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'couple'@'127.0.0.1' IDENTIFIED BY '${MYSQL_PWD}';
ALTER USER 'couple'@'127.0.0.1' IDENTIFIED BY '${MYSQL_PWD}';
GRANT ALL ON couple_diary.* TO 'couple'@'127.0.0.1';
FLUSH PRIVILEGES;
SQL

echo "== 9. Write .env.production =="
if [ ! -f "$APP_DIR/.env.production" ]; then
    SECRET_KEY=$(openssl rand -hex 32)
    cat > "$APP_DIR/.env.production" <<ENV
APP_ENV=production
SECRET_KEY=${SECRET_KEY}
DATABASE_URL=mysql+pymysql://couple:${MYSQL_PWD}@127.0.0.1/couple_diary?charset=utf8mb4
UPLOAD_DIR=${DATA_DIR}/uploads
BACKUP_DIR=${DATA_DIR}/backups
LOG_DIR=${LOG_DIR}
SESSION_COOKIE_NAME=cdsid
SESSION_MAX_AGE_DAYS=30
COOKIE_SECURE=true
ENV
fi
chmod 600 "$APP_DIR/.env.production"

echo "== 10. Permissions =="
chown -R "$APP_USER:$APP_USER" "$APP_DIR" "$DATA_DIR" "$LOG_DIR"

echo "== 11. Apply Alembic migrations =="
sudo -u "$APP_USER" bash -c "cd $APP_DIR && set -a && . $APP_DIR/.env.production && set +a && $APP_DIR/.venv/bin/python -m alembic -c $APP_DIR/alembic.ini upgrade head"

echo "== 12. Install systemd unit =="
cp "$APP_DIR/deploy/couple-diary.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable couple-diary
systemctl restart couple-diary

echo "== 13. Install nginx config =="
mkdir -p /etc/nginx/conf.d
cp "$APP_DIR/deploy/nginx-couple-diary.conf" /etc/nginx/conf.d/couple-diary.conf
# Disable default site if present (would conflict on :80)
if [ -f /etc/nginx/conf.d/default.conf ]; then
    mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.disabled || true
fi
# Some OpenCloudOS nginx packages put the default server in nginx.conf itself;
# comment out the bundled server { ... listen 80 ... } block if it exists.
if grep -q "listen.*80.*default_server" /etc/nginx/nginx.conf 2>/dev/null; then
    sed -i.bak '/^\s*server\s*{/,/^\s*}/ s/^/# /' /etc/nginx/nginx.conf || true
fi
nginx -t
systemctl enable nginx
systemctl reload nginx 2>/dev/null || systemctl restart nginx || systemctl start nginx

echo "== 14. Wait for app to be ready =="
sleep 5
if ! curl -fsS http://127.0.0.1:8000/healthz | grep -q '"status":"ok"'; then
    echo "ERROR: /healthz did not return ok"
    journalctl -u couple-diary -n 50 --no-pager
    exit 1
fi

echo ""
echo "============================================="
echo "  Bootstrap COMPLETE"
echo "============================================="
echo "  HTTPS: https://150.158.3.104/healthz (self-signed; first visit accept warning)"
echo ""
echo "  Next step: create the couple's accounts and invite tokens:"
echo "    sudo -u couple ${APP_DIR}/.venv/bin/python -m app.cli init-couple --he <your-name> --she <partner-name>"
echo ""
