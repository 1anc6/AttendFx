# AttendFX

An MCP server (plus a small admin web page) that lets an AI assistant answer campus course and attendance questions, seeing only what the caller is allowed to see. Privacy is enforced in the database with row-level security.

- Design: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Source guide: `Campus_MCP_Guide_Free_and_Paid.pdf`

## Local setup (Windows, PowerShell)

Requirements: Docker Desktop, [uv](https://docs.astral.sh/uv/), Python 3.12, Node 24 (frontend, later).

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
```

Seeded accounts use `@attendfx.test` emails (`admin@`, `teacher1@`..`teacher5@`, `student01@`..`student40@`) and the password in `AFX_SEED_PASSWORD`. All data is fake.

Run `psql` without installing it locally:

```powershell
docker compose exec db psql -U afx_owner -d attendfx
```

## Layout

```
backend/    FastAPI app, MCP server (later), migrations, tests
frontend/   React admin page (phase 5)
evals/      the 60-question test
infra/      deployment files
docs/       architecture and decisions
```

## Status

Done:
- Phase 0: schema, roles, RLS, seed data, permission tests, CI.
- Thin slice: access keys, authenticated `/mcp` endpoint, audit log.
- Phases 1 to 3: all six read-only tools: `search_courses`, `course_details`, `my_attendance`, `attendance_rule`, `course_attendance_summary`, `low_attendance_list`.

Next: the two MCP resources (course list guide, term calendar), then rate limiting (phase 4) and the admin UI (phase 5).
