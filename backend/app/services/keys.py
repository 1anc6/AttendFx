"""Access key lifecycle: issue, list, revoke. Shared by the CLI now and the web API later.

`actor` is who is acting: a verified Identity (web API), or None for the operator CLI, which
is trusted because it runs with database credentials.

Rules:
- Everyone creates keys only for themselves. Nobody, not even an admin, mints a key that acts
  as someone else; only the operator CLI can (for bootstrapping and support).
- Every key expires: 1 to 365 days, default 90.
- At most 10 usable (not revoked, not expired) keys per person.
- Owners revoke their own keys; admins can revoke anyone's (incident response).
- A key you may not see looks exactly like a key that does not exist.
"""

import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.audit import log as audit
from app.auth.keys import generate_key
from app.db.pools import Identity
from app.repos import auth_repo
from app.services.common import Denied, UserError

DEFAULT_KEY_DAYS = 90
MAX_KEY_DAYS = 365
MAX_ACTIVE_KEYS = 10
KEY_NAME = re.compile(r"^[\w .,:()@/-]{1,60}$")


class KeyNotFound(UserError):
    def __init__(self) -> None:
        super().__init__("No such key.")


def _surface(actor: Identity | None) -> str:
    return "cli" if actor is None else "api"


def _audit(actor: Identity | None, action: str, args: dict, status: str) -> None:
    audit.record(
        actor,
        surface=_surface(actor),
        action=action,
        args=args,
        status=status,
        latency_ms=0,
        request_id=None,
    )


def _status(expires_at: datetime | None, revoked_at: datetime | None, now: datetime) -> str:
    if revoked_at is not None:
        return "revoked"
    if expires_at is not None and expires_at <= now:
        return "expired"
    return "active"


def issue_key(
    actor: Identity | None, owner_id: UUID, name: str, days: int = DEFAULT_KEY_DAYS
) -> dict[str, Any]:
    """Create a key. The returned `key` is the only time the full value is ever available."""
    args = {"owner_id": owner_id, "name": name, "days": days}
    if actor is not None and actor.user_id != owner_id:
        _audit(actor, "key.create", args, "denied")
        raise Denied("You can only create keys for yourself.")
    name = name.strip()
    if not KEY_NAME.match(name):
        raise UserError("Key name must be 1 to 60 letters, digits, spaces or . , : ( ) @ / -")
    if not 1 <= days <= MAX_KEY_DAYS:
        raise UserError(f"Keys must expire in 1 to {MAX_KEY_DAYS} days.")

    full_key, prefix, secret_hash = generate_key()
    expires_at = datetime.now(UTC) + timedelta(days=days)
    outcome, key_id = auth_repo.create_key_limited(
        owner_id, name, prefix, secret_hash, expires_at, MAX_ACTIVE_KEYS
    )
    if outcome == "no_user":
        raise UserError("No such user.")
    if outcome == "limit":
        _audit(actor, "key.create", args, "limit")
        raise UserError(
            f"You already have {MAX_ACTIVE_KEYS} active keys. Revoke one you no longer use."
        )
    _audit(actor, "key.create", args, "ok")
    return {
        "id": str(key_id),
        "key": full_key,
        "prefix": prefix,
        "name": name,
        "expires_at": expires_at.isoformat(),
    }


def list_keys(actor: Identity | None, owner_id: UUID) -> list[dict[str, Any]]:
    if actor is not None and actor.user_id != owner_id and actor.role != "admin":
        raise Denied("You can only list your own keys.")
    now = datetime.now(UTC)
    return [
        {
            "id": str(key_id),
            "name": name,
            "prefix": prefix,
            "created_at": created.isoformat(),
            "last_used_at": last_used.isoformat() if last_used else None,
            "expires_at": expires.isoformat() if expires else None,
            "revoked_at": revoked.isoformat() if revoked else None,
            "status": _status(expires, revoked, now),
        }
        for key_id, name, prefix, created, last_used, expires, revoked in auth_repo.list_keys(
            owner_id
        )
    ]


def revoke_key(actor: Identity | None, key_id: UUID) -> dict[str, Any]:
    """Revoke a key. Takes effect on the very next request made with it. Idempotent."""
    owner = auth_repo.get_key_owner(key_id)
    allowed = owner is not None and (
        actor is None or actor.user_id == owner[0] or actor.role == "admin"
    )
    if not allowed:
        _audit(actor, "key.revoke", {"key_id": key_id}, "not_found")
        raise KeyNotFound()
    changed = auth_repo.revoke_key(key_id)
    _audit(actor, "key.revoke", {"key_id": key_id}, "ok" if changed else "already_revoked")
    return {"id": str(key_id), "status": "revoked", "was_already_revoked": not changed}


def revoke_key_by_prefix(actor: Identity | None, prefix: str) -> dict[str, Any]:
    key_id = auth_repo.find_key_id_by_prefix(prefix)
    if key_id is None:
        raise KeyNotFound()
    return revoke_key(actor, key_id)
