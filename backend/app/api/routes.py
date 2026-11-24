"""JSON API for the web app, under /api. Authenticated by a session cookie, not access keys.

Every route runs as the signed-in person. State-changing routes also need the session's CSRF
token in the X-CSRF-Token header. Endpoints are plain `def`, so FastAPI runs them in its
thread pool, matching the synchronous database layer.
"""

import math
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.auth import web
from app.config import get_settings
from app.ratelimit.limiter import TokenBucketLimiter
from app.services import keys
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


def _too_many(retry_after: int) -> HTTPException:
    return HTTPException(
        429,
        detail="Too many requests. Wait a moment and try again.",
        headers={"Retry-After": str(retry_after)},
    )


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


Session = Annotated[web.WebSession, Depends(current_session)]
CsrfSession = Annotated[web.WebSession, Depends(csrf_session)]


def _me(session: web.WebSession) -> dict[str, Any]:
    return {
        "user": {
            "id": str(session.identity.user_id),
            "name": session.name,
            "email": session.email,
            "role": session.identity.role,
        },
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
        minutes = max(1, math.ceil((exc.until - datetime.now(UTC)).total_seconds() / 60))
        raise HTTPException(
            423,
            detail=f"Too many wrong passwords. Try again in {minutes} minute"
            f"{'' if minutes == 1 else 's'}.",
        ) from None
    except web.SignInFailed:
        limits.login_failures.try_acquire(ip)
        raise HTTPException(401, detail="Email or password is wrong.") from None
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


@router.get("/keys")
def list_keys(session: Session) -> dict[str, Any]:
    rows = keys.list_keys(session.identity, session.identity.user_id)
    return {
        "keys": rows,
        "active": sum(1 for k in rows if k["status"] == "active"),
        "max_active": keys.MAX_ACTIVE_KEYS,
        "max_days": keys.MAX_KEY_DAYS,
    }


@router.post("/keys", status_code=201)
def create_key(body: NewKeyBody, session: CsrfSession) -> dict[str, Any]:
    return keys.issue_key(session.identity, session.identity.user_id, body.name, body.days)


@router.post("/keys/{key_id}/revoke")
def revoke_key(key_id: UUID, session: CsrfSession) -> dict[str, Any]:
    return keys.revoke_key(session.identity, key_id)


def install(app: FastAPI) -> None:
    """Add the router and map service errors to HTTP answers."""

    @app.exception_handler(keys.KeyNotFound)
    def _not_found(_: Request, exc: keys.KeyNotFound) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(Denied)
    def _denied(_: Request, exc: Denied) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=403)

    @app.exception_handler(UserError)
    def _user_error(_: Request, exc: UserError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    app.include_router(router)
