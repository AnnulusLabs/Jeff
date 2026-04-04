"""jeff.nerve — Tool dispatch. Bash, file ops, grep, git. The hands that do the work."""

import subprocess
import os
from pathlib import Path
from dataclasses import dataclass

@dataclass
class ToolResult:
    tool: str
    success: bool
    output: str
    error: str = ""
    exit_code: int = 0


def bash(cmd: str, cwd: str | None = None, timeout: int = 120) -> ToolResult:
    """Execute a shell command."""
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            cwd=cwd or os.getcwd(), timeout=timeout,
        )
        return ToolResult(
            tool="bash", success=r.returncode == 0,
            output=r.stdout.strip(), error=r.stderr.strip(),
            exit_code=r.returncode,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(tool="bash", success=False, output="", error=f"Timed out after {timeout}s")
    except Exception as e:
        return ToolResult(tool="bash", success=False, output="", error=str(e))


def read_file(path: str) -> ToolResult:
    """Read file contents."""
    try:
        text = Path(path).read_text()
        return ToolResult(tool="read", success=True, output=text)
    except Exception as e:
        return ToolResult(tool="read", success=False, output="", error=str(e))


def write_file(path: str, content: str) -> ToolResult:
    """Write content to file, creating directories as needed."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return ToolResult(tool="write", success=True, output=f"Wrote {len(content)} bytes to {path}")
    except Exception as e:
        return ToolResult(tool="write", success=False, output="", error=str(e))


def edit_file(path: str, old: str, new: str) -> ToolResult:
    """Replace exact string in file. Must match exactly once."""
    try:
        text = Path(path).read_text()
        count = text.count(old)
        if count == 0:
            return ToolResult(tool="edit", success=False, output="", error="String not found in file")
        if count > 1:
            return ToolResult(tool="edit", success=False, output="", error=f"String found {count} times. Must be unique.")
        text = text.replace(old, new, 1)
        Path(path).write_text(text)
        return ToolResult(tool="edit", success=True, output=f"Edited {path}")
    except Exception as e:
        return ToolResult(tool="edit", success=False, output="", error=str(e))


def grep(pattern: str, path: str = ".", flags: str = "-rn") -> ToolResult:
    """Search for pattern in files."""
    return bash(f"grep {flags} {_quote(pattern)} {_quote(path)}")


def glob_files(pattern: str, root: str = ".") -> ToolResult:
    """Find files matching glob pattern."""
    try:
        matches = sorted(str(p) for p in Path(root).rglob(pattern) if p.is_file())
        return ToolResult(tool="glob", success=True, output="\n".join(matches))
    except Exception as e:
        return ToolResult(tool="glob", success=False, output="", error=str(e))


def git(subcmd: str, cwd: str | None = None) -> ToolResult:
    """Run a git subcommand."""
    return bash(f"git {subcmd}", cwd=cwd)


def tree(path: str = ".", depth: int = 3) -> ToolResult:
    """Directory listing."""
    return bash(f"find {_quote(path)} -maxdepth {depth} -type f | head -200")


# Tool registry — name → callable
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


def dispatch(tool_name: str, **kwargs) -> ToolResult:
    """Dispatch to a registered tool."""
    fn = TOOLS.get(tool_name)
    if not fn:
        return ToolResult(tool=tool_name, success=False, output="", error=f"Unknown tool: {tool_name}")
    return fn(**kwargs)


def _quote(s: str) -> str:
    """Shell-safe quoting."""
    return f"'{s}'" if " " in s and "'" not in s else s
