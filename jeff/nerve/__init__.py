"""jeff.nerve - Tool dispatch and MCP bridge. The hands that do the work."""

from __future__ import annotations

import asyncio
import json
import os
import re
import shlex
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.server.fastmcp import FastMCP

from jeff.bone import JEFF_HOME


_SHELL_META = re.compile(r"(\|\||&&|[|;<>])")
MCP_SERVERS_PATH = JEFF_HOME / "mcp_servers.json"
LOCAL_SERVER = "local"
REMOTE_SEPARATORS = ("/", ":")


@dataclass
class ToolResult:
    tool: str
    success: bool
    output: str
    error: str = ""
    exit_code: int = 0


@dataclass
class MCPServerConfig:
    name: str
    transport: str = "stdio"
    command: str | None = None
    args: list[str] = field(default_factory=list)
    cwd: str | None = None
    url: str | None = None
    env: dict[str, str] | None = None


def _argv(cmd: str | list[str] | tuple[str, ...]) -> list[str]:
    if isinstance(cmd, (list, tuple)):
        return [str(part) for part in cmd]
    if _SHELL_META.search(cmd):
        raise ValueError("Shell operators are not supported. Pass argv-style commands instead.")
    return shlex.split(cmd, posix=os.name != "nt")


def bash(cmd: str | list[str], cwd: str | None = None, timeout: int = 120) -> ToolResult:
    """Execute a command without invoking a shell."""
    try:
        r = subprocess.run(
            _argv(cmd),
            shell=False,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd(),
            timeout=timeout,
        )
        return ToolResult(
            tool="bash",
            success=r.returncode == 0,
            output=r.stdout.strip(),
            error=r.stderr.strip(),
            exit_code=r.returncode,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(tool="bash", success=False, output="", error=f"Timed out after {timeout}s")
    except Exception as e:
        return ToolResult(tool="bash", success=False, output="", error=str(e))


def read_file(path: str) -> ToolResult:
    """Read file contents."""
    try:
        text = Path(path).read_text(encoding="utf-8")
        return ToolResult(tool="read", success=True, output=text)
    except Exception as e:
        return ToolResult(tool="read", success=False, output="", error=str(e))


def write_file(path: str, content: str) -> ToolResult:
    """Write content to file, creating directories as needed."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return ToolResult(tool="write", success=True, output=f"Wrote {len(content)} bytes to {path}")
    except Exception as e:
        return ToolResult(tool="write", success=False, output="", error=str(e))


def edit_file(path: str, old: str, new: str) -> ToolResult:
    """Replace exact string in file. Must match exactly once."""
    try:
        text = Path(path).read_text(encoding="utf-8")
        count = text.count(old)
        if count == 0:
            return ToolResult(tool="edit", success=False, output="", error="String not found in file")
        if count > 1:
            return ToolResult(
                tool="edit",
                success=False,
                output="",
                error=f"String found {count} times. Must be unique.",
            )
        Path(path).write_text(text.replace(old, new, 1), encoding="utf-8")
        return ToolResult(tool="edit", success=True, output=f"Edited {path}")
    except Exception as e:
        return ToolResult(tool="edit", success=False, output="", error=str(e))


def grep(pattern: str, path: str = ".", flags: str = "-rn") -> ToolResult:
    """Search for a pattern in files without relying on grep/find binaries."""
    try:
        opts = set(flags.replace("-", ""))
        base = Path(path)
        matcher = _matcher(pattern, ignore_case="i" in opts)
        walker = [base] if base.is_file() else (
            sorted(p for p in base.rglob("*")) if "r" in opts else sorted(base.glob("*"))
        )
        matches = []
        for file in walker:
            if not file.is_file():
                continue
            try:
                lines = file.read_text(encoding="utf-8", errors="ignore").splitlines()
                for line_no, line in enumerate(lines, 1):
                    if matcher.search(line):
                        prefix = f"{file}:{line_no}" if "n" in opts else str(file)
                        matches.append(f"{prefix}:{line}")
            except OSError:
                continue
        return ToolResult(
            tool="grep",
            success=bool(matches),
            output="\n".join(matches),
            exit_code=0 if matches else 1,
        )
    except Exception as e:
        return ToolResult(tool="grep", success=False, output="", error=str(e))


def _matcher(pattern: str, ignore_case: bool = False) -> re.Pattern[str]:
    flags = re.IGNORECASE if ignore_case else 0
    try:
        return re.compile(pattern, flags)
    except re.error:
        return re.compile(re.escape(pattern), flags)


def glob_files(pattern: str, root: str = ".") -> ToolResult:
    """Find files matching glob pattern."""
    try:
        matches = sorted(str(p) for p in Path(root).rglob(pattern) if p.is_file())
        return ToolResult(tool="glob", success=True, output="\n".join(matches))
    except Exception as e:
        return ToolResult(tool="glob", success=False, output="", error=str(e))


def git(subcmd: str, cwd: str | None = None) -> ToolResult:
    """Run a git subcommand."""
    return bash(["git", *_argv(subcmd)], cwd=cwd)


def tree(path: str = ".", depth: int = 3) -> ToolResult:
    """Directory listing."""
    try:
        base = Path(path)
        files = []
        for file in sorted(base.rglob("*")):
            if not file.is_file():
                continue
            if len(file.relative_to(base).parts) > depth:
                continue
            files.append(str(file))
            if len(files) == 200:
                break
        return ToolResult(tool="tree", success=True, output="\n".join(files))
    except Exception as e:
        return ToolResult(tool="tree", success=False, output="", error=str(e))


TOOLS: dict[str, callable] = {
    "bash": bash,
    "read": read_file,
    "write": write_file,
    "edit": edit_file,
    "grep": grep,
    "glob": glob_files,
    "git": git,
    "tree": tree,
}


def _payload(result: ToolResult) -> dict[str, str | int | bool]:
    return {
        "tool": result.tool,
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "exit_code": result.exit_code,
    }


LOCAL_MCP = FastMCP("Jeff Nerve", log_level="WARNING")


@LOCAL_MCP.tool(name="bash", structured_output=True)
def bash_tool(cmd: str | list[str], cwd: str | None = None, timeout: int = 120) -> dict[str, str | int | bool]:
    return _payload(bash(cmd, cwd=cwd, timeout=timeout))


@LOCAL_MCP.tool(name="read", structured_output=True)
def read_tool(path: str) -> dict[str, str | int | bool]:
    return _payload(read_file(path))


@LOCAL_MCP.tool(name="write", structured_output=True)
def write_tool(path: str, content: str) -> dict[str, str | int | bool]:
    return _payload(write_file(path, content))


@LOCAL_MCP.tool(name="edit", structured_output=True)
def edit_tool(path: str, old: str, new: str) -> dict[str, str | int | bool]:
    return _payload(edit_file(path, old, new))


@LOCAL_MCP.tool(name="grep", structured_output=True)
def grep_tool(pattern: str, path: str = ".", flags: str = "-rn") -> dict[str, str | int | bool]:
    return _payload(grep(pattern, path=path, flags=flags))


@LOCAL_MCP.tool(name="glob", structured_output=True)
def glob_tool(pattern: str, root: str = ".") -> dict[str, str | int | bool]:
    return _payload(glob_files(pattern, root=root))


@LOCAL_MCP.tool(name="git", structured_output=True)
def git_tool(subcmd: str, cwd: str | None = None) -> dict[str, str | int | bool]:
    return _payload(git(subcmd, cwd=cwd))


@LOCAL_MCP.tool(name="tree", structured_output=True)
def tree_tool(path: str = ".", depth: int = 3) -> dict[str, str | int | bool]:
    return _payload(tree(path=path, depth=depth))


def _sync(awaitable):
    box: dict[str, Any] = {}

    def runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            box["value"] = loop.run_until_complete(awaitable)
        except Exception as exc:
            box["error"] = exc
        finally:
            loop.close()

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()
    if "error" in box:
        raise box["error"]
    return box.get("value")


def _normalize_payload(tool_name: str, payload: dict[str, Any] | None) -> ToolResult:
    payload = payload or {}
    return ToolResult(
        tool=str(payload.get("tool", tool_name)),
        success=bool(payload.get("success", False)),
        output=str(payload.get("output", "")),
        error=str(payload.get("error", "")),
        exit_code=int(payload.get("exit_code", 0)),
    )


def _normalize_remote_result(tool_name: str, result) -> ToolResult:
    payload = getattr(result, "structuredContent", None)
    if isinstance(payload, dict) and {"tool", "success", "output"} <= payload.keys():
        return _normalize_payload(tool_name, payload)
    text = "\n".join(block.text for block in result.content if hasattr(block, "text")).strip()
    success = not getattr(result, "isError", False)
    return ToolResult(
        tool=tool_name,
        success=success,
        output=text if success else "",
        error="" if success else text or f"{tool_name} failed",
        exit_code=0 if success else 1,
    )


def list_local_tools() -> list:
    return _sync(LOCAL_MCP.list_tools())


def _records(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        servers = data.get("servers", data)
        if isinstance(servers, dict):
            return [{"name": name, **cfg} for name, cfg in servers.items() if isinstance(cfg, dict)]
        if isinstance(servers, list):
            return [cfg for cfg in servers if isinstance(cfg, dict) and cfg.get("name")]
    if isinstance(data, list):
        return [cfg for cfg in data if isinstance(cfg, dict) and cfg.get("name")]
    return []


def load_server_configs(path: str | Path | None = None) -> list[MCPServerConfig]:
    config_path = Path(path) if path else MCP_SERVERS_PATH
    if not config_path.exists():
        return []
    data = json.loads(config_path.read_text(encoding="utf-8-sig"))
    configs = []
    for cfg in _records(data):
        configs.append(
            MCPServerConfig(
                name=str(cfg["name"]),
                transport=str(cfg.get("transport", "stdio")).lower(),
                command=cfg.get("command"),
                args=[str(arg) for arg in cfg.get("args", [])],
                cwd=str(cfg["cwd"]) if cfg.get("cwd") else None,
                url=cfg.get("url"),
                env={str(k): str(v) for k, v in (cfg.get("env") or {}).items()} or None,
            )
        )
    return configs


async def _with_session(config: MCPServerConfig, fn):
    if config.transport == "stdio":
        if not config.command:
            raise ValueError(f"{config.name}: stdio transport requires a command")
        params = StdioServerParameters(
            command=config.command,
            args=config.args,
            cwd=config.cwd,
            env=config.env,
        )
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                return await fn(session)
    if config.transport in {"http", "streamable-http", "streamable_http"}:
        if not config.url:
            raise ValueError(f"{config.name}: {config.transport} transport requires a url")
        async with streamablehttp_client(config.url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                return await fn(session)
    raise ValueError(f"{config.name}: unsupported transport {config.transport}")


async def _list_remote_tools(config: MCPServerConfig):
    result = await _with_session(config, lambda session: session.list_tools())
    return result.tools


async def _call_remote_tool(config: MCPServerConfig, tool_name: str, arguments: dict[str, Any]):
    return await _with_session(config, lambda session: session.call_tool(tool_name, arguments=arguments))


def list_mcp_inventory(path: str | Path | None = None) -> dict[str, list[dict[str, str]]]:
    inventory = {
        "local": [
            {
                "server": LOCAL_SERVER,
                "tool": tool.name,
                "description": tool.description or "",
                "transport": "in-process",
            }
            for tool in list_local_tools()
        ],
        "external": [],
    }
    for config in load_server_configs(path):
        try:
            tools = _sync(_list_remote_tools(config))
            inventory["external"].append(
                {
                    "server": config.name,
                    "transport": config.transport,
                    "status": "connected",
                    "tools": ", ".join(tool.name for tool in tools) or "(none)",
                }
            )
        except Exception as exc:
            inventory["external"].append(
                {
                    "server": config.name,
                    "transport": config.transport,
                    "status": "error",
                    "tools": str(exc),
                }
            )
    return inventory


def _split_remote_name(tool_name: str, configs: list[MCPServerConfig]) -> tuple[str, str] | None:
    names = {cfg.name for cfg in configs}
    for separator in REMOTE_SEPARATORS:
        if separator not in tool_name:
            continue
        server, remote = tool_name.split(separator, 1)
        if server in names and remote:
            return server, remote
    return None


def dispatch(tool_name: str, **kwargs) -> ToolResult:
    """Dispatch to a local or remote MCP-backed tool."""
    if tool_name in TOOLS:
        _, payload = _sync(LOCAL_MCP.call_tool(tool_name, kwargs))
        return _normalize_payload(tool_name, payload)

    configs = load_server_configs()
    remote = _split_remote_name(tool_name, configs)
    if not remote:
        return ToolResult(tool=tool_name, success=False, output="", error=f"Unknown tool: {tool_name}")

    server_name, remote_tool = remote
    config = next(cfg for cfg in configs if cfg.name == server_name)
    try:
        result = _sync(_call_remote_tool(config, remote_tool, kwargs))
    except Exception as exc:
        return ToolResult(tool=tool_name, success=False, output="", error=str(exc), exit_code=1)
    return _normalize_remote_result(tool_name, result)
