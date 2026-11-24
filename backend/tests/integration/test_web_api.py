"""Web sign-in, lockout, sessions, CSRF and the keys API (/api)."""

import pytest
from fastapi.testclient import TestClient

from app.api import routes as api_routes
from app.main import app
from app.ratelimit.limiter import TokenBucketLimiter
from app.worker.seed import uid
from tests.integration.mcp_helpers import call

# Users no other test touches.
WEB = "student32@attendfx.test"
LOCK = "student33@attendfx.test"
OTHER = "student34@attendfx.test"
USERS = [uid("user", n) for n in ("student32", "student33", "student34")]


@pytest.fixture(autouse=True)
def clean(owner):
    def wipe():
        owner.execute(
            "DELETE FROM audit_log WHERE user_id = ANY(%s) "
            "OR key_id IN (SELECT id FROM api_keys WHERE user_id = ANY(%s))",
            (USERS, USERS),
        )
        owner.execute("DELETE FROM api_keys WHERE user_id = ANY(%s)", (USERS,))
        owner.execute("DELETE FROM web_sessions WHERE user_id = ANY(%s)", (USERS,))
        owner.execute(
            "UPDATE users SET failed_logins = 0, locked_until = NULL WHERE id = ANY(%s)", (USERS,)
        )
        owner.commit()

    wipe()
    yield
    wipe()


def new_browser() -> TestClient:
    """A fresh cookie jar over HTTPS (the session cookie is Secure). Not used as a context
    manager: that would re-run the app lifespan, and the MCP session manager starts only once
    per process (the shared `client` fixture owns it)."""
    return TestClient(app, base_url="https://testserver")


@pytest.fixture
def browser(require_db):
    return new_browser()


def sign_in(client, email, password):
    return client.post("/api/auth/sign-in", json={"email": email, "password": password})


def signed_in(client, settings, email=WEB):
    r = sign_in(client, email, settings.seed_password)
    assert r.status_code == 200, r.text
    return r.json()["csrf_token"]


def test_sign_in_sets_a_locked_down_session_cookie(browser, settings):
    r = sign_in(browser, WEB, settings.seed_password)
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == WEB and body["user"]["role"] == "student"
    assert "password_hash" not in r.text

    cookie = r.headers["set-cookie"]
    assert cookie.startswith("__Host-afx_session=")
    for flag in ("HttpOnly", "Secure", "Path=/", "SameSite=lax"):
        assert flag.lower() in cookie.lower()
    assert "domain" not in cookie.lower()

    me = browser.get("/api/me")
    assert me.status_code == 200 and me.json()["user"]["email"] == WEB


def test_session_is_stored_only_as_a_hash(browser, settings, owner):
    signed_in(browser, settings)
    token = browser.cookies.get("__Host-afx_session")
    stored = owner.execute("SELECT id FROM web_sessions WHERE user_id = %s", (USERS[0],)).fetchall()
    assert len(stored) == 1 and stored[0][0] != token and len(stored[0][0]) == 64


def test_wrong_password_and_unknown_email_look_the_same(browser):
    wrong = sign_in(browser, WEB, "not-the-password")
    unknown = sign_in(browser, "nobody@attendfx.test", "not-the-password")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "Email or password is wrong."}
    assert "set-cookie" not in wrong.headers


def test_account_locks_after_five_wrong_passwords(browser, settings, owner):
    for _ in range(settings.login_max_failures - 1):
        assert sign_in(browser, LOCK, "wrong").status_code == 401
    fifth = sign_in(browser, LOCK, "wrong")
    assert fifth.status_code == 423 and "Try again in 15 minutes" in fifth.json()["detail"]

    # Locked: even the right password is refused, and not checked.
    assert sign_in(browser, LOCK, settings.seed_password).status_code == 423

    # When the lock runs out, the right password works and the counter starts again.
    owner.execute(
        "UPDATE users SET locked_until = now() - interval '1 second' WHERE id = %s", (USERS[1],)
    )
    owner.commit()
    assert sign_in(browser, LOCK, settings.seed_password).status_code == 200
    row = owner.execute(
        "SELECT failed_logins, locked_until FROM users WHERE id = %s", (USERS[1],)
    ).fetchone()
    assert row == (0, None)


def test_a_success_resets_the_failure_count(browser, settings, owner):
    for _ in range(settings.login_max_failures - 1):
        sign_in(browser, LOCK, "wrong")
    assert sign_in(browser, LOCK, settings.seed_password).status_code == 200
    assert sign_in(browser, LOCK, "wrong").status_code == 401  # not locked: count restarted


def test_failed_sign_ins_are_throttled_per_ip(browser, settings):
    api_routes.limits.login_failures = TokenBucketLimiter(1, 2)
    assert sign_in(browser, "nobody@attendfx.test", "x").status_code == 401
    assert sign_in(browser, "nobody@attendfx.test", "x").status_code == 401
    blocked = sign_in(browser, WEB, settings.seed_password)
    assert blocked.status_code == 429 and int(blocked.headers["retry-after"]) > 0


def test_api_needs_a_session(browser):
    assert browser.get("/api/me").status_code == 401
    assert browser.get("/api/keys").status_code == 401
    browser.cookies.set("__Host-afx_session", "made-up-token", domain="testserver")
    assert browser.get("/api/me").status_code == 401


def test_expired_sessions_stop_working(browser, settings, owner):
    signed_in(browser, settings)
    owner.execute(
        "UPDATE web_sessions SET expires_at = now() - interval '1 second' WHERE user_id = %s",
        (USERS[0],),
    )
    owner.commit()
    assert browser.get("/api/me").status_code == 401


def test_changes_need_the_csrf_token(browser, settings):
    csrf = signed_in(browser, settings)
    assert browser.post("/api/keys", json={"name": "laptop"}).status_code == 403
    bad = browser.post("/api/keys", json={"name": "laptop"}, headers={"X-CSRF-Token": "nope"})
    assert bad.status_code == 403
    ok = browser.post("/api/keys", json={"name": "laptop"}, headers={"X-CSRF-Token": csrf})
    assert ok.status_code == 201


def test_sign_in_rejects_non_json_bodies(browser, settings):
    # A cross-site HTML form can only send form or text bodies, never JSON.
    r = browser.post(
        "/api/auth/sign-in",
        content=f'{{"email":"{WEB}","password":"{settings.seed_password}"}}',
        headers={"content-type": "text/plain"},
    )
    assert r.status_code == 422


def test_key_lifecycle_through_the_api(browser, client, settings):
    csrf = signed_in(browser, settings)
    h = {"X-CSRF-Token": csrf}

    created = browser.post("/api/keys", json={"name": "laptop", "days": 30}, headers=h)
    assert created.status_code == 201
    full_key = created.json()["key"]
    assert call(client, full_key, "attendance_rule").status_code == 200

    listed = browser.get("/api/keys").json()
    assert listed["active"] == 1 and listed["max_active"] == 10
    assert [k["name"] for k in listed["keys"]] == ["laptop"]
    assert full_key not in str(listed)

    key_id = created.json()["id"]
    revoked = browser.post(f"/api/keys/{key_id}/revoke", headers=h)
    assert revoked.status_code == 200 and revoked.json()["status"] == "revoked"
    assert call(client, full_key, "attendance_rule").status_code == 401
    assert browser.get("/api/keys").json()["active"] == 0


def test_bad_key_requests_get_clear_errors(browser, settings):
    h = {"X-CSRF-Token": signed_in(browser, settings)}
    too_long = browser.post("/api/keys", json={"name": "x", "days": 400}, headers=h)
    assert too_long.status_code == 400 and "1 to 365 days" in too_long.json()["detail"]
    bad_name = browser.post("/api/keys", json={"name": "<script>"}, headers=h)
    assert bad_name.status_code == 400


def test_you_cannot_revoke_someone_elses_key(require_db, settings):
    other = new_browser()
    other_csrf = signed_in(other, settings, OTHER)
    theirs = other.post(
        "/api/keys", json={"name": "theirs"}, headers={"X-CSRF-Token": other_csrf}
    ).json()["id"]
    me = new_browser()
    csrf = signed_in(me, settings)
    r = me.post(f"/api/keys/{theirs}/revoke", headers={"X-CSRF-Token": csrf})
    assert r.status_code == 404 and r.json() == {"detail": "No such key."}


def test_sign_out_ends_the_session(browser, settings, owner):
    csrf = signed_in(browser, settings)
    token = browser.cookies.get("__Host-afx_session")
    r = browser.post("/api/auth/sign-out", headers={"X-CSRF-Token": csrf})
    assert r.status_code == 204
    assert owner.execute(
        "SELECT count(*) FROM web_sessions WHERE user_id = %s", (USERS[0],)
    ).fetchone() == (0,)
    browser.cookies.set("__Host-afx_session", token, domain="testserver")
    assert browser.get("/api/me").status_code == 401  # replaying the old cookie fails


def test_api_is_rate_limited_per_person(browser, settings):
    signed_in(browser, settings)
    api_routes.limits.per_user = TokenBucketLimiter(1, 2)
    assert browser.get("/api/me").status_code == 200
    assert browser.get("/api/me").status_code == 200
    assert browser.get("/api/me").status_code == 429


def test_sign_ins_are_audited_without_secrets(browser, settings, owner):
    sign_in(browser, WEB, "wrong")
    signed_in(browser, settings)
    rows = owner.execute(
        "SELECT action, status, surface FROM audit_log WHERE user_id = %s ORDER BY id",
        (USERS[0],),
    ).fetchall()
    assert rows == [("web.sign_in", "invalid", "api"), ("web.sign_in", "ok", "api")]


def test_responses_carry_security_headers(browser):
    r = browser.get("/healthz")
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff"
    assert browser.get("/api/me").headers["cache-control"] == "no-store"
