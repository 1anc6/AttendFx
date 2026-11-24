# AttendFX

An MCP server (plus a small admin web page) that lets an AI assistant answer campus course and attendance questions, seeing only what the caller is allowed to see. Privacy is enforced in the database with row-level security.

- Design: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Source guide: `Campus_MCP_Guide_Free_and_Paid.pdf`

## Local setup (Windows, PowerShell)

Requirements: Docker Desktop, [uv](https://docs.astral.sh/uv/), Python 3.12, Node 24.

```powershell
Copy-Item .env.example .env          # dev-only values
docker compose up -d                 # Postgres 17
cd backend
uv sync
uv run alembic upgrade head          # tables, roles, RLS
uv run python -m app.worker seed     # fake data (Faker), idempotent
uv run pytest                        # unit + permission tests
uv run uvicorn app.main:app --reload # http://localhost:8000/healthz
```

Mint an access key for a seeded user and talk to the MCP endpoint:

```powershell
uv run python -m app.worker create-key --email student01@attendfx.test --days 7
# then connect an MCP client to http://localhost:8000/mcp with header  Authorization: Bearer <key>
uv run python -m app.worker list-keys --email student01@attendfx.test
uv run python -m app.worker revoke-key --prefix <8-char prefix>
```

Each person gets a burst of 20 requests, then 60 a minute (`AFX_RATE_LIMIT_BURST`, `AFX_RATE_LIMIT_PER_MINUTE`).

Seeded accounts use `@attendfx.test` emails (`admin@`, `teacher1@`..`teacher5@`, `student01@`..`student40@`) and the password in `AFX_SEED_PASSWORD`. All data is fake.

### Web app

```powershell
cd frontend
npm ci
npm run dev       # http://localhost:5173, proxies /api and /mcp to uvicorn on :8000
npm run build     # frontend/dist, which uvicorn then serves at http://localhost:8000
```

Sign in with any seeded account. Five wrong passwords lock an account for 15 minutes. Admins add people under Admin → People; each new account gets a temporary password that must be replaced at first sign-in.

### Database shell

Run `psql` without installing it locally:

```powershell
docker compose exec db psql -U afx_owner -d attendfx
```

## Layout

```
backend/    FastAPI app, MCP server, web API, migrations, tests
frontend/   React web app (Vite, Tailwind, shadcn/ui)
evals/      the 60-question test
infra/      deployment files
docs/       architecture and decisions
```

## Status

Done:
- Phase 0: schema, roles, RLS, seed data, permission tests, CI.
- Thin slice: access keys, authenticated `/mcp` endpoint, audit log.
- Phases 1 to 3: all six read-only tools (`search_courses`, `course_details`, `my_attendance`, `attendance_rule`, `course_attendance_summary`, `low_attendance_list`) and both resources (`attendfx://guides/course-list`, `attendfx://calendar/current-term`).
- Phase 4: per-person rate limits, failed-key throttling per IP, key lifecycle rules (expiry, 10-key cap, owner/admin revocation), operator CLI, audit for key actions.
- Phase 5 (web app): web sign-in with lockout, cookie sessions with CSRF, `/api` for keys and people, security headers, the app shell, Your access keys, Connect assistant, Account (change password), People (add one, CSV import, temporary passwords, reset, unlock, turn off), and the admin dashboards: Overview (term attendance, fortnight trend, enrolment funnel, students below the minimum), Activity (the audit log, searchable and filterable, no arguments or answers shown) and Usage (calls per day, by tool with median and p95 latency, most active people, over 7, 30 or 90 days). Every chart has a table view.
- Deployed on Render with a Neon database (`infra/Dockerfile`).

Phase 6 (ship):
- Done: the 60-question test (`evals/`): 60 of 60 pass, run in CI. See [evals/results.md](evals/results.md).
- Done: security scans in CI: gitleaks (secrets), pip-audit and npm audit (dependencies), and Trivy on the production image and its Dockerfile.
- Done: demo write-up, see [docs/DEMO.md](docs/DEMO.md).

Phase 7 (student page):
- Done: Your attendance (`/me`), where students land after signing in. Per-course attendance against the rule, sessions to spare or the run needed to recover, recent marks, a fortnight trend, and every session of a course in a side sheet. Served by `GET /api/me/attendance` and `GET /api/me/attendance/{course}`, which take no student id and read through row-level security as the student. Plan and decisions: [docs/STUDENT_DASHBOARD.md](docs/STUDENT_DASHBOARD.md).
- Done: UI polish across the app: press feedback and stronger easing on buttons and overlays, reduced-motion support, themed selection and scrollbars, a scale and rule line on the attendance charts, and per-page tab titles. The sign-in page checks fields in place, keeps focus on the password after a failed attempt, has a show-password button and a Caps Lock warning, and keeps browser autofill in the app's colours.
