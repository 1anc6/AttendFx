"""The student's own attendance page: /api/me/attendance and /api/me/attendance/{course}."""

import pytest

from app.services import student
from app.services.common import STATUSES, attended_percent
from app.worker.seed import TERM, uid
from tests.integration.test_web_api import new_browser, signed_in

STUDENT_EMAIL = "student38@attendfx.test"
OTHER_EMAIL = "student39@attendfx.test"
TEACHER_EMAIL = "teacher4@attendfx.test"
ADMIN_EMAIL = "admin@attendfx.test"
STUDENT = uid("user", "student38")
OTHER = uid("user", "student39")
PAGE = "/api/me/attendance"


@pytest.fixture(autouse=True)
def clean(owner):
    def wipe():
        people = [STUDENT, OTHER, uid("user", "teacher4"), uid("user", "admin")]
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


def enrolled_codes(truth, student_id):
    return {
        code
        for (code,) in truth.execute(
            """
            SELECT c.code FROM enrolments e JOIN courses c ON c.id = e.course_id
            WHERE e.student_id = %s AND c.term = %s
            """,
            (student_id, TERM),
        ).fetchall()
    }


# ---- Who may look -------------------------------------------------------------------------


def test_signed_out_visitors_get_401(require_db):
    assert new_browser().get(PAGE).status_code == 401
    assert new_browser().get(f"{PAGE}/CSE301").status_code == 401


@pytest.mark.parametrize("email", [TEACHER_EMAIL, ADMIN_EMAIL])
def test_teachers_and_admins_get_403(settings, email):
    b = browser_for(settings, email)
    for path in (PAGE, f"{PAGE}/CSE301"):
        r = b.get(path)
        assert r.status_code == 403
        assert r.json()["detail"] == "Only students have an attendance page."


def test_the_service_refuses_non_students_even_without_the_route(require_db):
    from app.db.pools import Identity
    from app.services.common import Denied

    with pytest.raises(Denied):
        student.my_page(Identity(uid("user", "teacher4"), "teacher"))
    with pytest.raises(Denied):
        student.my_course(Identity(uid("user", "admin"), "admin"), "CSE301")


# ---- Only your own data -------------------------------------------------------------------


def test_the_page_matches_the_database_for_the_signed_in_student(settings, truth):
    body = browser_for(settings, STUDENT_EMAIL).get(PAGE).json()
    assert body["term"]["name"] == TERM
    assert {c["course_code"] for c in body["courses"]} == enrolled_codes(truth, STUDENT)

    counts = dict.fromkeys(STATUSES, 0)
    for status, n in truth.execute(
        """
        SELECT a.status, count(*) FROM attendance_records a
        JOIN class_sessions s ON s.id = a.class_session_id
        JOIN courses c ON c.id = s.course_id
        WHERE a.student_id = %s AND c.term = %s GROUP BY a.status
        """,
        (STUDENT, TERM),
    ).fetchall():
        counts[status] = n
    assert {s: body["overall"][s] for s in STATUSES} == counts
    assert body["overall"]["attended_percent"] == attended_percent(counts)
    assert sum(f["records"] for f in body["fortnights"]) <= sum(counts.values())
    assert len(body["recent"]) <= student.RECENT


def test_a_student_id_in_the_query_is_ignored(settings):
    """There is no way to ask for someone else: extra parameters change nothing."""
    b = browser_for(settings, STUDENT_EMAIL)
    plain = b.get(PAGE).json()
    probing = b.get(PAGE, params={"student_id": str(OTHER)}).json()
    assert probing == plain


def test_each_student_gets_their_own_counts(settings, truth):
    for email, student_id in ((STUDENT_EMAIL, STUDENT), (OTHER_EMAIL, OTHER)):
        body = browser_for(settings, email).get(PAGE).json()
        (records,) = truth.execute(
            "SELECT count(*) FROM attendance_records a JOIN class_sessions s "
            "ON s.id = a.class_session_id JOIN courses c ON c.id = s.course_id "
            "WHERE a.student_id = %s AND c.term = %s",
            (student_id, TERM),
        ).fetchone()
        assert sum(body["overall"][s] for s in STATUSES) == records


def test_sessions_to_come_never_include_a_marked_session(settings, truth):
    """Every scheduled session is either marked or still to come, never both."""
    body = browser_for(settings, STUDENT_EMAIL).get(PAGE).json()
    for c in body["courses"]:
        (scheduled,) = truth.execute(
            "SELECT count(*) FROM class_sessions s JOIN courses co ON co.id = s.course_id "
            "WHERE co.code = %s AND co.term = %s",
            (c["course_code"], TERM),
        ).fetchone()
        marked = sum(c[s] for s in STATUSES)
        assert marked + c["remaining_sessions"] <= scheduled


def test_course_sessions_for_an_enrolled_course(settings, truth):
    code = sorted(enrolled_codes(truth, STUDENT))[0]
    body = browser_for(settings, STUDENT_EMAIL).get(f"{PAGE}/{code}").json()
    assert body["course_code"] == code
    sessions = body["sessions"]
    total = truth.execute(
        "SELECT count(*) FROM class_sessions s JOIN courses c ON c.id = s.course_id "
        "WHERE c.code = %s AND c.term = %s",
        (code, TERM),
    ).fetchone()[0]
    assert len(sessions) == total
    allowed = set(STATUSES) | {"upcoming", "unmarked"}
    assert {s["status"] for s in sessions} <= allowed


def test_a_course_you_are_not_in_gets_404(settings, truth):
    mine = enrolled_codes(truth, STUDENT)
    (other,) = truth.execute(
        "SELECT code FROM courses WHERE term = %s AND NOT (code = ANY(%s)) LIMIT 1",
        (TERM, list(mine)),
    ).fetchone()
    r = browser_for(settings, STUDENT_EMAIL).get(f"{PAGE}/{other}")
    assert r.status_code == 404
    assert r.json()["detail"] == "You are not enrolled in that course this term."


def test_a_malformed_course_code_gets_400(settings):
    r = browser_for(settings, STUDENT_EMAIL).get(f"{PAGE}/cse31")
    assert r.status_code == 400
