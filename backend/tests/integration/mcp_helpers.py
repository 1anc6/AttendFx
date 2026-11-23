"""Small JSON-RPC helpers for calling the MCP endpoint in tests."""

from app.worker.seed import uid

HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}

STUDENT, OTHER_STUDENT = uid("user", "student1"), uid("user", "student2")
TEACHER, OTHER_TEACHER = uid("user", "teacher1"), uid("user", "teacher2")
ADMIN = uid("user", "admin")


def call(client, key, name, arguments=None, *, method="tools/call"):
    headers = dict(HEADERS)
    if key:
        headers["Authorization"] = f"Bearer {key}"
    body = {"jsonrpc": "2.0", "id": 1, "method": method}
    if method == "tools/call":
        body["params"] = {"name": name, "arguments": arguments or {}}
    return client.post("/mcp", json=body, headers=headers)


def rpc(client, key, method, params=None):
    headers = dict(HEADERS)
    if key:
        headers["Authorization"] = f"Bearer {key}"
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    return client.post("/mcp", json=body, headers=headers)


def tool_result(response):
    """(is_error, structured_content, first text block)."""
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    return result["isError"], result.get("structuredContent"), result["content"][0]["text"]
