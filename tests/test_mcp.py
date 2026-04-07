import json
import sys

from click.testing import CliRunner

import jeff.nerve as nerve
from jeff.cli import main


def test_dispatch_keeps_local_tools_working(tmp_path):
    target = tmp_path / "note.txt"
    written = nerve.dispatch("write", path=str(target), content="hello")
    read_back = nerve.dispatch("read", path=str(target))
    assert written.success is True
    assert read_back.success is True
    assert read_back.output == "hello"


def test_mcp_list_shows_local_tools(monkeypatch):
    monkeypatch.setattr(nerve, "MCP_SERVERS_PATH", nerve.Path("__missing__.json"))
    result = CliRunner().invoke(main, ["mcp", "list"])
    assert result.exit_code == 0
    assert "local/bash" in result.output
    assert "No external MCP servers configured" in result.output


def test_external_stdio_server_can_be_listed_and_called(tmp_path, monkeypatch):
    server = tmp_path / "demo_mcp.py"
    config = tmp_path / "mcp_servers.json"
    server.write_text(
        "\n".join(
            [
                "from mcp.server.fastmcp import FastMCP",
                "",
                "app = FastMCP('demo')",
                "",
                "@app.tool(structured_output=True)",
                "def ping(name: str) -> dict[str, str | int | bool]:",
                "    return {",
                "        'tool': 'ping',",
                "        'success': True,",
                "        'output': f'pong {name}',",
                "        'error': '',",
                "        'exit_code': 0,",
                "    }",
                "",
                "if __name__ == '__main__':",
                "    app.run()",
            ]
        ),
        encoding="utf-8",
    )
    config.write_text(
        json.dumps(
            {
                "servers": {
                    "demo": {
                        "transport": "stdio",
                        "command": sys.executable,
                        "args": [str(server)],
                    }
                }
            },
            indent=2,
        ),
        encoding="utf-8-sig",
    )
    monkeypatch.setattr(nerve, "MCP_SERVERS_PATH", config)

    inventory = nerve.list_mcp_inventory()
    external = next(item for item in inventory["external"] if item["server"] == "demo")
    result = nerve.dispatch("demo/ping", name="Jeff")

    assert external["status"] == "connected"
    assert "ping" in external["tools"]
    assert result.success is True
    assert result.output == "pong Jeff"
