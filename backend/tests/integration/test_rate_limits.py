"""Rate limits on /mcp: per person (all their keys together) and per IP for failed key checks."""

from app.main import mcp_asgi
from app.ratelimit.limiter import TokenBucketLimiter
from tests.integration.mcp_helpers import STUDENT, TEACHER, call


def test_person_over_the_limit_gets_429_with_retry_after(client, make_key):
    mcp_asgi.user_limiter = TokenBucketLimiter(per_minute=6, burst=3)
    key = make_key(STUDENT)
    codes = [call(client, key, "attendance_rule").status_code for _ in range(3)]
    assert codes == [200, 200, 200]
    limited = call(client, key, "attendance_rule")
    assert limited.status_code == 429
    assert limited.headers["Retry-After"] == "10"
    assert limited.json() == {"error": "rate_limited", "retry_after_seconds": 10}


def test_limit_is_per_person_not_per_key(client, make_key):
    mcp_asgi.user_limiter = TokenBucketLimiter(per_minute=6, burst=2)
    first, second = make_key(STUDENT), make_key(STUDENT)
    assert call(client, first, "attendance_rule").status_code == 200
    assert call(client, second, "attendance_rule").status_code == 200
    assert call(client, second, "attendance_rule").status_code == 429  # a new key does not help


def test_one_person_being_limited_does_not_affect_another(client, make_key):
    mcp_asgi.user_limiter = TokenBucketLimiter(per_minute=6, burst=1)
    student, teacher = make_key(STUDENT), make_key(TEACHER)
    assert call(client, student, "attendance_rule").status_code == 200
    assert call(client, student, "attendance_rule").status_code == 429
    assert call(client, teacher, "attendance_rule").status_code == 200


def test_rate_limited_calls_do_not_reach_the_tool_or_the_audit_log(client, make_key, owner):
    mcp_asgi.user_limiter = TokenBucketLimiter(per_minute=6, burst=1)
    key = make_key(STUDENT)
    call(client, key, "attendance_rule")
    for _ in range(5):
        assert call(client, key, "attendance_rule").status_code == 429
    audited = owner.execute(
        "SELECT count(*) FROM audit_log a JOIN api_keys k ON k.id = a.key_id WHERE k.prefix = %s",
        (key.split("_")[1],),
    ).fetchone()[0]
    assert audited == 1  # a flood cannot turn into a flood of database writes


def test_repeated_bad_keys_from_one_ip_are_throttled(client, make_key):
    mcp_asgi.failure_limiter = TokenBucketLimiter(per_minute=6, burst=3)
    for _ in range(3):
        assert call(client, "afx_00000000_wrong", "attendance_rule").status_code == 401
    assert call(client, "afx_00000000_wrong", "attendance_rule").status_code == 429
    # While the IP is throttled no key is even checked, so a valid one waits too. That is why
    # the production limit is generous: a whole campus can share one IP.
    assert call(client, make_key(STUDENT), "attendance_rule").status_code == 429


def test_successful_calls_do_not_count_as_failures(client, make_key):
    mcp_asgi.failure_limiter = TokenBucketLimiter(per_minute=6, burst=2)
    key = make_key(STUDENT)
    for _ in range(10):
        assert call(client, key, "attendance_rule").status_code == 200
