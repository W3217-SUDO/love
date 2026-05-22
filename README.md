# Couple Diary

Private two-person web app for tracking cycle, intimacy, mood, and shared memories.

See [design spec](docs/superpowers/specs/2026-05-22-couple-diary-design.md) and [M1 plan](docs/superpowers/plans/2026-05-22-couple-diary-m1.md).

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

## Dev DB access (SSH tunnel)

Production MariaDB binds to `127.0.0.1` only (see spec §8.3). For dev against
the prod-style DB on `150.158.3.104`, start a local SSH tunnel BEFORE running
tests or the app:

```bash
ssh -i 密钥/tencent_cloud -fN -L 13306:127.0.0.1:3306 \
    -o ServerAliveInterval=30 root@150.158.3.104
```

Then point your `.env` at `127.0.0.1:13306` (already the default in `.env.example`
once edited). Check the tunnel is alive with `netstat -an | findstr 13306` on
Windows or `ss -tlnp | grep 13306` on Linux.

If your network sits behind a VPN/CGNAT (e.g., 198.18.0.x routes), direct TCP
to 3306 will be silently dropped — the tunnel is required.
