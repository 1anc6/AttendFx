"""Admin dashboards: /api/admin/overview, /api/admin/activity and /api/admin/usage."""

import pytest

from app.services import admin
from app.services.common import STATUSES, attended_percent
from app.worker.seed import TERM, uid
from tests.integration.mcp_helpers import call
from tests.integration.test_web_api import new_browser, signed_in

ADMIN_EMAIL = "admin@attendfx.test"
STUDENT_EMAIL = "student38@attendfx.test"
TEACHER_EMAIL = "teacher4@attendfx.test"
ADMIN = uid("user", "admin")
STUDENT = uid("user", "student38")
TEACHER = uid("user", "teacher4")
ENDPOINTS = ("/api/admin/overview", "/api/admin/activity", "/api/admin/usage")


@pytest.fixture(autouse=True)
def clean(owner):
    """Remove the sessions and web audit rows these tests create (keys clean up after
    themselves through the make_key fixture)."""

    def wipe():
        people = [ADMIN, STUDENT, TEACHER]
        owner.execute(
            "DELETE FROM audit_log WHERE user_id = ANY(%s) AND action LIKE 'web.%%'", (people,)
        )
        owner.execute("DELETE FROM web_sessions WHERE user_id = ANY(%s)", (people,))
        owner.commit()

    wipe()
    yield
    wipe()


def browser_for(settings, email):
    b = new_browser()
    signed_in(b, settings, email)
    return b


# ---- Who may look -------------------------------------------------------------------------


@pytest.mark.parametrize("path", ENDPOINTS)
def test_signed_out_visitors_get_401(path, require_db):
    assert new_browser().get(path).status_code == 401


@pytest.mark.parametrize("email", [STUDENT_EMAIL, TEACHER_EMAIL])
@pytest.mark.parametrize("path", ENDPOINTS)
def test_students_and_teachers_get_403(settings, path, email):
    r = browser_for(settings, email).get(path)
    assert r.status_code == 403
    assert r.json()["detail"] == "Only admins can do this."


def test_the_service_refuses_non_admins_even_without_the_route(require_db):
    """The audit log is read as afx_auth, which sees every row: the service checks too."""
    from app.db.pools import Identity
    from app.services.common import Denied

    teacher = Identity(TEACHER, "teacher")
    for fn in (admin.overview, admin.activity, admin.usage):
        with pytest.raises(Denied):
            fn(teacher)


# ---- Overview ------------------------------------------------------------------------------


def test_overview_matches_the_database(settings, truth):
    body = browser_for(settings, ADMIN_EMAIL).get("/api/admin/overview").json()
    assert body["term"]["name"] == TERM
    att = body["attendance"]

    enrolled = truth.execute(
        "SELECT count(*) FROM enrolments e JOIN courses c ON c.id = e.course_id WHERE c.term = %s",
        (TERM,),
    ).fetchone()[0]
    assert att["funnel"]["enrolled"] == enrolled

    counts = dict.fromkeys(STATUSES, 0)
    for status, n in truth.execute(
        """
        SELECT a.status, count(*) FROM attendance_records a
        JOIN class_sessions s ON s.id = a.class_session_id
        JOIN courses c ON c.id = s.course_id WHERE c.term = %s GROUP BY a.status
        """,
        (TERM,),
    ).fetchall():
        counts[status] = n
    assert att["overall_percent"] == attended_percent(counts)
    assert sum(f["records"] for f in att["fortnights"]) <= sum(counts.values())

    funnel = att["funnel"]
    assert (
        funnel["enrolled"]
        >= funnel["attended_any"]
        >= funnel["at_or_above_minimum"]
        >= funnel["at_or_above_high"]
    )
    assert body["people"]["student"] == 40


def test_overview_lists_everyone_below_the_rule_lowest_first(settings):
    att = browser_for(settings, ADMIN_EMAIL).get("/api/admin/overview").json()["attendance"]
    below = att["below_minimum"]
    assert below, "the seed has students under the minimum"
    percents = [e["attended_percent"] for e in below]
    assert percents == sorted(percents)
    assert all(p < att["minimum_percent"] for p in percents)
    measured = att["funnel"]["enrolled"] - att["funnel"]["at_or_above_minimum"]
    assert len(below) <= measured
    assert att["students_below_minimum"] == len({e["student_id"] for e in below})
    for e in below:
        expected = "at_risk" if e["attended_percent"] < att["minimum_percent"] - 10 else "watch"
        assert e["risk"] == expected


def test_overview_counts_assistant_calls(settings, client, make_key):
    before = browser_for(settings, ADMIN_EMAIL).get("/api/admin/overview").json()["assistant"]
    key = make_key(STUDENT)
    assert call(client, key, "attendance_rule").status_code == 200
    after = browser_for(settings, ADMIN_EMAIL).get("/api/admin/overview").json()["assistant"]
    assert after["calls"] == before["calls"] + 1
    assert after["active_keys"] == before["active_keys"] + 1


# ---- Activity ------------------------------------------------------------------------------


def test_activity_shows_who_did_what_without_arguments(settings, client, make_key):
    key = make_key(STUDENT)
    call(client, key, "my_attendance", {"course_code": "CSE301"})
    b = browser_for(settings, ADMIN_EMAIL)
    body = b.get("/api/admin/activity", params={"surface": "mcp", "q": STUDENT_EMAIL}).json()
    event = body["events"][0]
    assert event["action"] == "my_attendance" and event["surface"] == "mcp"
    assert event["person"]["email"] == STUDENT_EMAIL and event["key_prefix"]
    assert event["ok"] is True
    # The log keeps ids and hashes only: no arguments or answers reach the page.
    assert "CSE301" not in str(body) and "args_hash" not in event


def test_activity_problem_filter_hides_successes(settings, client, make_key):
    key = make_key(TEACHER)
    call(client, key, "my_attendance")  # teachers must name a student: "invalid"
    b = browser_for(settings, ADMIN_EMAIL)
    body = b.get("/api/admin/activity", params={"outcome": "problems", "q": TEACHER_EMAIL}).json()
    assert body["events"], "the invalid call is listed"
    assert all(not e["ok"] for e in body["events"])
    assert body["events"][0]["status"] == "invalid"


def test_activity_newest_first_and_paged(settings):
    b = browser_for(settings, ADMIN_EMAIL)
    body = b.get("/api/admin/activity").json()
    stamps = [e["ts"] for e in body["events"]]
    assert stamps == sorted(stamps, reverse=True)
    assert body["page_size"] == 50 and len(body["events"]) <= 50
    assert b.get("/api/admin/activity", params={"surface": "email"}).status_code == 422


# ---- Usage ---------------------------------------------------------------------------------


@pytest.mark.parametrize("days", [7, 30, 90])
def test_usage_has_one_row_per_day(settings, days):
    body = browser_for(settings, ADMIN_EMAIL).get("/api/admin/usage", params={"days": days}).json()
    assert body["days"] == days and len(body["daily"]) == days
    days_listed = [d["day"] for d in body["daily"]]
    assert days_listed == sorted(days_listed)


def test_usage_counts_calls_by_tool_and_person(settings, client, make_key):
    key = make_key(STUDENT)
    for _ in range(3):
        call(client, key, "attendance_rule")
    body = browser_for(settings, ADMIN_EMAIL).get("/api/admin/usage", params={"days": 7}).json()
    tool = next(t for t in body["tools"] if t["action"] == "attendance_rule")
    assert tool["calls"] >= 3 and tool["median_ms"] is not None
    person = next(p for p in body["people"] if p["email"] == STUDENT_EMAIL)
    assert person["calls"] >= 3
    assert body["daily"][-1]["assistant"] >= 3


def test_usage_only_offers_three_windows(settings):
    b = browser_for(settings, ADMIN_EMAIL)
    r = b.get("/api/admin/usage", params={"days": 14})
    assert r.status_code == 400 and "7, 30 or 90" in r.json()["detail"]
