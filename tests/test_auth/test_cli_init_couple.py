import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_cli_init_couple_prints_bind_urls(db):
    """Smoke-test the CLI as a subprocess. Uses the real (test) DB via .env.

    NOTE: This test invokes `python -m app.cli init-couple ...`.
    It will REFUSE if users exist; the conftest's per-test transaction rollback
    doesn't affect subprocess (subprocess has its own connection / commit).
    So we directly clear the relevant tables BEFORE the subprocess runs, and
    again after to leave the DB clean for subsequent tests.
    """
    from sqlalchemy import delete

    from app.modules.auth.models import Couple, InviteToken, User
    from tests.conftest import TestSessionLocal

    # Wipe BEFORE
    with TestSessionLocal() as s:
        s.execute(delete(InviteToken))
        s.execute(delete(Couple))
        s.execute(delete(User))
        s.commit()

    try:
        env_overrides = {"APP_ENV": "test"}
        # Use the venv python explicitly
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.cli",
                "init-couple",
                "--he",
                "Aaron",
                "--she",
                "Beth",
            ],
            cwd=REPO,
            capture_output=True,
            text=True,
            env={**__import__("os").environ, **env_overrides},
            timeout=30,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
        assert "Aaron" in result.stdout
        assert "Beth" in result.stdout
        assert "/bind?token=" in result.stdout
    finally:
        # Wipe AFTER so subsequent tests have a clean DB
        with TestSessionLocal() as s:
            s.execute(delete(InviteToken))
            s.execute(delete(Couple))
            s.execute(delete(User))
            s.commit()


def test_cli_init_couple_refuses_when_exists(db):
    """Run twice; the second call should exit non-zero."""
    from sqlalchemy import delete

    from app.modules.auth.models import Couple, InviteToken, User
    from tests.conftest import TestSessionLocal

    with TestSessionLocal() as s:
        s.execute(delete(InviteToken))
        s.execute(delete(Couple))
        s.execute(delete(User))
        s.commit()

    try:
        first = subprocess.run(
            [sys.executable, "-m", "app.cli", "init-couple",
             "--he", "X", "--she", "Y"],
            cwd=REPO, capture_output=True, text=True,
            env={**__import__("os").environ, "APP_ENV": "test"},
            timeout=30,
        )
        assert first.returncode == 0

        second = subprocess.run(
            [sys.executable, "-m", "app.cli", "init-couple",
             "--he", "P", "--she", "Q"],
            cwd=REPO, capture_output=True, text=True,
            env={**__import__("os").environ, "APP_ENV": "test"},
            timeout=30,
        )
        assert second.returncode != 0
    finally:
        with TestSessionLocal() as s:
            s.execute(delete(InviteToken))
            s.execute(delete(Couple))
            s.execute(delete(User))
            s.commit()
