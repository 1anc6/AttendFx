# AttendFX demo

AttendFX is an MCP server with a small admin web app. It lets an AI assistant answer campus course and attendance questions, and it only returns what the signed-in person is allowed to see. The privacy rules are enforced in the database (row-level security), not in the assistant or the API code. All data is fake.

Live: https://attendfx.onrender.com (free Render tier: the first request after a quiet period can be slow while the service wakes up).

## What to show

1. **Sign in as admin.** Open the live site and sign in with the admin account. Overview shows term attendance, the fortnight trend, the enrolment funnel and students below the minimum. Activity shows the audit log: who called which tool, when, and how fast, with no arguments or answers recorded. Usage shows calls per day, calls by tool with median and p95 latency, and the most active people.
2. **Mint an access key.** Under Your access keys, create a key. Under Connect assistant, copy the MCP endpoint and the key. The key is shown once.
3. **Ask the assistant.** Connect an MCP client to `https://attendfx.onrender.com/mcp` with the header `Authorization: Bearer <key>`. Good questions to try:
   - "What courses are running this term?" (`search_courses`)
   - "How many classes did I miss in CSE301?" (`my_attendance`, as a student)
   - "Who is below the minimum attendance?" (`low_attendance_list`, as a teacher or admin)
4. **Show the privacy rule.** Ask as one student for another student's attendance. The answer is refused, and the database would refuse it too even if the API code had a bug. The permission tests and the 60-question test cover this.

## What it can do today

**Tools for the assistant (all read-only):** `search_courses`, `course_details`, `my_attendance`, `attendance_rule`, `course_attendance_summary`, `low_attendance_list`.

**Resources:** the course-list guide (`attendfx://guides/course-list`) and the current term calendar (`attendfx://calendar/current-term`).

**Roles:**
- Students see only their own attendance.
- Teachers see the courses they teach. They may pass a `student_id` to `my_attendance` only for students in their own courses.
- Admins see everything but cannot change attendance records through the assistant.

**Admin web app:** sign-in with lockout after five wrong passwords (15-minute pause), cookie sessions with CSRF protection, Your access keys, Connect assistant, Account (change password), People (add one, CSV import, temporary passwords, reset, unlock, turn off), and the Overview, Activity and Usage dashboards. Every chart has a table view.

**Access keys and limits:** each person gets a burst of 20 requests, then 60 per minute. Keys expire, each person can hold up to 10 keys, and owners or admins can revoke them.

## How it was tested

- **The 60-question test** (`evals/`). Each question is asked as a real seeded person through `/mcp` with that person's own key, and the answer is checked against the database. Result: **60 of 60 passed** (catalogue 11, calendar 3, policy 3, student 10, teacher 10, admin 5, privacy 13, bad input 5). It runs in CI. Full table: [evals/results.md](../evals/results.md). What it does and does not cover: [evals/README.md](../evals/README.md).
- **Unit, integration and permission tests** (`backend/tests`), run with pytest.
- **Security scans in CI:** gitleaks (secrets), pip-audit and npm audit (dependencies), and Trivy on the production image and Dockerfile.

## Run it locally (Windows, PowerShell)

```powershell
Copy-Item .env.example .env
docker compose up -d
cd backend
uv sync
uv run alembic upgrade head
uv run python -m app.worker seed
uv run pytest
uv run uvicorn app.main:app --reload    # http://localhost:8000
```

See the README for the web app setup and the access key commands.

## Limits to say out loud

- **The data is fake.** Faker generates the seed data. Real student data would need stronger backups and monitoring first.
- **Not built yet:** student and teacher web pages. The source guide describes the web app as admin-only, and students and teachers use the assistant instead.
- **Open decisions:** the official minimum attendance percentage (stored as a setting; the guide does not state it), the source for the term calendar (seeded for v1), and whether real student data will ever be used.
- **Demo trade-off:** on Render, `FORWARDED_ALLOW_IPS=*` means the per-IP throttle for failed keys can be spoofed. Acceptable for a demo; fix it before real use.
