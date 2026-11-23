"""Access keys: format `afx_<prefix>_<secret>`.

Only the prefix (for lookup) and a SHA-256 of the secret are stored. A fast hash is appropriate
because the secret is 256 bits of randomness, so there is nothing to brute-force.
"""

import hashlib
import hmac
import secrets
from dataclasses import dataclass

KEY_TAG = "afx"


@dataclass(frozen=True)
class ParsedKey:
    prefix: str
    secret: str


def generate_key() -> tuple[str, str, str]:
    """Return (full_key, prefix, secret_hash). The full key is shown to the user once."""
    prefix = secrets.token_hex(4)  # 8 hex chars, no underscores
    secret = secrets.token_urlsafe(32)
    return f"{KEY_TAG}_{prefix}_{secret}", prefix, hash_secret(secret)


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def parse_key(raw: str) -> ParsedKey | None:
    parts = raw.strip().split("_", 2)
    if len(parts) != 3 or parts[0] != KEY_TAG:
        return None
    _, prefix, secret = parts
    if len(prefix) != 8 or not secret:
        return None
    return ParsedKey(prefix=prefix, secret=secret)


def secrets_match(secret: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_secret(secret), stored_hash)


# Used to burn the same CPU time when a prefix is unknown, so lookups do not leak existence.
DUMMY_HASH = hash_secret("dummy")
