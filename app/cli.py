"""Couple Diary CLI.

Entry points:
  python -m app.cli init-couple --he <name> --she <name>
  python -m app.cli generate-vapid   (placeholder for M2 PWA push)
"""
from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.modules.auth.invite import create_couple_and_invites


def _make_session() -> sessionmaker:  # type: ignore[type-arg]
    settings = get_settings()
    # Use the TEST DB if APP_ENV=test, else the production DB.
    url = (
        settings.database_test_url
        if settings.app_env == "test" and settings.database_test_url
        else settings.database_url
    )
    return sessionmaker(bind=create_engine(url, future=True), future=True)


def cmd_init_couple(args: argparse.Namespace) -> int:
    Session = _make_session()
    with Session() as db:
        try:
            he_token, she_token = create_couple_and_invites(
                db, he_name=args.he, she_name=args.she,
            )
            db.commit()
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            db.rollback()
            return 1

    base = os.environ.get("BIND_BASE_URL", "http://localhost:8000")
    print(f"He   ({args.he}):  {base}/bind?token={he_token}")
    print(f"She  ({args.she}):  {base}/bind?token={she_token}")
    print()
    print("Tokens expire in 7 days. Share each link with the corresponding partner.")
    return 0


def cmd_generate_vapid(args: argparse.Namespace) -> int:
    print("generate-vapid is a placeholder; implemented in M2 Web Push task.",
          file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="couple-diary")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init-couple", help="Create the 2 users and their invite tokens")
    p_init.add_argument("--he", required=True, help="Display name for the partner with role=he")
    p_init.add_argument("--she", required=True, help="Display name for the partner with role=she")
    p_init.set_defaults(func=cmd_init_couple)

    p_vapid = sub.add_parser("generate-vapid", help="Generate VAPID push keypair (M2)")
    p_vapid.set_defaults(func=cmd_generate_vapid)

    ns = parser.parse_args(argv)
    return int(ns.func(ns))


if __name__ == "__main__":
    sys.exit(main())
