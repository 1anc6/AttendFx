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


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.worker")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed", help="load deterministic fake development data")
    prune = sub.add_parser("prune-audit", help="delete old audit log rows")
    prune.add_argument("--days", type=int, default=90)
    args = parser.parse_args()

    if args.command == "seed":
        from app.worker.seed import seed

        for table, count in seed().items():
            print(f"{table}: {count} rows upserted")
    elif args.command == "prune-audit":
        print(f"deleted {prune_audit(args.days)} audit rows")


if __name__ == "__main__":
    main()
