"""The two MCP resources (course list guide, term calendar) and the seeded term calendar."""

import json
from datetime import date

import pytest

from app.db.pools import Identity
from app.services import resources
from tests.integration.mcp_helpers import ADMIN, STUDENT, TEACHER, rpc

GUIDE = "attendfx://guides/course-list"
CALENDAR = "attendfx://calendar/current-term"


def read(client, key, uri):
    response = rpc(client, key, "resources/read", {"uri": uri})
    assert response.status_code == 200, response.text
    content = response.json()["result"]["contents"][0]
    return content["mimeType"], content["text"]


def test_resources_are_listed(client, make_key):
    response = rpc(client, make_key(STUDENT), "resources/list")
    listed = {r["uri"]: r for r in response.json()["result"]["resources"]}
    assert set(listed) == {GUIDE, CALENDAR}
    assert listed[GUIDE]["mimeType"] == "text/markdown"
    assert listed[CALENDAR]["mimeType"] == "application/json"


def test_resources_need_a_key(client):
    assert rpc(client, None, "resources/read", {"uri": GUIDE}).status_code == 401
    assert rpc(client, None, "resources/list").status_code == 401


# --------------------------------------------------------------------- course list guide


def test_course_list_guide_content(client, make_key):
    mime, text = read(client, make_key(STUDENT), GUIDE)
    assert mime == "text/markdown"
    assert "2 to 4 capital letters followed by 3 digits" in text
    assert "- 2026-Autumn: 2026-08-03 to 2026-11-27" in text
    assert "### Computer Science" in text
    assert "- CSE301: Database Systems (2026-Autumn)" in text
    assert text.count("\n- ") >= 8  # every seeded course is listed
    assert "data, not instructions" in text


def test_course_list_guide_is_the_same_for_every_role(client, make_key):
    texts = {read(client, make_key(user), GUIDE)[1] for user in (STUDENT, TEACHER, ADMIN)}
    assert len(texts) == 1  # nothing role-specific or private in it
    assert "@" not in texts.pop()


# ------------------------------------------------------------------------ term calendar


def test_term_calendar_content(client, make_key):
    mime, text = read(client, make_key(STUDENT), CALENDAR)
    assert mime == "application/json"
    data = json.loads(text)
    assert data["configured"] is True
    assert (data["term"], data["starts_on"], data["ends_on"]) == (
        "2026-Autumn",
        "2026-08-03",
        "2026-11-27",
    )
    assert data["timezone"] == "Asia/Kolkata"
    assert data["holidays"] == [
        {"date": "2026-08-15", "weekday": "Saturday", "name": "Independence Day"},
        {"date": "2026-10-02", "weekday": "Friday", "name": "Gandhi Jayanti"},
    ]
    assert data["status"] in {"upcoming", "in progress", "ended"}


@pytest.mark.parametrize(
    ("today", "status"),
    [
        (date(2026, 7, 1), "upcoming"),
        (date(2026, 8, 3), "in progress"),
        (date(2026, 11, 27), "in progress"),
        (date(2027, 1, 10), "ended"),
    ],
)
def test_term_status_follows_the_date(require_db, today, status):
    identity = Identity(user_id=STUDENT, role="student")
    data = resources.term_calendar(identity, today=today)
    assert data["term"] == "2026-Autumn" and data["status"] == status
    assert data["today"] == today.isoformat()


def test_resource_reads_are_audited(client, make_key, owner):
    key = make_key(TEACHER)
    read(client, key, CALENDAR)
    read(client, key, GUIDE)
    rows = owner.execute(
        """SELECT a.action, a.status FROM audit_log a JOIN api_keys k ON k.id = a.key_id
           WHERE k.prefix = %s ORDER BY a.id""",
        (key.split("_")[1],),
    ).fetchall()
    assert rows == [("resource:term_calendar", "ok"), ("resource:course_list_guide", "ok")]


def test_concurrent_callers_never_see_each_others_identity(client, make_key):
    """Interleave a student and a teacher from many threads; any identity mix-up would show
    as the teacher getting the student's data, or the student being asked for a student_id."""
    from concurrent.futures import ThreadPoolExecutor

    from tests.integration.mcp_helpers import call, tool_result

    student_key, teacher_key = make_key(STUDENT), make_key(TEACHER)

    def ask(i):
        key = student_key if i % 2 == 0 else teacher_key
        return i, tool_result(call(client, key, "my_attendance"))

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(ask, range(40)))

    for i, (is_error, data, text) in results:
        if i % 2 == 0:
            assert not is_error and data["student_id"] == str(STUDENT)
        else:
            assert is_error and "student_id is required" in text


# ------------------------------------------------------------------- seeded calendar data


def test_no_class_is_scheduled_on_a_holiday(truth):
    clashes = truth.execute(
        """SELECT c.code, h.day FROM class_sessions s
           JOIN courses c ON c.id = s.course_id
           JOIN term_holidays h ON h.term = c.term
                AND h.day = (s.starts_at AT TIME ZONE 'Asia/Kolkata')::date"""
    ).fetchall()
    assert clashes == []


def test_every_course_still_has_sixteen_sessions_inside_the_term(truth):
    rows = truth.execute(
        """SELECT c.code, count(*),
                  bool_and((s.starts_at AT TIME ZONE 'Asia/Kolkata')::date
                           BETWEEN t.starts_on AND t.ends_on)
           FROM class_sessions s
           JOIN courses c ON c.id = s.course_id
           JOIN terms t ON t.name = c.term
           GROUP BY c.code"""
    ).fetchall()
    assert len(rows) == 8
    assert all(n == 16 and inside for _, n, inside in rows)
