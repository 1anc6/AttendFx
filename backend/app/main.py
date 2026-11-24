"""FastAPI entry point.

- /mcp: MCP server, access-key auth.
- /api: JSON API for the web app, session-cookie auth.
- /healthz: liveness.
- everything else: the built React app, when frontend/dist exists.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import routes as api_routes
from app.db.pools import close_pools
from app.mcp.server import build_mcp_app
from app.web_ui import SecurityHeaders, mount_spa

mcp_asgi, mcp_inner = build_mcp_app()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # A mounted sub-app's own lifespan is not run by the parent, so run the MCP one here.
    async with mcp_inner.router.lifespan_context(mcp_inner):
        yield
    close_pools()


app = FastAPI(title="AttendFX", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.add_middleware(SecurityHeaders)

# Forward /mcp with the original scope (no Mount) so POST /mcp never redirects to /mcp/.
app.add_route("/mcp", mcp_asgi)
api_routes.install(app)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


# Last, so its catch-all route never shadows /mcp, /api or /healthz.
mount_spa(app)
