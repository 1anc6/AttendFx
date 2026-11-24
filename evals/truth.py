"""Ground truth for the evals, read straight from the database as the owner role.

Deliberately independent of the app: it loads raw rows once and does its own counting in
Python, so a bug in the app's SQL or in its percent formula shows up as a mismatch instead of
being repeated on both sides.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

import psycopg

IST = ZoneInfo("Asia/Kolkata")
STATUSES = ("present", "absent", "late", "excused")


@dataclass(frozen=True)
class Course:
    id: UUID
    code: str
    title: str
    department: str
    credits: int
    term: str
    description: str
    teacher_id: UUID | None
    teacher_name: str | None


@dataclass(frozen=True)
class Record:
    student_id: UUID
    code: str
    day: date  # India-time calendar day of the session
    status: str


def percent(counts: dict[str, int]) -> float | None:
    """(present + late) / (all - excused) * 100, one decimal. Written again on purpose."""
    counted = sum(counts.values()) - counts["excused"]
    if counted == 0:
        return None
    return round(100 * (counts["present"] + counts["late"]) / counted, 1)


class Truth:
    def __init__(self, conn: psycopg.Connection) -> None:
        self.users = {
            row[0]: {"id": row[0], "name": row[1], "email": row[2], "role": row[3]}
            for row in conn.execute("SELECT id, name, email, role FROM users")
        }
        self.courses: dict[str, Course] = {}
        for row in conn.execute(
            """
            SELECT c.id, c.code, c.title, c.department, c.credits, c.term,
                   coalesce(c.description, ''), c.teacher_id, u.name
            FROM courses c LEFT JOIN users u ON u.id = c.teacher_id
            """
        ):
            self.courses[row[1]] = Course(*row)
        self.sessions: dict[str, list[datetime]] = defaultdict(list)
        for code, starts_at in conn.execute(
            "SELECT c.code, s.starts_at FROM class_sessions s JOIN courses c ON c.id = s.course_id"
        ):
            self.sessions[code].append(starts_at)
        for starts in self.sessions.values():
            starts.sort()
        self.records = [
            Record(student_id, code, starts_at.astimezone(IST).date(), status)
            for student_id, code, starts_at, status in conn.execute(
                """
                SELECT a.student_id, c.code, s.starts_at, a.status
                FROM attendance_records a
                JOIN class_sessions s ON s.id = a.class_session_id
                JOIN courses c ON c.id = s.course_id
                """
            )
        ]
        self.enrolled: dict[UUID, set[str]] = defaultdict(set)
        for student_id, code in conn.execute(
            "SELECT e.student_id, c.code FROM enrolments e JOIN courses c ON c.id = e.course_id"
        ):
            self.enrolled[student_id].add(code)
        row = conn.execute(
            "SELECT value FROM settings WHERE key = 'attendance_min_percent'"
        ).fetchone()
        self.minimum = float(row[0]) if row else None
        self.term = conn.execute(
            "SELECT name, starts_on, ends_on FROM terms ORDER BY starts_on DESC LIMIT 1"
        ).fetchone()
        self.holidays = {
            day: name for day, name in conn.execute("SELECT day, name FROM term_holidays")
        }

    # ---- people and courses ---------------------------------------------------------------

    def name(self, user_id: UUID) -> str:
        return self.users[user_id]["name"]

    def taught_by(self, teacher_id: UUID) -> set[str]:
        return {c.code for c in self.courses.values() if c.teacher_id == teacher_id}

    def students_of(self, code: str) -> set[UUID]:
        return {s for s, codes in self.enrolled.items() if code in codes}

    # ---- counting ---------------------------------------------------------------------------

    def _select(self, *, student=None, codes=None, start=None, end=None):
        for r in self.records:
            if student is not None and r.student_id != student:
                continue
            if codes is not None and r.code not in codes:
                continue
            if start is not None and r.day < start:
                continue
            if end is not None and r.day > end:
                continue
            yield r

    def counts(self, student, codes=None, start=None, end=None) -> dict[str, int]:
        c = Counter(
            r.status for r in self._select(student=student, codes=codes, start=start, end=end)
        )
        return {s: c.get(s, 0) for s in STATUSES}

    def by_course(self, student, codes=None, start=None, end=None) -> dict[str, dict[str, int]]:
        out: dict[str, Counter] = defaultdict(Counter)
        for r in self._select(student=student, codes=codes, start=start, end=end):
            out[r.code][r.status] += 1
        return {code: {s: c.get(s, 0) for s in STATUSES} for code, c in out.items()}

    def course_students(self, code, start=None, end=None) -> dict[UUID, dict[str, int]]:
        out: dict[UUID, Counter] = defaultdict(Counter)
        for r in self._select(codes={code}, start=start, end=end):
            out[r.student_id][r.status] += 1
        return {sid: {s: c.get(s, 0) for s in STATUSES} for sid, c in out.items()}

    def below(self, code, threshold, start=None, end=None) -> list[tuple[float, str, UUID]]:
        """(percent, name, id) for students under `threshold`, lowest first, as the tool sorts."""
        rows = []
        for sid, counts in self.course_students(code, start, end).items():
            p = percent(counts)
            if p is not None and p < threshold:
                rows.append((p, self.name(sid), sid))
        return sorted(rows)
