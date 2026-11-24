"""Run the 60-question test against the real /mcp endpoint and write the results sheet.

    cd backend
    uv run python ../evals/run.py

Needs the database migrated and seeded (as for the tests). Each persona gets a short-lived
access key for the run; the keys and the audit rows they create are removed afterwards.
Writes evals/results.md and evals/results.json. Exits 1 if any case fails.
"""

import json
import sys
import time
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "backend")]

import psycopg  # noqa: E402
from cases import ADMIN, CASES, Case, Result, S, T, lowest_student  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from truth import Truth  # noqa: E402

from app.auth.keys import generate_key  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.main import app, mcp_asgi  # noqa: E402
from app.ratelimit.limiter import TokenBucketLimiter  # noqa: E402
from app.repos import auth_repo  # noqa: E402

HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
NO_RECORDS = "No attendance records were found for that request."
DENIED_HINTS = ("only available to teachers", "Not authorised")


def owner_url() -> str:
    return get_settings().owner_database_url.replace("postgresql+psycopg://", "postgresql://")


def persona_id(persona: str, truth: Truth):
    if persona == "admin":
        return ADMIN
    if persona == "lowest":
        return S(lowest_student(truth))
    if persona.startswith("student"):
        return S(int(persona.removeprefix("student")))
    if persona.startswith("teacher"):
        return T(int(persona.removeprefix("teacher")))
    raise ValueError(persona)


def classify(response) -> Result:
    if response.status_code != 200:
        return Result(f"http_{response.status_code}", text=response.text)
    body = response.json()
    if "error" in body:
        return Result("invalid", text=json.dumps(body["error"]))
    result = body["result"]
    if "contents" in result:  # a resource read
        text = result["contents"][0]["text"]
        try:
            return Result("ok", json.loads(text), text)
        except ValueError:
            return Result("ok", None, text)
    text = result["content"][0]["text"] if result.get("content") else ""
    if result.get("isError"):
        if any(h in text for h in DENIED_HINTS):
            return Result("denied", text=text)
        if "Something went wrong" in text:
            return Result("error", text=text)
        return Result("invalid", text=text)
    data = result.get("structuredContent")
    if isinstance(data, dict) and data.get("found") is False:
        return Result("no_records", data, text)
    return Result("ok", data, text)


def ask(client: TestClient, key: str | None, case: Case, args: dict) -> Result:
    headers = dict(HEADERS)
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if case.tool.startswith("resource:"):
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/read",
            "params": {"uri": case.tool.removeprefix("resource:")},
        }
    else:
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": case.tool, "arguments": args},
        }
    return classify(client.post("/mcp", json=body, headers=headers))


def main() -> int:
    # One run makes ~60 calls as a few people in a second or two: lift the per-person limit.
    mcp_asgi.user_limiter = TokenBucketLimiter(1_000_000, 1_000_000)
    mcp_asgi.failure_limiter = TokenBucketLimiter(1_000_000, 1_000_000)

    with psycopg.connect(owner_url()) as conn:
        truth = Truth(conn)

    keys: dict[str, str] = {"no key": "", "bad key": "afx_deadbeef_" + "0" * 43}
    key_ids = []
    rows = []
    started = time.monotonic()
    try:
        for case in CASES:
            if case.persona not in keys:
                full, prefix, secret_hash = generate_key()
                key_ids.append(
                    auth_repo.create_key(
                        persona_id(case.persona, truth),
                        "eval run",
                        prefix,
                        secret_hash,
                        datetime.now(UTC) + timedelta(hours=1),
                    )
                )
                keys[case.persona] = full

        with TestClient(app) as client:
            for case in CASES:
                args = case.args(truth) if callable(case.args) else case.args
                question = case.question(truth) if callable(case.question) else case.question
                result = ask(client, keys[case.persona] or None, case, args)
                try:
                    problem = case.check(result, truth)
                except Exception as exc:  # a malformed answer is a failure, not a crash
                    problem = f"check crashed: {type(exc).__name__}: {exc}"
                rows.append(
                    {
                        "id": case.id,
                        "area": case.area,
                        "persona": case.persona,
                        "question": question,
                        "tool": case.tool,
                        "args": args,
                        "outcome": result.kind,
                        "passed": problem is None,
                        "problem": problem,
                    }
                )
    finally:
        with psycopg.connect(owner_url()) as conn:
            conn.execute("DELETE FROM audit_log WHERE key_id = ANY(%s)", (key_ids,))
            conn.execute("DELETE FROM api_keys WHERE id = ANY(%s)", (key_ids,))

    seconds = time.monotonic() - started
    write_results(rows, seconds)
    failed = [r for r in rows if not r["passed"]]
    print(f"{len(rows) - len(failed)}/{len(rows)} passed in {seconds:.1f}s")
    for r in failed:
        print(f"  FAIL {r['id']} {r['question']}\n       {r['problem']}")
    return 1 if failed else 0


def write_results(rows: list[dict], seconds: float) -> None:
    (HERE / "results.json").write_text(
        json.dumps({"cases": rows}, indent=2, default=str) + "\n", encoding="utf-8"
    )
    passed = sum(r["passed"] for r in rows)
    areas = Counter(r["area"] for r in rows)
    area_pass = Counter(r["area"] for r in rows if r["passed"])
    lines = [
        "# AttendFX 60-question test: results",
        "",
        "Generated by `evals/run.py`. Each question is asked as a real seeded person through the",
        "`/mcp` endpoint with their own access key, and the answer is checked against the",
        "database (`evals/truth.py`). See `evals/README.md` for what is and isn't covered.",
        "",
        f"**{passed} of {len(rows)} passed** in {seconds:.1f} s.",
        "",
        "| Area | Passed |",
        "|---|---|",
    ]
    for area in areas:
        lines.append(f"| {area} | {area_pass[area]} of {areas[area]} |")
    lines += [
        "",
        "| # | Who asks | Question | Tool | Answer | Result |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        mark = "pass" if r["passed"] else f"**fail**: {r['problem']}"
        question = r["question"].replace("|", "\\|")
        lines.append(
            f"| {r['id']} | {r['persona']} | {question} | `{r['tool']}` | {r['outcome']} | {mark} |"
        )
    (HERE / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
