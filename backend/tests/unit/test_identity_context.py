import anyio
import pytest
from mcp.server.mcpserver.exceptions import ResourceError, ToolError

from app.mcp import server


def test_handler_without_verified_identity_fails_closed():
    called = []

    def service(identity):
        called.append(identity)
        return {}

    with pytest.raises(ToolError, match="Not authorised"):
        anyio.run(server._invoke, "test", service)
    assert called == []  # the service never ran


def test_resource_without_verified_identity_fails_closed():
    async def read():
        await server._invoke("test", lambda identity: "", error_cls=ResourceError)

    with pytest.raises(ResourceError, match="Not authorised"):
        anyio.run(read)
