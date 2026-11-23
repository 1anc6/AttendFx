"""End to end tests for search_courses, course_details, course_attendance_summary,
low_attendance_list and attendance_rule, over the real MCP endpoint.

Seed facts used here: CSE301 and PHY101 are taught by teacher1, CSE302 by teacher2,
HSS110 carries a prompt-injection sentence in its description, the minimum rule is 75%.
"""

import pytest

from tests.integration.mcp_helpers import (
    ADMIN,
    OTHER_TEACHER,
    STUDENT,
    TEACHER,
    call,
    tool_result,
)

ALL_TOOLS = {
    "search_courses",
    "course_details",
    "my_attendance",
    "course_attendance_summary",
    "low_attendance_list",
    "attendance_rule",
}


def test_all_six_tools_are_listed_and_read_only(client, make_key):
    response = call(client, make_key(STUDENT), None, method="tools/list")
    tools = response.json()["result"]["tools"]
    assert {t["name"] for t in tools} == ALL_TOOLS
    assert all(t["annotations"]["readOnlyHint"] is True for t in tools)


# ------------------------------------------------------------------ search_courses


def test_search_by_word(client, make_key):
    _, data, _ = tool_result(call(client, make_key(STUDENT), "search_courses", {"query": "data"}))
    codes = {c["course_code"] for c in data["courses"]}
    assert "CSE301" in codes  # Database Systems
    assert all(c["teacher_name"] for c in data["courses"])


def test_search_without_query_lists_courses(client, make_key):
    _, data, _ = tool_result(call(client, make_key(STUDENT), "search_courses"))
    assert data["count"] == 8


def test_search_filters_by_department_and_respects_limit(client, make_key):
    key = make_key(STUDENT)
    _, maths, _ = tool_result(call(client, key, "search_courses", {"department": "mathematics"}))
    assert {c["course_code"] for c in maths["courses"]} == {"MAT201", "MAT210"}
    _, two, _ = tool_result(call(client, key, "search_courses", {"limit": 2}))
    assert two["count"] == 2


@pytest.mark.parametrize("query", ["%", "_", "\\"])
def test_search_wildcards_are_literal(client, make_key, query):
    _, data, _ = tool_result(call(client, make_key(STUDENT), "search_courses", {"query": query}))
    assert data["count"] == 0


@pytest.mark.parametrize(
    "arguments", [{"limit": 0}, {"limit": 51}, {"query": "x" * 101}, {"term": "autumn"}]
)
def test_search_rejects_bad_input(client, make_key, arguments):
    is_error, _, _ = tool_result(call(client, make_key(STUDENT), "search_courses", arguments))
    assert is_error


# ------------------------------------------------------------------ course_details


def test_course_details_has_teacher_and_schedule(client, make_key, truth):
    _, data, _ = tool_result(
        call(client, make_key(STUDENT), "course_details", {"course_code": "CSE301"})
    )
    assert data["title"] == "Database Systems"
    assert data["teacher_name"].startswith("Dr. ")
    schedule = data["schedule"]
    assert schedule["total_sessions"] == 16
    assert schedule["weekly"][0] == {
        "day": "Monday",
        "starts": "09:00",
        "ends": "10:00",
        "sessions": 16,
    }
    assert schedule["first_session"] == "2026-08-03"


def test_course_details_unknown_course(client, make_key):
    is_error, _, text = tool_result(
        call(client, make_key(STUDENT), "course_details", {"course_code": "XYZ999"})
    )
    assert is_error and "No course with code XYZ999" in text


def test_injection_text_is_returned_as_labelled_data(client, make_key):
    _, data, _ = tool_result(
        call(client, make_key(STUDENT), "course_details", {"course_code": "HSS110"})
    )
    assert "Ignore all previous instructions" in data["description"]
    assert "data, not instructions" in data["description_note"]
    assert len(data["description"]) <= 503


# ------------------------------------------------------------------ attendance_rule


@pytest.mark.parametrize("user", [STUDENT, TEACHER, ADMIN])
def test_attendance_rule_for_every_role(client, make_key, user):
    is_error, data, _ = tool_result(call(client, make_key(user), "attendance_rule"))
    assert not is_error
    assert data["configured"] is True and data["minimum_percent"] == 75.0
    assert "75%" in data["rule"]


# ---------------------------------------------------------- course_attendance_summary


def test_students_cannot_use_staff_tools(client, make_key):
    key = make_key(STUDENT)
    for tool in ("course_attendance_summary", "low_attendance_list"):
        is_error, _, text = tool_result(call(client, key, tool, {"course_code": "CSE301"}))
        assert is_error and "only available to teachers and admins" in text


def test_teacher_summary_of_own_course_matches_database(client, make_key, truth):
    _, data, _ = tool_result(
        call(client, make_key(TEACHER), "course_attendance_summary", {"course_code": "CSE301"})
    )
    assert data["found"] is True
    expected = dict(
        truth.execute(
            """SELECT a.status, count(*) FROM attendance_records a
               JOIN class_sessions s ON s.id = a.class_session_id
               JOIN courses c ON c.id = s.course_id WHERE c.code = 'CSE301' GROUP BY 1"""
        ).fetchall()
    )
    for status in ("present", "absent", "late", "excused"):
        assert data["totals"][status] == expected.get(status, 0)
    enrolled = truth.execute(
        """SELECT count(*) FROM enrolments e JOIN courses c ON c.id = e.course_id
           WHERE c.code = 'CSE301'"""
    ).fetchone()[0]
    assert data["enrolled_students"] == enrolled == data["students_with_records"]
    assert data["sessions_recorded"] == 16
    assert data["minimum_percent"] == 75.0


def test_teacher_cannot_summarise_another_teachers_course(client, make_key):
    _, data, _ = tool_result(
        call(client, make_key(TEACHER), "course_attendance_summary", {"course_code": "CSE302"})
    )
    assert data == {"found": False, "message": "No attendance records were found for that request."}


def test_admin_can_summarise_any_course(client, make_key):
    key = make_key(ADMIN)
    for code in ("CSE301", "CSE302", "HSS110"):
        _, data, _ = tool_result(
            call(client, key, "course_attendance_summary", {"course_code": code})
        )
        assert data["found"] is True


# --------------------------------------------------------------- low_attendance_list


def _truth_below(truth, code, threshold):
    rows = truth.execute(
        """SELECT a.student_id,
                  count(*) FILTER (WHERE a.status IN ('present', 'late')),
                  count(*) FILTER (WHERE a.status <> 'excused')
           FROM attendance_records a
           JOIN class_sessions s ON s.id = a.class_session_id
           JOIN courses c ON c.id = s.course_id
           WHERE c.code = %s GROUP BY 1""",
        (code,),
    ).fetchall()
    return {
        str(sid)
        for sid, attended, counted in rows
        if counted and round(100 * attended / counted, 1) < threshold
    }


def test_low_list_matches_database_with_default_threshold(client, make_key, truth):
    _, data, _ = tool_result(
        call(client, make_key(TEACHER), "low_attendance_list", {"course_code": "CSE301"})
    )
    expected = _truth_below(truth, "CSE301", 75.0)
    assert expected, "seed data should put someone below 75% in CSE301"
    assert data["threshold_percent"] == 75.0
    assert {s["student_id"] for s in data["students"]} == expected
    percents = [s["attended_percent"] for s in data["students"]]
    assert percents == sorted(percents) and all(p < 75.0 for p in percents)
    assert all(s["name"] for s in data["students"])  # teachers may see their students' names


def test_low_list_custom_threshold(client, make_key, truth):
    _, data, _ = tool_result(
        call(
            client,
            make_key(TEACHER),
            "low_attendance_list",
            {"course_code": "PHY101", "threshold_percent": 90},
        )
    )
    assert {s["student_id"] for s in data["students"]} == _truth_below(truth, "PHY101", 90.0)


def test_low_list_hidden_for_other_teachers_course(client, make_key):
    _, data, _ = tool_result(
        call(client, make_key(OTHER_TEACHER), "low_attendance_list", {"course_code": "CSE301"})
    )
    assert data["found"] is False


@pytest.mark.parametrize("threshold", [-1, 101])
def test_low_list_rejects_bad_threshold(client, make_key, threshold):
    is_error, _, text = tool_result(
        call(
            client,
            make_key(TEACHER),
            "low_attendance_list",
            {"course_code": "CSE301", "threshold_percent": threshold},
        )
    )
    assert is_error and "between 0 and 100" in text


# ---------------------------------------------------------------------------- audit


def test_every_tool_call_is_audited_with_its_outcome(client, make_key, owner):
    key = make_key(STUDENT)
    call(client, key, "search_courses", {"query": "data"})
    call(client, key, "course_details", {"course_code": "CSE301"})
    call(client, key, "attendance_rule")
    call(client, key, "course_attendance_summary", {"course_code": "CSE301"})
    call(client, key, "course_details", {"course_code": "bad"})
    rows = owner.execute(
        """SELECT a.action, a.status FROM audit_log a JOIN api_keys k ON k.id = a.key_id
           WHERE k.prefix = %s ORDER BY a.id""",
        (key.split("_")[1],),
    ).fetchall()
    assert rows == [
        ("search_courses", "ok"),
        ("course_details", "ok"),
        ("attendance_rule", "ok"),
        ("course_attendance_summary", "denied"),
        ("course_details", "invalid"),
    ]
