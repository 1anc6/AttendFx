"""Operator CLI: `python -m app.worker <command>`.

Runs with database credentials, so it acts as the trusted operator (actor=None). Key actions
are audited with surface 'cli'.
"""

import argparse
import sys

import psycopg

from app.config import get_settings


def prune_audit(days: int = 90) -> int:
    with psycopg.connect(get_settings().sync_database_url) as conn:
        cur = conn.execute(
            "DELETE FROM audit_log WHERE ts < now() - make_interval(days => %s)", (days,)
        )
        return cur.rowcount


def _user_id(email: str):
    from app.repos import auth_repo

    user = auth_repo.find_user_by_email(email)
    if user is None:
        raise SystemExit("No user with that email.")
    return user[0]


def create_key(email: str, name: str, days: int) -> str:
    from app.services import keys

    issued = keys.issue_key(None, _user_id(email), name, days)
    expires = issued["expires_at"][:10]
    return f"{issued['key']}\n(shown once; prefix {issued['prefix']}, expires {expires})"


def list_keys(email: str) -> str:
    from app.services import keys

    rows = keys.list_keys(None, _user_id(email))
    if not rows:
        return "No keys."
    lines = [f"{'PREFIX':<10}{'STATUS':<9}{'EXPIRES':<12}{'LAST USED':<12}NAME"]
    for k in rows:
        last = (k["last_used_at"] or "never")[:10]
        expires = (k["expires_at"] or "-")[:10]
        lines.append(f"{k['prefix']:<10}{k['status']:<9}{expires:<12}{last:<12}{k['name']}")
    return "\n".join(lines)


def revoke_key(prefix: str) -> str:
    from app.services import keys

    result = keys.revoke_key_by_prefix(None, prefix)
    return "Already revoked." if result["was_already_revoked"] else f"Revoked key {prefix}."


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.worker")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed", help="load deterministic fake development data")
    prune = sub.add_parser("prune-audit", help="delete old audit log rows")
    prune.add_argument("--days", type=int, default=90)
    create = sub.add_parser("create-key", help="issue an access key for a user (shown once)")
    create.add_argument("--email", required=True)
    create.add_argument("--name", default="cli")
    create.add_argument("--days", type=int, default=90, help="days until it expires (1-365)")
    listing = sub.add_parser("list-keys", help="list a user's keys (never the secret)")
    listing.add_argument("--email", required=True)
    revoke = sub.add_parser("revoke-key", help="revoke a key by its 8-character prefix")
    revoke.add_argument("--prefix", required=True)
    args = parser.parse_args()

    from app.services.common import UserError

    try:
        if args.command == "create-key":
            print(create_key(args.email, args.name, args.days))
        elif args.command == "list-keys":
            print(list_keys(args.email))
        elif args.command == "revoke-key":
            print(revoke_key(args.prefix))
        elif args.command == "seed":
            from app.worker.seed import seed

            for table, count in seed().items():
                print(f"{table}: {count} rows upserted")
        elif args.command == "prune-audit":
            print(f"deleted {prune_audit(args.days)} audit rows")
    except UserError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
