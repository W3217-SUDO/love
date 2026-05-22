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
