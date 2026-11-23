"""Audit trail: who called what, and whether it worked. IDs and hashes only, no names or answers."""

import hashlib
import json
import logging

from app.db.pools import Identity
from app.repos import auth_repo

logger = logging.getLogger("attendfx.audit")


def hash_args(args: dict) -> str:
    canonical = json.dumps(args, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def record(
    identity: Identity | None,
    *,
    surface: str,
    action: str,
    args: dict,
    status: str,
    latency_ms: int,
    request_id: str | None,
) -> None:
    """Write one audit row. A failure here is logged but never breaks the request.

    `identity` is None for operator (CLI) actions, recorded with no user.
    """
    try:
        auth_repo.insert_audit(
            user_id=identity.user_id if identity else None,
            key_id=identity.key_id if identity else None,
            surface=surface,
            action=action,
            args_hash=hash_args(args),
            status=status,
            latency_ms=latency_ms,
            request_id=request_id,
        )
    except Exception:
        logger.exception("failed to write audit row")
