"""The "room left" arithmetic behind the student attendance page."""

import pytest

from app.services.student import room_left


def test_above_the_rule_counts_the_absences_still_possible():
    # 9 of 10 so far, 10 to come, rule 75%: end total 20 needs 15 attended; 9 + 10 - k >= 15.
    assert room_left(9, 10, 10, 75) == {"kind": "spare", "sessions": 4}


def test_on_or_above_the_rule_with_nothing_left_is_final():
    """Not "no sessions to spare": the term's sessions are over and the student made it."""
    assert room_left(3, 4, 0, 75) == {"kind": "final"}
    assert room_left(15, 16, 0, 75) == {"kind": "final"}


def test_exactly_on_the_rule_is_on_it_not_a_rounding_error_below():
    # 2 of 3 is 66.666...%; a rule of 66.6 must not tip it under.
    assert room_left(2, 3, 0, 66.6) == {"kind": "final"}
    assert room_left(2, 3, 1, 66.6)["kind"] == "spare"


def test_exactly_on_the_rule_with_one_session_left_has_none_to_spare():
    assert room_left(3, 4, 1, 75) == {"kind": "spare", "sessions": 0}


def test_below_the_rule_needs_a_run_of_sessions():
    # 5 of 10, rule 75%: (5 + n) / (10 + n) >= 0.75 first holds at n = 10.
    assert room_left(5, 10, 12, 75) == {"kind": "need", "sessions": 10}


def test_below_the_rule_with_too_few_sessions_left_cannot_reach_it():
    assert room_left(5, 10, 9, 75) == {"kind": "cannot_reach"}


def test_nothing_marked_yet_counts_spare_from_the_sessions_to_come():
    # 0 of 0, 8 to come, rule 75%: must attend 6 of 8, so 2 to spare.
    assert room_left(0, 0, 8, 75) == {"kind": "spare", "sessions": 2}


def test_no_sessions_at_all():
    assert room_left(0, 0, 0, 75) == {"kind": "no_sessions"}


def test_a_full_attendance_rule():
    assert room_left(4, 4, 3, 100) == {"kind": "spare", "sessions": 0}
    assert room_left(3, 4, 3, 100) == {"kind": "cannot_reach"}


@pytest.mark.parametrize("attended,counted,remaining", [(7, 12, 30), (0, 5, 40), (11, 20, 25)])
def test_need_is_the_smallest_run_that_works(attended, counted, remaining):
    result = room_left(attended, counted, remaining, 75)
    assert result["kind"] == "need"
    n = result["sessions"]
    assert (attended + n) / (counted + n) >= 0.75
    assert (attended + n - 1) / (counted + n - 1) < 0.75
    assert n <= remaining
