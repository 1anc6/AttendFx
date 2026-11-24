# Plan: student dashboard

Status: built (phase 7). Steps 7a to 7d are done; section 8 records the decisions taken. Where the build differs from the original plan, this file has been updated to match.

## 1. Why, and what it changes

Today the web app is for admins, and students only reach their data through an AI assistant. The source guide (`Campus_MCP_Guide_Free_and_Paid.pdf`) describes the web page as admin-only, so a student dashboard is a **scope change**, not a missing piece. It is still a reasonable one: a student who has not set up an assistant has no way to check their own attendance, and a page answers the most common question ("am I safe in each course?") faster than typing it.

The privacy model does not change. The dashboard reads through the same row-level security as the `my_attendance` tool, so a student can only ever see their own rows.

## 2. What a student needs to know

In order of importance:

1. **Am I safe in each course?** Attendance per course against the rule, with a clear status.
2. **How much room is left?** For each course, how many of the remaining sessions this term could be missed before falling below the rule, or how many must be attended in a row to get back above it.
3. **What happened recently?** The last few marked sessions, so a wrong mark is easy to spot.
4. **How is it trending?** Attendance by fortnight, the same view admins get, for this one student.

## 3. Screen design

Mode: Operate. The page follows the existing look (variant E: monochrome layers, Geist, colour only for status, light and dark). It reuses `PageHeader`, `StatCard`, `Meter`, `BarChart` (with the new guide lines) and the table-on-desktop, cards-on-phone pattern.

```
Your attendance                                   [2026-Autumn · 3 Aug to 27 Nov]
Across your 4 courses this term. The rule is 75% in each course.

[ Overall 86.5% ]  [ Below 75%: 1 course ]  [ Needs most attention: CSE301, 1 session to spare ]

Your courses
  Course              Teacher           Status     Attendance                    Room left
  CSE301 Databases    Dr. A. Maharaj    Watch      78.6%  ███████▌|──  11 of 14   1 more absence
  MAT210 Probability  Dr. V. Tiwari     At risk    56.2%  █████  |───   9 of 16   attend the next 6
  ...                                               (the | marks the 75% rule)

Recent sessions                       Attendance by fortnight
  Mon 23 Nov  CSE301  Present           bars with 50% / 75% / 100% guide lines
  Fri 20 Nov  MAT210  Absent
  ...
```

- The course list is the main part of the page, not the stat tiles. The three tiles are a short summary above it.
- Each meter shows a tick at the rule, so "how far above or below" reads without numbers.
- "Room left" wording is still an open question (see section 8).
- Selecting a course opens a sheet with every session in that course, its date and status. A sheet keeps the student on the page and works on phones.
- Empty and edge states: no term running; enrolled but no sessions marked yet; rule not configured (hide the rule tick and "room left", show percentages only); loading skeleton; load error with retry.

## 4. Navigation

- Students sign in to **Your attendance** (`/me`) instead of `/keys`. The "You" group in the sidebar becomes: Your attendance, Connect assistant, Your access keys, Account.
- Teachers and admins do not see this item; teachers keep `/keys` as the landing page until a teacher view exists.

## 5. API

One new read-only endpoint, for a signed-in student with a ready session:

`GET /api/me/attendance` returns:

- `term`: name, start, end.
- `minimum_percent` and `rule_set`: the rule. If the college has not set one, the same 75% default the admin Overview uses is returned with `rule_set: false`, and the page says it is only a guide.
- `courses[]`: code, title, teacher name, counts by status, `attended_percent`, `status` (ok, watch, at risk, no marks yet; same 10-point margin as the admin Overview), `remaining_sessions` (scheduled sessions after now that have no mark yet, so a session marked ahead of time is never counted twice), and `room` (see section 6).
- `recent[]`: the last 10 marked sessions: date and time, course code, status.
- `fortnights[]`: start date and attended percent, the same shape as the admin overview.
- `how_percent_is_calculated`: the existing rule text.

Rules:

- The endpoint takes **no student id**. It always uses the session's own user, through `rls_connection`, so row-level security is the final check, as it is for `my_attendance`.
- Teachers and admins get 403. They already have `my_attendance` with a `student_id` through the assistant.
- It reuses `attendance_repo.status_counts` and `fortnight_counts`. It adds two small queries: recent records for the student, and future `class_sessions` per enrolled course. `courses` and `class_sessions` are already readable by the app role.

## 6. The "room left" calculation

For one course: `attended` = present + late, `counted` = all marked sessions minus excused, `remaining` = scheduled sessions after now, `m` = minimum as a fraction.

- **Absences still possible** = the largest `k` with `(attended + remaining − k) / (counted + remaining) ≥ m`, floored at 0.
- If even attending every remaining session ends below the rule, report that instead ("cannot reach 75% this term").
- If no sessions are left and the student is at or above the rule, report "no sessions left this term" rather than "no sessions to spare", which would read as a warning.
- If currently below the rule, **sessions needed in a row** = the smallest `n ≤ remaining` with `(attended + n) / (counted + n) ≥ m`.
- This assumes no future excused sessions, and the page says so in one line.

This is pure arithmetic, so it gets plain unit tests with edge cases (no sessions yet, no remaining sessions, exactly on the rule, rule not set).

## 7. Build order and checks

| Step | Deliverable | Done when |
|---|---|---|
| 7a | `GET /api/me/attendance`, repo queries, the room-left function | Unit tests for the calculation; permission tests: student sees only self, teacher/admin get 403, no id parameter exists |
| 7b | `/me` page: summary, course list, recent sessions, trend | Typecheck, lint and build pass; checked in light and dark, desktop and phone, with a seeded student |
| 7c | Course sheet with every session | Keyboard and screen reader names checked; the sheet closes with Escape |
| 7d | Students land on `/me`; sidebar updated | Sign-in as a student goes to `/me`; teachers and admins unchanged |
| 7e | README and ARCHITECTURE updated; demo doc mentions the page | Docs match what shipped |

A teacher view ("my courses": each course's attendance, students below the rule) is a natural follow-up using the same pieces, but it is not part of this plan.

## 8. Decisions

1. **Scope.** Approved: the web app now has a student page as well as the admin pages.
2. **"Room left" wording.** Neutral: "3 sessions to spare", "Attend the next 4", "Can't reach 75% this term", "No sessions left this term". Never "you can miss".
3. **Audit.** Not audited, like the admin dashboards. Assistant calls stay audited as before.
4. **Teacher view.** Not built. Still a natural follow-up using the same pieces.

Not yet done: step 7e for the demo write-up, which lives on a separate branch (`docs/demo-writeup`); add the student page there once both are merged.
