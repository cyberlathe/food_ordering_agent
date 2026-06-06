"""
mcp_client.py
-------------
Client adapter for calling a remote MCP server over its URL.
"""

import json

import anyio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from config import MCP_SERVER_URL


def _mcp_result_to_json(result) -> str:
    """Convert an MCP tool result into a JSON string for the reasoning loop."""
    if hasattr(result, "model_dump"):
        result = result.model_dump()

    if isinstance(result, dict):
        if result.get("structuredContent") is not None:
            return json.dumps(result["structuredContent"])

        content = result.get("content")
    else:
        content = getattr(result, "content", None)

    if not isinstance(content, list):
        if isinstance(result, dict):
            return json.dumps(result)
        return json.dumps({"result": result})

    values = []
    text_chunks = []
    for block in content:
        if isinstance(block, dict):
            if "data" in block:
                values.append(block["data"])
                continue

            if "text" in block:
                text = str(block["text"])
                try:
                    values.append(json.loads(text))
                except json.JSONDecodeError:
                    text_chunks.append(text)
                continue

        text_chunks.append(str(block))

    if len(values) == 1 and not text_chunks:
        return json.dumps(values[0])

    if values or text_chunks:
        return json.dumps({
            "content": values,
            "text": "\n".join(text_chunks).strip(),
        })

    return json.dumps(result)


async def _call_tool_via_mcp(name: str, input_data: dict) -> str:
    """Call a tool on the MCP server reachable at MCP_SERVER_URL."""
    async with streamablehttp_client(MCP_SERVER_URL) as (read_stream, write_stream, _session):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(name, input_data)
            return _mcp_result_to_json(result)


def execute_tool(name: str, input_data: dict) -> tuple[str, bool]:
    """Execute a food order agent tool via the local MCP server."""
    result = anyio.run(_call_tool_via_mcp, name, input_data)
    return result
