import asyncio
import sys
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from jeff.bell import status, summary


def test_bell_status_and_summary():
    bell = status()
    assert bell["implemented"] is True
    assert bell["default_transport"] == "stdio"
    assert bell["network_transport"] == "streamable-http"
    assert {"jeff_run", "jeff_audit", "jeff_ask", "jeff_status"} <= set(bell["tools"])
    assert {"jeff_k_history", "jeff_flaw_count", "jeff_coherence", "jeff_session"} <= set(bell["tools"])
    assert "jeff_umph_scan" in set(bell["tools"])
    assert "jeff serve --transport http" in summary()


def test_bell_stdio_round_trip(tmp_path):
    async def round_trip():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "jeff.cli", "serve"],
            cwd=Path(__file__).resolve().parents[1],
        )
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
                result = await session.call_tool("jeff_status", {"cwd": str(tmp_path)})
                return tools, result

    tools, result = asyncio.run(round_trip())
    names = {tool.name for tool in tools.tools}

    assert {"jeff_run", "jeff_audit", "jeff_ask", "jeff_status"} <= names
    assert result.isError is False
    assert result.structuredContent is not None
    assert result.structuredContent["tool"] == "jeff_status"
    assert result.structuredContent["cwd"] == str(tmp_path)
