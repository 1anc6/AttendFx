"""JSON API for the web app, under /api. Authenticated by a session cookie, not access keys.

Every route runs as the signed-in person. State-changing routes also need the session's CSRF
token in the X-CSRF-Token header. Endpoints are plain `def`, so FastAPI runs them in its
thread pool, matching the synchronous database layer.

A session signed in with a temporary password may only read /api/me, change its password and
sign out. /api/people is for admins only.
"""

import math
from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.auth import web
from app.config import get_settings
from app.ratelimit.limiter import TokenBucketLimiter
from app.services import keys, people
from app.services.common import Denied, UserError

COOKIE = "__Host-afx_session"  # __Host- forces Secure, Path=/ and no Domain
CSRF_HEADER = "X-CSRF-Token"


class WebLimits:
    """Swappable in tests, like the MCP limiters."""

    def __init__(self) -> None:
        s = get_settings()
        self.login_failures = TokenBucketLimiter(
            s.login_failures_per_minute, s.login_failures_burst
        )
        self.per_user = TokenBucketLimiter(s.rate_limit_per_minute, s.rate_limit_burst)


limits = WebLimits()
router = APIRouter(prefix="/api")


class SignInBody(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=1024)


class NewKeyBody(BaseModel):
    name: str = Field(max_length=100)
    days: int = keys.DEFAULT_KEY_DAYS


class ChangePasswordBody(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=1, max_length=1024)


class NewPersonBody(BaseModel):
    name: str = Field(max_length=200)
    email: str = Field(max_length=254)
    role: str = Field(max_length=20)


class ImportBody(BaseModel):
    csv: str = Field(max_length=people.MAX_IMPORT_CHARS)
    dry_run: bool = True


class DisableBody(BaseModel):
    disabled: bool


def _too_many(retry_after: int) -> HTTPException:
    return HTTPException(
        429,
        detail="Too many requests. Wait a moment and try again.",
        headers={"Retry-After": str(retry_after)},
    )


def _lock_message(until: datetime) -> str:
    minutes = max(1, math.ceil((until - datetime.now(UTC)).total_seconds() / 60))
    unit = "minute" if minutes == 1 else "minutes"
    return f"Too many wrong passwords. Try again in {minutes} {unit}."


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def current_session(request: Request) -> web.WebSession:
    session = web.current_session(request.cookies.get(COOKIE))
    if session is None:
        raise HTTPException(401, detail="Sign in first.")
    decision = limits.per_user.try_acquire(str(session.identity.user_id))
    if not decision.allowed:
        raise _too_many(decision.retry_after)
    return session


def csrf_session(
    request: Request, session: Annotated[web.WebSession, Depends(current_session)]
) -> web.WebSession:
    if not web.csrf_ok(session, request.headers.get(CSRF_HEADER)):
        raise HTTPException(403, detail="Missing or wrong CSRF token. Reload the page.")
    return session


def _ready(session: web.WebSession) -> web.WebSession:
    if session.must_change_password:
        raise HTTPException(403, detail="Choose a new password first.")
    return session


def ready_session(
    session: Annotated[web.WebSession, Depends(current_session)],
) -> web.WebSession:
    return _ready(session)


def ready_csrf_session(
    session: Annotated[web.WebSession, Depends(csrf_session)],
) -> web.WebSession:
    return _ready(session)


def _admin(session: web.WebSession) -> web.WebSession:
    if session.identity.role != "admin":
        raise HTTPException(403, detail="Only admins can do this.")
    return session


def admin_session(
    session: Annotated[web.WebSession, Depends(ready_session)],
) -> web.WebSession:
    return _admin(session)


def admin_csrf_session(
    session: Annotated[web.WebSession, Depends(ready_csrf_session)],
) -> web.WebSession:
    return _admin(session)


Session = Annotated[web.WebSession, Depends(current_session)]
CsrfSession = Annotated[web.WebSession, Depends(csrf_session)]
ReadySession = Annotated[web.WebSession, Depends(ready_session)]
ReadyCsrfSession = Annotated[web.WebSession, Depends(ready_csrf_session)]
AdminSession = Annotated[web.WebSession, Depends(admin_session)]
AdminCsrfSession = Annotated[web.WebSession, Depends(admin_csrf_session)]


def _me(session: web.WebSession) -> dict[str, Any]:
    return {
        "user": {
            "id": str(session.identity.user_id),
            "name": session.name,
            "email": session.email,
            "role": session.identity.role,
        },
        "must_change_password": session.must_change_password,
        "csrf_token": session.csrf_token,
        "expires_at": session.expires_at.isoformat(),
    }


@router.post("/auth/sign-in")
def sign_in(body: SignInBody, request: Request, response: Response) -> dict[str, Any]:
    ip = _client_ip(request)
    blocked = limits.login_failures.peek(ip)
    if not blocked.allowed:
        raise _too_many(blocked.retry_after)
    try:
        result = web.sign_in(body.email, body.password)
    except web.AccountLocked as exc:
        limits.login_failures.try_acquire(ip)
        raise HTTPException(423, detail=_lock_message(exc.until)) from None
    except web.SignInFailed:
        limits.login_failures.try_acquire(ip)
        raise HTTPException(401, detail="Email or password is wrong.") from None
    except web.AccountDisabled:
        raise HTTPException(
            403, detail="This account is turned off. Ask an admin to turn it back on."
        ) from None
    response.set_cookie(
        COOKIE,
        result.token,
        max_age=get_settings().session_hours * 3600,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )
    return _me(result.session)


@router.post("/auth/sign-out", status_code=204)
def sign_out(request: Request, session: CsrfSession) -> Response:
    web.sign_out(request.cookies[COOKIE], session)
    response = Response(status_code=204)
    response.delete_cookie(COOKIE, path="/", secure=True, httponly=True, samesite="lax")
    return response


@router.get("/me")
def me(session: Session) -> dict[str, Any]:
    return _me(session)


@router.post("/account/password")
def change_password(
    body: ChangePasswordBody, request: Request, session: CsrfSession
) -> dict[str, Any]:
    """Works with a temporary password too: this is how you replace it."""
    token = request.cookies[COOKIE]
    try:
        web.change_password(session, token, body.current_password, body.new_password)
    except web.AccountLocked as exc:
        raise HTTPException(423, detail=_lock_message(exc.until)) from None
    return _me(web.current_session(token) or session)


@router.get("/keys")
def list_keys(session: ReadySession) -> dict[str, Any]:
    rows = keys.list_keys(session.identity, session.identity.user_id)
    return {
        "keys": rows,
        "active": sum(1 for k in rows if k["status"] == "active"),
        "max_active": keys.MAX_ACTIVE_KEYS,
        "max_days": keys.MAX_KEY_DAYS,
    }


@router.post("/keys", status_code=201)
def create_key(body: NewKeyBody, session: ReadyCsrfSession) -> dict[str, Any]:
    return keys.issue_key(session.identity, session.identity.user_id, body.name, body.days)


@router.post("/keys/{key_id}/revoke")
def revoke_key(key_id: UUID, session: ReadyCsrfSession) -> dict[str, Any]:
    return keys.revoke_key(session.identity, key_id)


@router.get("/people")
def list_people(
    session: AdminSession,
    q: Annotated[str, Query(max_length=100)] = "",
    role: Literal["student", "teacher", "admin"] | None = None,
    status: Literal["all", "active", "locked", "must_change", "disabled"] = "all",
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
) -> dict[str, Any]:
    return people.list_people(session.identity, search=q, role=role, status=status, page=page)


@router.post("/people", status_code=201)
def create_person(body: NewPersonBody, session: AdminCsrfSession) -> dict[str, Any]:
    return people.create_person(session.identity, body.name, body.email, body.role)


@router.post("/people/import")
def import_people(body: ImportBody, session: AdminCsrfSession) -> dict[str, Any]:
    return people.import_people(session.identity, body.csv, dry_run=body.dry_run)


@router.post("/people/{person_id}/reset-password")
def reset_password(person_id: UUID, session: AdminCsrfSession) -> dict[str, Any]:
    return people.reset_password(session.identity, person_id)


@router.post("/people/{person_id}/unlock")
def unlock_person(person_id: UUID, session: AdminCsrfSession) -> dict[str, Any]:
    return people.unlock(session.identity, person_id)


@router.post("/people/{person_id}/disabled")
def set_person_disabled(
    person_id: UUID, body: DisableBody, session: AdminCsrfSession
) -> dict[str, Any]:
    return people.set_disabled(session.identity, person_id, body.disabled)


def install(app: FastAPI) -> None:
    """Add the router and map service errors to HTTP answers."""

    @app.exception_handler(keys.KeyNotFound)
    @app.exception_handler(people.PersonNotFound)
    def _not_found(_: Request, exc: UserError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(Denied)
    def _denied(_: Request, exc: Denied) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=403)

    @app.exception_handler(UserError)
    def _user_error(_: Request, exc: UserError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    app.include_router(router)
