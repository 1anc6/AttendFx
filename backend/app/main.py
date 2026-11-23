"""FastAPI entry point. The MCP endpoint (/mcp) and the admin API (/api) are mounted here later."""

from fastapi import FastAPI

app = FastAPI(title="AttendFX", docs_url=None, redoc_url=None)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
