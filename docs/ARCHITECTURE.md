# AttendFX Architecture

Status: draft v1. Source: *Campus Course and Attendance Helper, Plain-Language Guide v2.0* (October 2026). The guide's "earlier specification" is not available, so this document is the working design.

## 1. Goals and non-goals

**Goals**
- Let an AI assistant (via MCP) answer course and attendance questions, seeing only what the caller is allowed to see.
- Give staff and users a small web page for access keys, users, the activity log and usage charts.
- Run entirely on free tiers, with a clear upgrade path (AWS) later.

**Non-goals (v1)**
- Writing or editing attendance through the helper. Every tool is read-only.
- Real university data. v1 uses Faker-generated data behind a swappable adapter.
- University SSO. Accounts are admin-created or CSV-imported in v1.

## 2. System view

```
 AI assistant (Claude Desktop, etc.)         Browser (all roles)
        |  MCP over HTTPS                           |  HTTPS
        |  Authorization: Bearer afx_...            |  session cookie
        v                                           v
 +-------------------------- FastAPI app (one container) ---------------------------+
 |  middleware: request-id -> auth -> rate-limit -> handler -> audit                |
 |                                                                                  |
 |   /mcp  (Streamable HTTP, stateless)         /api  (admin + self-service REST)   |
 |        6 tools + 2 resources                       keys, users, logs, stats      |
 |              +--------------+---------------------------+                        |
 |                      services (business rules, role checks)                      |
 |                      repositories (SQL only)                                     |
 |   /      static React build (same origin as /api)                                |
 +---------------+----------------------------------------------+-------------------+
                 | role afx_app (RLS enforced)                  | role afx_auth (narrow)
                 v                                              v
              +---------------------- Postgres (Neon) -----------------------+
              | courses, enrolments, class_sessions, attendance (RLS)        |
              | users, api_keys, web_sessions, audit_log                     |
              +--------------------------^-----------------------------------+
                                         | role afx_sync (write, scheduled)
                                 Worker CLI: nightly sync + log retention
```

## 3. Components

### 3.1 FastAPI app (single deployable)
- `/mcp`: MCP server using the official Python SDK, Streamable HTTP in **stateless** mode so a sleeping or restarted free-tier instance loses nothing.
- `/api`: REST for the admin page and self-service (keys, profile).
- `/`: the built React app, served from the same container. Same origin means no CORS and no cross-site cookie problems. It can be split onto Cloudflare Pages later by proxying `/api` through the same domain.
- Layers: transport (MCP or REST) -> services -> repositories -> database. Tools are thin: a Pydantic input model, a service call, a Pydantic output model.

### 3.2 Request pipeline
1. **Request id**: generated, attached to logs and the audit row.
2. **Auth**: `/mcp` expects a bearer access key. `/api` expects a session cookie. Failure stops here with a generic error.
3. **Rate limit**: token bucket per person (all of one user's keys share it; default burst 20, then 60 a minute), answered with 429 and `Retry-After` before any tool runs or any audit row is written. A second bucket per client IP counts failed key checks (default burst 60, then 30 a minute); while it is empty the IP gets 429 without a database lookup. That limit is generous because a whole campus may share one IP behind NAT. In-memory behind a `RateLimiter` interface, so limits are per process; use Redis when running more than one instance. Behind a proxy, run uvicorn with `--proxy-headers` so the real client IP is used.
4. **Validation**: Pydantic. Reject bad course codes, date ranges outside the term, oversized inputs.
5. **Handler**: service layer checks the role may call this tool, then runs its queries inside one RLS transaction (section 4.2).
6. **Audit**: one row per request (section 3.6), written after the response.

### 3.3 Authentication
**Access keys (MCP)**
- Format `afx_<8-char prefix>_<32-byte secret>`.
- Stored: prefix (indexed lookup) and SHA-256 of the secret. A fast hash is fine because the secret is random with 256 bits of entropy.
- Columns: `expires_at`, `revoked_at`, `last_used_at`. Plaintext is shown once, at creation.
- Revocation takes effect on the next request (no key caching beyond a few seconds, and none in v1).
- Lifecycle rules (`services/keys.py`, shared by the CLI and the future web API):
  - People create keys only for themselves. No one, not even an admin, mints a key that acts as someone else; only the operator CLI can, for bootstrapping and support.
  - Every key expires in 1 to 365 days (default 90). At most 10 usable keys per person, enforced under a row lock.
  - Owners revoke their own keys; admins can revoke anyone's. A key you may not see looks exactly like one that does not exist.
  - Create and revoke are audited (`key.create`, `key.revoke`); operator actions use surface `cli`.

**Web sign-in** (`auth/web.py`, `api/routes.py`)
- Email and password, argon2id (hashes are upgraded on sign-in if the parameters change). Unknown emails do the same argon2 work and get the same "Email or password is wrong." answer.
- 5 wrong passwords in a row lock the account for 15 minutes (`AFX_LOGIN_MAX_FAILURES`, `AFX_LOGIN_LOCK_MINUTES`). The count and lock are one atomic `UPDATE`. While locked the password is not checked. A success resets the count. Trade-off: the "locked" message reveals that an account exists, after 5 tries; the per-IP throttle below limits how far that goes.
- Failed sign-ins per client IP are throttled (burst 60, then 30 a minute, generous for campus NAT), returning 429 with Retry-After.
- Session: the cookie `__Host-afx_session` holds a random token (HttpOnly, Secure, SameSite=Lax, Path=/, no Domain). `web_sessions.id` stores only its SHA-256, so a copy of the table holds no live sessions. Sessions last 12 hours from sign-in, not sliding (`AFX_SESSION_HOURS`). Sign-out deletes the row.
- CSRF: each session has its own token, returned by `/api/me` and sign-in. Every state-changing request must send it as `X-CSRF-Token` (constant-time compare). Sign-in itself accepts only a JSON body, which a cross-site HTML form cannot send.
- `/api` is rate-limited per person with the same budget as MCP. Responses carry `Cache-Control: no-store`.
- All roles can sign in (everyone manages their own keys). Admin pages are gated by role in the API, not only in the UI.
- Audit actions: `web.sign_in` (`ok`, `invalid`, `locked`), `web.sign_out`, plus the key actions above with surface `api`.

**Web app hosting and headers** (`web_ui.py`)
- FastAPI serves `frontend/dist` on the same origin as `/api` and `/mcp`: hashed assets under `/assets`, `index.html` for client-side routes, never for `/api/*` or `/mcp`.
- Every response gets a strict CSP (`script-src 'self'`, no inline scripts, `frame-ancestors 'none'`), `nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY` and COOP. The no-flash theme script is a separate file for that reason, and fonts are self-hosted.
- The MCP endpoint rejects browser origins (DNS-rebinding protection), so a web page cannot call `/mcp` with a key, even on the same site.

### 3.4 Tools and resources
| Tool | Roles | Notes |
|---|---|---|
| `search_courses` | all | Keyword or term filter, paged, capped result size |
| `course_details` | all | Teacher, timings, credits |
| `my_attendance` | student (self), teacher (students in own courses), admin | Optional `student_id`; RLS enforces the boundary |
| `course_attendance_summary` | teacher (own courses), admin | Present, absent, late, excused counts |
| `low_attendance_list` | teacher (own courses), admin | Students below a chosen percentage |
| `attendance_rule` | all | Reads the configured minimum percentage |

Resources:
- `attendfx://guides/course-list` (Markdown): course code format, valid term names with dates, every course by department.
- `attendfx://calendar/current-term` (JSON): the current term (the one containing today, else the latest started, else the next), its status, start and end, and holidays, in Asia/Kolkata.

Both are public catalogue data, identical for every role, but still require a valid key and are audited (`resource:<name>`).

Denied or missing data returns the same short message, so the caller cannot tell "not allowed" from "does not exist". Errors never include stack traces, SQL or internal ids.

### 3.5 Background worker
- CLI: `python -m app.worker sync` and `python -m app.worker prune-audit`.
- `SourceAdapter` interface. v1 implementations: Faker generator and CSV import. A real university adapter replaces them later.
- Sync loads staging tables, then upserts into the data tables in one transaction. It is idempotent: running it twice gives the same result.
- Free path scheduling: a scheduled GitHub Actions workflow. Paid path: a scheduled ECS task.

### 3.6 Audit log
Row fields: timestamp (UTC), user id, key id, surface (`mcp` or `api`), tool or route, hash of arguments, status, latency in ms, request id. It holds no names, no raw arguments and no answers. Rows older than 90 days are pruned.

## 4. Data and the privacy rule

### 4.1 Tables
- `users(id, name, email, role, password_hash, failed_logins, locked_until, created_at)`
- `api_keys(id, user_id, name, prefix, secret_hash, expires_at, revoked_at, last_used_at, created_at)`
- `web_sessions(id, user_id, csrf_token, expires_at, created_at)`
- `courses(id, code, title, department, credits, term, teacher_id)`
- `enrolments(id, student_id, course_id)`
- `class_sessions(id, course_id, starts_at, ends_at)`
- `attendance_records(id, class_session_id, student_id, status)` with status in `present | absent | late | excused`
- `audit_log(...)` as in 3.6
- `settings(key, value)` holds the minimum attendance percentage, for example `attendance_min_percent`
- `terms(name, starts_on, ends_on)` and `term_holidays(term, day, name)`: the term calendar. Readable by `afx_app`, written by `afx_sync`, no RLS (public data)

All timestamps are `timestamptz`, stored UTC, displayed as Asia/Kolkata.

### 4.2 Database roles
| Role | Can | Cannot |
|---|---|---|
| `afx_owner` | Run migrations | Used only by CI and deploy |
| `afx_app` | `SELECT` on data tables, subject to RLS | Read `api_keys`, write anything on attendance, bypass RLS |
| `afx_auth` | Read and create/update `users` (account management); read/write `api_keys`, `web_sessions`; read/insert `audit_log` | Read attendance, courses or enrolments |
| `afx_sync` | Write data tables during the sync | Used only by the worker |

`afx_app` must not be a superuser, must not own the tables and must not have `BYPASSRLS`. Tables use `FORCE ROW LEVEL SECURITY`.

### 4.3 Per-request identity
Once the key (or session) is verified, the handler runs in one transaction:

```sql
BEGIN;
SELECT set_config('app.user_id', :uid, true),   -- true = transaction-local
       set_config('app.role',    :role, true);
-- tool queries
COMMIT;
```

Transaction-local settings are safe with Neon's pooled (transaction-mode) connections and cannot leak between requests.

### 4.4 RLS policy sketch
```sql
ALTER TABLE attendance_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance_records FORCE  ROW LEVEL SECURITY;

CREATE POLICY att_student ON attendance_records FOR SELECT TO afx_app
  USING (current_setting('app.role', true) = 'student'
         AND student_id = current_setting('app.user_id', true)::uuid);

CREATE POLICY att_teacher ON attendance_records FOR SELECT TO afx_app
  USING (current_setting('app.role', true) = 'teacher'
         AND EXISTS (SELECT 1 FROM class_sessions s
                     JOIN courses c ON c.id = s.course_id
                     WHERE s.id = class_session_id
                       AND c.teacher_id = current_setting('app.user_id', true)::uuid));

CREATE POLICY att_admin ON attendance_records FOR SELECT TO afx_app
  USING (current_setting('app.role', true) = 'admin');
```
There is no INSERT, UPDATE or DELETE grant for `afx_app`, so "admins cannot change attendance" is enforced by grants, not only by policy. `enrolments` and `class_sessions` get matching policies. `courses` is readable by all roles.

## 5. Security notes
| Risk | Control |
|---|---|
| Stolen key | Hashed at rest, expiry, instant revocation |
| Cross-student access | Application role check plus RLS; denied equals empty |
| Password guessing | argon2id, lockout, per-IP and per-account throttling |
| Flooding | Per-key and per-session rate limits |
| Prompt injection via course text | Length caps, structured output, tool descriptions mark fields as data; injection cases in the 60-question test |
| Sensitive data in logs | IDs and hashes only; no names or answers |
| Secrets in code | Env vars via pydantic-settings; gitleaks in CI |
| Dependency issues | pip-audit, npm audit, Trivy in CI |

## 6. Technology choices
- **Backend**: Python 3.12, FastAPI, official `mcp` SDK (2.x, `MCPServer`), Pydantic v2, psycopg 3 with `psycopg_pool` and plain SQL, Alembic. No heavy ORM.
- **Why psycopg and not asyncpg**: Neon's pooler runs in transaction mode, where asyncpg's prepared statements break.
- **Sync driver, threaded calls (changed from the first draft)**: database calls use synchronous psycopg and run in worker threads (`anyio.to_thread`). Async psycopg needs a non-default event loop on Windows; the sync path behaves identically on Windows, Linux and CI, and is fast enough at this scale.
- **MCP identity**: an ASGI wrapper verifies the bearer key and stores the Identity on the HTTP request scope. An MCP server middleware runs around each MCP message, copies it into a context variable for exactly that message, and resets it afterwards. Tools and resources read only that variable (never headers or arguments), and fail closed when it is empty. A concurrency test interleaves callers to prove identities never cross.
- **MCP route**: `/mcp` is served by routing to the SDK app with the original scope (no `Mount`), so `POST /mcp` never redirects.
- **Percent rule**: `attended_percent = (present + late) / (sessions - excused) * 100`. This is an assumption; the guide does not define it.
- **Frontend**: React, TypeScript, Vite, Tailwind CSS and shadcn/ui (Radix primitives), TanStack Query, React Router. The look is "variant E": monochrome layered surfaces, colour only for status, Geist type, light and dark, picked from a design exploration. Tables collapse into cards on small screens, charts come with a table view, full keyboard support.
- **Database**: Neon Postgres (plain Postgres, no second auth system). Local dev uses Postgres in Docker Compose.
- **Tests**: pytest (unit, integration, permission matrix), Vitest, Playwright later.
- **CI**: GitHub Actions: tests, gitleaks, pip-audit, npm audit, Trivy.
- **Tooling**: `uv` for Python environments and dependencies.

## 7. Deployment

| Part | Free path | Paid path (later) |
|---|---|---|
| App container | Render, Fly.io or Koyeb free plan | Paid plan, or ECS on Fargate |
| Database | Neon free | Neon paid or RDS |
| Frontend | Served by the app container | Split to Cloudflare Pages, or S3 and CloudFront |
| Scheduler | Scheduled GitHub Actions | Scheduled ECS task |
| Rate-limit store | In-memory | Redis (Upstash or ElastiCache) |
| Monitoring | Sentry and Grafana free | CloudWatch, paid alerts |

Free-tier caveat: the container sleeps when idle, so the first request after a pause can take up to a minute. Stateless MCP means nothing is lost, but some MCP clients may time out on that first call. Acceptable for a demo.

## 8. Repository layout
```
backend/app/{auth,mcp,api,services,repos,db,ratelimit,audit,worker,config}
backend/migrations/        # Alembic: tables, roles, grants, RLS policies
backend/tests/{unit,integration,permissions}
frontend/                  # Vite + React + TypeScript
evals/                     # the 60 questions and the results sheet
infra/                     # docker-compose, Dockerfile, CI workflows
docs/                      # this file, ADRs
```

## 9. Build order
| Phase | Deliverable |
|---|---|
| 0 Foundation | Repo, Docker Compose Postgres, migrations with roles, Faker seed, CI skeleton |
| 0.5 Thin slice | One key, one RLS policy, `my_attendance` working end to end |
| 1 Read tools | `search_courses`, `course_details`, checked with MCP Inspector |
| 2 Privacy core | Full RLS, permission test matrix (role by table by operation) |
| 3 Remaining tools | Teacher and admin tools, `attendance_rule`, resources |
| 4 Auth and limits | Key lifecycle, rate limiting, audit log |
| 5 Admin UI | Sign-in with lockout, keys, users, activity log, charts |
| 6 Ship | 60-question test, security scans, free-tier deploy, README and demo |

## 10. Decisions and open items
**Decided**
- Frontend served from the app container first.
- Accounts are admin-created or CSV-imported in v1; SSO later.
- Teachers may pass `student_id` to `my_attendance` for students in their own courses; RLS enforces it.
- Neon over Supabase; psycopg 3 over asyncpg.

**Open**
- The official minimum attendance percentage (the guide does not state it). Stored as a setting, so it is not blocking.
- Term and holiday data source for `term-calendar`. Seeded for v1.
- Whether any real student data is ever used. If so, stronger backups and monitoring become required (see the guide's upgrade triggers).
