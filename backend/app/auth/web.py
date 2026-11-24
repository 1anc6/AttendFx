"""Web sign-in: email and password (argon2id), account lockout, server-side sessions.

- The session cookie holds a random token. The database stores only its SHA-256, so a leaked
  `web_sessions` table does not hand out live sessions.
- Unknown emails cost the same argon2 work as real ones and get the same answer.
- After `login_max_failures` wrong passwords in a row the account locks for
  `login_lock_minutes`. While locked, the password is not even checked.
- Each session has its own CSRF token; state-changing requests must echo it in a header.
- A turned-off account is refused only after the right password, so the message does not
  tell strangers which emails exist.
- Admins hand out temporary passwords. Those sessions must set a new password first.
"""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.audit import log as audit
from app.config import get_settings
from app.db.pools import Identity
from app.repos import session_repo
from app.services.common import UserError

_hasher = PasswordHasher()
# Verified against when the email is unknown, so both paths take the same time.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))

MAX_TOKEN_LENGTH = 128
MIN_PASSWORD = 12
MAX_PASSWORD = 128
# No 0/o, 1/l/i: temporary passwords get read aloud and typed by hand.
_TEMP_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


class SignInFailed(Exception):
    """Wrong email or password. Deliberately says nothing about which."""


class AccountLocked(Exception):
    def __init__(self, until: datetime) -> None:
        super().__init__("Account temporarily locked.")
        self.until = until


class AccountDisabled(Exception):
    """Right password, but an admin has turned the account off."""


class WrongPassword(UserError):
    def __init__(self) -> None:
        super().__init__("Your current password is wrong.")


@dataclass(frozen=True)
class WebSession:
    identity: Identity
    name: str
    email: str
    csrf_token: str
    expires_at: datetime
    must_change_password: bool = False


@dataclass(frozen=True)
class SignIn:
    token: str  # goes in the cookie, never stored server-side
    session: WebSession


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def new_temporary_password() -> str:
    """Four groups of four, about 79 bits: k7mq-3xpt-9hdr-w2fn."""
    chars = "".join(secrets.choice(_TEMP_ALPHABET) for _ in range(16))
    return "-".join(chars[i : i + 4] for i in range(0, 16, 4))


def check_new_password(new: str, *, current: str, email: str) -> None:
    """Length is what matters (NIST 800-63B): no composition rules, no forced rotation."""
    if len(new) < MIN_PASSWORD:
        raise UserError(f"Use at least {MIN_PASSWORD} characters.")
    if len(new) > MAX_PASSWORD:
        raise UserError(f"Use at most {MAX_PASSWORD} characters.")
    if new == current:
        raise UserError("Choose a password different from your current one.")
    if new.strip().lower() in (email.lower(), email.split("@")[0].lower()):
        raise UserError("Don't use your email as your password.")
    if len(set(new)) < 4:
        raise UserError("That password is too easy to guess. Try a few words together.")


def _verify(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def _audit(identity: Identity | None, action: str, status: str) -> None:
    audit.record(
        identity,
        surface="api",
        action=action,
        args={},
        status=status,
        latency_ms=0,
        request_id=None,
    )


def sign_in(email: str, password: str) -> SignIn:
    settings = get_settings()
    now = datetime.now(UTC)
    record = session_repo.find_login(email.strip()) if email.strip() else None
    if record is None:
        _verify(_DUMMY_HASH, password)
        _audit(None, "web.sign_in", "invalid")
        raise SignInFailed()

    who = Identity(user_id=record.id, role=record.role)
    if record.locked_until is not None and record.locked_until > now:
        _audit(who, "web.sign_in", "locked")
        raise AccountLocked(record.locked_until)

    if not _verify(record.password_hash, password):
        locked_until = session_repo.record_failure(
            record.id, settings.login_max_failures, settings.login_lock_minutes
        )
        if locked_until is not None and locked_until > now:
            _audit(who, "web.sign_in", "locked")
            raise AccountLocked(locked_until)
        _audit(who, "web.sign_in", "invalid")
        raise SignInFailed()

    if record.disabled_at is not None:
        _audit(who, "web.sign_in", "disabled")
        raise AccountDisabled()

    upgraded = _hasher.hash(password) if _hasher.check_needs_rehash(record.password_hash) else None
    session_repo.record_success(record.id, upgraded)

    token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    expires_at = now + timedelta(hours=settings.session_hours)
    session_repo.create_session(hash_token(token), record.id, csrf_token, expires_at)
    _audit(who, "web.sign_in", "ok")
    return SignIn(
        token=token,
        session=WebSession(
            who, record.name, record.email, csrf_token, expires_at, record.must_change_password
        ),
    )


def current_session(token: str | None) -> WebSession | None:
    if not token or len(token) > MAX_TOKEN_LENGTH:
        return None
    record = session_repo.find_session(hash_token(token))
    if record is None:
        return None
    return WebSession(
        Identity(user_id=record.user_id, role=record.role),
        record.name,
        record.email,
        record.csrf_token,
        record.expires_at,
        record.must_change_password,
    )


def csrf_ok(session: WebSession, header_value: str | None) -> bool:
    return bool(header_value) and hmac.compare_digest(
        session.csrf_token.encode(), header_value.encode()
    )


def sign_out(token: str, session: WebSession) -> None:
    session_repo.delete_session(hash_token(token))
    _audit(session.identity, "web.sign_out", "ok")


def set_password_for(user_id: UUID, password: str, *, must_change: bool) -> bool:
    """Set someone's password (admin reset). Clears lockout, ends all their web sessions."""
    return session_repo.set_password(user_id, hash_password(password), must_change=must_change)


def change_password(session: WebSession, token: str, current: str, new: str) -> None:
    """Change your own password. Needs the current one, which counts toward the lockout like
    a sign-in, so a borrowed session cannot be used to guess it. Ends your other sessions."""
    settings = get_settings()
    now = datetime.now(UTC)
    who = session.identity
    record = session_repo.find_login_by_id(who.user_id)
    if record is None:
        raise SignInFailed()
    if record.locked_until is not None and record.locked_until > now:
        _audit(who, "account.password_change", "locked")
        raise AccountLocked(record.locked_until)
    if not _verify(record.password_hash, current):
        locked_until = session_repo.record_failure(
            record.id, settings.login_max_failures, settings.login_lock_minutes
        )
        if locked_until is not None and locked_until > now:
            _audit(who, "account.password_change", "locked")
            raise AccountLocked(locked_until)
        _audit(who, "account.password_change", "invalid")
        raise WrongPassword()
    try:
        check_new_password(new, current=current, email=record.email)
    except UserError:
        _audit(who, "account.password_change", "rejected")
        raise
    session_repo.set_password(
        record.id, hash_password(new), must_change=False, keep_session=hash_token(token)
    )
    _audit(who, "account.password_change", "ok")
