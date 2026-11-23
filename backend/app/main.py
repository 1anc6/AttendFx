"""FastAPI entry point. Serves /mcp (access-key auth) and /healthz. /api and the UI come later."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.pools import close_pools
from app.mcp.server import build_mcp_app

mcp_asgi, mcp_inner = build_mcp_app()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # A mounted sub-app's own lifespan is not run by the parent, so run the MCP one here.
    async with mcp_inner.router.lifespan_context(mcp_inner):
        yield
    close_pools()


app = FastAPI(title="AttendFX", docs_url=None, redoc_url=None, lifespan=lifespan)

# Forward /mcp with the original scope (no Mount) so POST /mcp never redirects to /mcp/.
app.add_route("/mcp", mcp_asgi)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
