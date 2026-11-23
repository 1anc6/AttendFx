"""Worker CLI: `python -m app.worker <command>`."""

import argparse

import psycopg

from app.config import get_settings


def prune_audit(days: int = 90) -> int:
    with psycopg.connect(get_settings().sync_database_url) as conn:
        cur = conn.execute(
            "DELETE FROM audit_log WHERE ts < now() - make_interval(days => %s)", (days,)
        )
        return cur.rowcount


def create_key(email: str, name: str, days: int) -> str:
    from datetime import UTC, datetime, timedelta

    from app.auth.keys import generate_key
    from app.repos import auth_repo

    user = auth_repo.find_user_by_email(email)
    if user is None:
        raise SystemExit("No user with that email.")
    full_key, prefix, secret_hash = generate_key()
    expires_at = datetime.now(UTC) + timedelta(days=days)
    auth_repo.create_key(user[0], name, prefix, secret_hash, expires_at)
    return f"{full_key}\n(shown once; expires {expires_at:%Y-%m-%d})"


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.worker")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed", help="load deterministic fake development data")
    prune = sub.add_parser("prune-audit", help="delete old audit log rows")
    prune.add_argument("--days", type=int, default=90)
    key = sub.add_parser("create-key", help="mint an access key for a user (shown once)")
    key.add_argument("--email", required=True)
    key.add_argument("--name", default="cli")
    key.add_argument("--days", type=int, default=90, help="days until the key expires")
    args = parser.parse_args()

    if args.command == "create-key":
        print(create_key(args.email, args.name, args.days))
    elif args.command == "seed":
        from app.worker.seed import seed

        for table, count in seed().items():
            print(f"{table}: {count} rows upserted")
    elif args.command == "prune-audit":
        print(f"deleted {prune_audit(args.days)} audit rows")


if __name__ == "__main__":
    main()
