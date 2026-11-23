"""End to end: HTTP -> access key -> RLS identity -> my_attendance, over the real MCP endpoint."""

from datetime import timedelta

import pytest

from tests.integration.mcp_helpers import (
    ADMIN,
    OTHER_STUDENT,
    STUDENT,
    TEACHER,
    call,
    tool_result,
)

# ---------------------------------------------------------------- authentication


def test_missing_and_bad_keys_are_rejected(client, make_key):
    assert call(client, None, "my_attendance").status_code == 401
    assert call(client, "afx_deadbeef_notarealsecret", "my_attendance").status_code == 401
    assert call(client, "garbage", "my_attendance").status_code == 401
    good = make_key(STUDENT)
    tampered = good[:-3] + ("aaa" if not good.endswith("aaa") else "bbb")
    assert call(client, tampered, "my_attendance").status_code == 401


def test_expired_key_is_rejected(client, make_key):
    key = make_key(STUDENT, expires_in=timedelta(seconds=-5))
    assert call(client, key, "my_attendance").status_code == 401


def test_revoked_key_stops_working_immediately(client, make_key, owner):
    key = make_key(STUDENT)
    assert call(client, key, "my_attendance").status_code == 200
    prefix = key.split("_")[1]
    owner.execute("UPDATE api_keys SET revoked_at = now() WHERE prefix = %s", (prefix,))
    owner.commit()
    assert call(client, key, "my_attendance").status_code == 401


# ---------------------------------------------------------------- the privacy rule


def test_student_gets_own_summary_matching_the_database(client, make_key, truth):
    key = make_key(STUDENT)
    is_error, data, _ = tool_result(call(client, key, "my_attendance"))
    assert not is_error and data["found"] is True
    assert data["student_id"] == str(STUDENT)

    expected = dict(
        truth.execute(
            "SELECT status, count(*) FROM attendance_records WHERE student_id = %s GROUP BY 1",
            (STUDENT,),
        ).fetchall()
    )
    for status in ("present", "absent", "late", "excused"):
        assert data["overall"][status] == expected.get(status, 0)
    assert data["overall"]["total_sessions"] == sum(expected.values())
    assert len(data["courses"]) == 4  # seed enrols each student in four courses


def test_student_filter_by_course(client, make_key):
    key = make_key(STUDENT)
    _, all_data, _ = tool_result(call(client, key, "my_attendance"))
    code = all_data["courses"][0]["course_code"]
    _, data, _ = tool_result(call(client, key, "my_attendance", {"course_code": code}))
    assert [c["course_code"] for c in data["courses"]] == [code]


def test_student_asking_for_someone_else_gets_the_generic_answer(client, make_key):
    key = make_key(STUDENT)
    other = tool_result(call(client, key, "my_attendance", {"student_id": str(OTHER_STUDENT)}))
    missing = tool_result(
        call(client, key, "my_attendance", {"student_id": "00000000-0000-0000-0000-000000000000"})
    )
    assert other == missing  # identical: no way to tell "forbidden" from "does not exist"
    assert other[1]["found"] is False


def test_teacher_sees_own_students_only(client, make_key, truth):
    key = make_key(TEACHER)
    mine = truth.execute(
        """SELECT DISTINCT e.student_id FROM enrolments e
           JOIN courses c ON c.id = e.course_id WHERE c.teacher_id = %s""",
        (TEACHER,),
    ).fetchall()
    all_students = truth.execute("SELECT id FROM users WHERE role = 'student'").fetchall()
    mine_ids = {r[0] for r in mine}
    outside = [r[0] for r in all_students if r[0] not in mine_ids]
    assert mine_ids and outside, "seed data should give both groups"

    _, inside_data, _ = tool_result(
        call(client, key, "my_attendance", {"student_id": str(next(iter(mine_ids)))})
    )
    assert inside_data["found"] is True
    teacher_courses = {
        r[0] for r in truth.execute("SELECT code FROM courses WHERE teacher_id = %s", (TEACHER,))
    }
    # A teacher only ever sees their own courses, even for a student who takes other courses.
    assert {c["course_code"] for c in inside_data["courses"]} <= teacher_courses

    _, outside_data, _ = tool_result(
        call(client, key, "my_attendance", {"student_id": str(outside[0])})
    )
    assert outside_data["found"] is False


def test_teacher_and_admin_must_name_a_student(client, make_key):
    for user in (TEACHER, ADMIN):
        is_error, _, text = tool_result(call(client, make_key(user), "my_attendance"))
        assert is_error and "student_id is required" in text


def test_admin_can_read_any_student(client, make_key):
    key = make_key(ADMIN)
    _, data, _ = tool_result(call(client, key, "my_attendance", {"student_id": str(STUDENT)}))
    assert data["found"] is True and len(data["courses"]) == 4


# ---------------------------------------------------------------- validation and audit


@pytest.mark.parametrize(
    "arguments",
    [
        {"course_code": "cse301"},
        {"course_code": "'; DROP TABLE users;--"},
        {"from_date": "2019-01-01", "to_date": "2026-01-01"},
        {"from_date": "2026-09-01", "to_date": "2026-08-01"},
        {"student_id": "not-a-uuid"},
    ],
)
def test_invalid_input_is_rejected_with_a_safe_message(client, make_key, arguments):
    is_error, _, text = tool_result(call(client, make_key(STUDENT), "my_attendance", arguments))
    assert is_error
    assert "Traceback" not in text and "SELECT" not in text


def test_date_range_narrows_results(client, make_key):
    key = make_key(STUDENT)
    _, full, _ = tool_result(call(client, key, "my_attendance"))
    _, narrow, _ = tool_result(
        call(client, key, "my_attendance", {"from_date": "2026-08-03", "to_date": "2026-08-30"})
    )
    assert narrow["found"] is True
    assert narrow["overall"]["total_sessions"] < full["overall"]["total_sessions"]


def test_calls_are_audited_without_raw_arguments(client, make_key, owner):
    key = make_key(STUDENT)
    key_prefix = key.split("_")[1]
    call(client, key, "my_attendance", {"student_id": str(OTHER_STUDENT)})
    rows = owner.execute(
        """SELECT a.user_id, a.surface, a.action, a.status, a.args_hash, a.latency_ms
           FROM audit_log a JOIN api_keys k ON k.id = a.key_id WHERE k.prefix = %s""",
        (key_prefix,),
    ).fetchall()
    assert len(rows) == 1
    user_id, surface, action, status, args_hash, latency = rows[0]
    assert (user_id, surface, action, status) == (STUDENT, "mcp", "my_attendance", "no_records")
    assert len(args_hash) == 64 and str(OTHER_STUDENT) not in args_hash
    assert latency >= 0
