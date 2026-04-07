"""jeff.bell - Jeff's MCP server surface and instance relay seam."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys

from mcp.server.fastmcp import FastMCP

from jeff import __version__
from jeff import bone
from jeff.pantry import is_available, list_models


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7331
BELL_TOOLS = [
    "jeff_run", "jeff_audit", "jeff_ask", "jeff_status",
    "jeff_k_history", "jeff_flaw_count", "jeff_coherence", "jeff_session",
]


def _payload(
    tool: str,
    success: bool,
    output: str = "",
    error: str = "",
    exit_code: int = 0,
    **extra,
) -> dict[str, str | int | bool]:
    payload = {
        "tool": tool,
        "success": success,
        "output": output,
        "error": error,
        "exit_code": exit_code,
    }
    payload.update({key: value for key, value in extra.items() if value is not None})
    return payload


def _sid(cwd: str) -> str:
    return hashlib.sha256(cwd.encode()).hexdigest()[:12]


def _run_cli(command: list[str], cwd: str | None = None, timeout: int = 120):
    target = cwd or os.getcwd()
    try:
        result = subprocess.run(
            [sys.executable, "-m", "jeff.cli", *command],
            cwd=target,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return _payload(
            command[0],
            success=result.returncode == 0,
            output=result.stdout.strip(),
            error=result.stderr.strip(),
            exit_code=result.returncode,
            cwd=target,
        )
    except subprocess.TimeoutExpired:
        return _payload(command[0], False, error=f"Timed out after {timeout}s", exit_code=1, cwd=target)
    except Exception as exc:
        return _payload(command[0], False, error=str(exc), exit_code=1, cwd=target)


def status() -> dict:
    return {
        "implemented": True,
        "version": __version__,
        "default_transport": "stdio",
        "network_transport": "streamable-http",
        "host": DEFAULT_HOST,
        "port": DEFAULT_PORT,
        "tools": BELL_TOOLS,
    }


def summary() -> str:
    s = status()
    return (
        f"Bell: MCP server ready. stdio is default. Network transport is "
        f"{s['network_transport']} on {s['host']}:{s['port']} when you start "
        "it with `jeff serve --transport http`."
    )


def _build_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> FastMCP:
    app = FastMCP("Jeff Bell", host=host, port=port, log_level="WARNING")

    @app.tool(structured_output=True)
    def jeff_status(cwd: str | None = None) -> dict[str, str | int | bool]:
        target = cwd or os.getcwd()
        session = bone.load_session(_sid(target))
        models = list_models() if is_available() else []
        output = (
            f"cwd={target}\n"
            f"session={'present' if session else 'missing'}\n"
            f"messages={len(session.messages) if session else 0}\n"
            f"ollama={'running' if models else 'offline'}\n"
            f"models={len(models)}"
        )
        return _payload(
            "jeff_status",
            True,
            output=output,
            cwd=target,
            session=session.id if session else "",
            messages=len(session.messages) if session else 0,
            models=len(models),
            ollama=bool(models),
        )

    @app.tool(structured_output=True)
    def jeff_ask(task: str, model: str | None = None, cwd: str | None = None) -> dict[str, str | int | bool]:
        command = ["ask"]
        if model:
            command.extend(["--model", model])
        command.append(task)
        return _run_cli(command, cwd=cwd)

    @app.tool(structured_output=True)
    def jeff_run(task: str, model: str | None = None, cwd: str | None = None) -> dict[str, str | int | bool]:
        command = ["run"]
        if model:
            command.extend(["--model", model])
        command.append(task)
        return _run_cli(command, cwd=cwd)

    @app.tool(structured_output=True)
    def jeff_audit(cwd: str | None = None) -> dict[str, str | int | bool]:
        return _run_cli(["audit"], cwd=cwd)

    @app.tool(structured_output=True)
    def jeff_k_history(
        context_fragment: str = "",
        limit: int = 50,
    ) -> dict[str, str | int | bool]:
        """Query retained K from the quality gate."""
        from jeff.gate import history_for
        rows = history_for(context_fragment=context_fragment, limit=limit)
        lines = []
        for row in rows:
            flaws = ", ".join(row.get("flaws", []))
            ctx = row.get("context", "")[:60]
            lines.append(f"[{flaws}] {ctx}")
        return _payload(
            "jeff_k_history",
            True,
            output="\n".join(lines) if lines else "No K-history found.",
            count=len(rows),
        )

    @app.tool(structured_output=True)
    def jeff_flaw_count(
        flaw: str = "",
        context_fragment: str = "",
        limit: int = 200,
    ) -> dict[str, str | int | bool]:
        """Count occurrences of a specific cognitive flaw."""
        from jeff.gate import CognitiveFlaw, count_flaws
        if flaw and flaw in CognitiveFlaw.__members__:
            n = count_flaws(CognitiveFlaw[flaw], context_fragment=context_fragment, limit=limit)
            return _payload("jeff_flaw_count", True, output=f"{flaw}: {n}", count=n)
        from jeff.gate import flaw_history
        all_flaws = flaw_history(limit=limit)
        from collections import Counter
        counts = Counter(f.name for f in all_flaws)
        lines = [f"{name}: {count}" for name, count in counts.most_common()]
        return _payload(
            "jeff_flaw_count",
            True,
            output="\n".join(lines) if lines else "No flaws recorded.",
            count=len(all_flaws),
        )

    @app.tool(structured_output=True)
    def jeff_coherence() -> dict[str, str | int | bool]:
        """Get phi coherence and awareness metrics from the evolve engine."""
        from jeff.mind.evolve import EvolutionEngine
        engine = EvolutionEngine()
        coh = engine.coherence()
        awa = engine.awareness()
        cb = engine.convergence_rate()
        return _payload(
            "jeff_coherence",
            True,
            output=engine.summary(),
            phi=round(coh, 4),
            awareness=round(awa, 4),
            convergence_rate=round(cb, 4),
            k_count=len(engine.k_history),
            strategy_count=len(engine.strategies),
        )

    @app.tool(structured_output=True)
    def jeff_session(
        session_id: str = "",
        cwd: str | None = None,
    ) -> dict[str, str | int | bool]:
        """Get a session's message history."""
        sid = session_id or _sid(cwd or os.getcwd())
        session = bone.load_session(sid)
        if not session:
            return _payload("jeff_session", False, error=f"Session {sid} not found")
        lines = []
        for msg in session.messages[-20:]:
            role = msg.role.upper()
            content = msg.content[:200]
            lines.append(f"[{role}] {content}")
        return _payload(
            "jeff_session",
            True,
            output="\n".join(lines),
            session_id=session.id,
            message_count=len(session.messages),
            tokens_in=session.tokens_in,
            tokens_out=session.tokens_out,
        )

    return app


def serve(transport: str = "stdio", host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    server = _build_server(host=host, port=port)
    chosen = "streamable-http" if transport == "http" else "stdio"
    server.run(chosen)
