# The 60-question test

Sixty questions a student, teacher or admin might ask their assistant. Each one goes through
the real `/mcp` endpoint, authenticated with that person's own access key. The answer is
checked against the database.

```powershell
cd backend
uv run python ../evals/run.py
```

You need the database migrated and seeded, as for the tests. The run takes about a second. It
writes [results.md](results.md) (the results sheet) and `results.json`, then removes the
temporary keys and their audit rows. It exits 1 if any question fails, and CI runs it after
the test suite.

## What the questions cover

| Area | Questions | What a pass means |
|---|---|---|
| Catalogue | 11 | Searches, credits, weekly timetable, first and last class are right. A bad or lower-case code gets a helpful correction. |
| Calendar | 3 | Term dates, holidays and the course list guide are right. |
| Policy | 3 | The minimum, how late and excused count, and the formula. |
| Student | 10 | Their own attendance per course and overall, with date ranges, matches every count and percent. |
| Teacher | 10 | Class summaries, below-minimum lists (any threshold, any range) and a student's record in their own courses are exact. Missing or out-of-range input is refused. |
| Admin | 5 | The same across every course and student. |
| Privacy | 13 | Students can't see other people or use staff tools. Teachers see nothing outside their courses. A hidden record looks exactly like a missing one. No key or a fake key gets 401. The injection text in HSS110 comes back as plain data, with no student data. |
| Bad input | 5 | SQL-looking text, wildcards, oversized input and over-long ranges are handled safely. |

## How answers are checked

[truth.py](truth.py) loads the raw rows as the database owner and does its own counting in
Python, including its own copy of the percent formula. A bug in the app's SQL or formula shows
up as a mismatch instead of being repeated on both sides. Enrolments in the seed are random,
so cases pick concrete people and courses from the data at run time ("a course student 5 takes",
"a student teacher 1 does not teach").

To check the test can fail, the app was broken on purpose, once by counting late as absent and
once by deleting the service check that stops a student asking for another student. The
first change failed 20 questions. The second failed none, because row-level security in the
database still hid the other student's records. That is the second layer doing its job.

## What it does not cover

This tests the server: that each tool gives the right answer, and only to the right person,
for the call a correct assistant would make. It does not test whether a language model picks
that call, reads the numbers back correctly, or resists the injected course text in its reply.
That needs a model in the loop and an API key. The questions are written so they can be reused
for that later.
