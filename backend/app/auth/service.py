"""Turn a presented access key into a verified Identity, or nothing."""

from datetime import UTC, datetime

from app.auth.keys import DUMMY_HASH, parse_key, secrets_match
from app.db.pools import Identity
from app.repos import auth_repo


def authenticate_key(raw: str) -> Identity | None:
    """Verify a bearer key. Every failure returns None, so callers cannot tell why it failed."""
    parsed = parse_key(raw)
    if parsed is None:
        secrets_match("x", DUMMY_HASH)  # keep timing similar to the real path
        return None

    record = auth_repo.find_key(parsed.prefix)
    matches = secrets_match(parsed.secret, record.secret_hash if record else DUMMY_HASH)
    if record is None or not matches:
        return None
    if record.revoked_at is not None:
        return None
    if record.expires_at is not None and record.expires_at <= datetime.now(UTC):
        return None

    auth_repo.touch_key(record.id)
    return Identity(user_id=record.user_id, role=record.role, key_id=record.id)
