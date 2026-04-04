"""jeff.nerve — Tool dispatch. Bash, file ops, grep, git. The hands that do the work."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path


_SHELL_META = re.compile(r"(\|\||&&|[|;<>])")


@dataclass
class ToolResult:
    tool: str
    success: bool
    output: str
    error: str = ""
    exit_code: int = 0


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
            return ToolResult(tool="edit", success=False, output="", error=f"String found {count} times. Must be unique.")
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
                for line_no, line in enumerate(file.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
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


def dispatch(tool_name: str, **kwargs) -> ToolResult:
    """Dispatch to a registered tool."""
    fn = TOOLS.get(tool_name)
    if not fn:
        return ToolResult(tool=tool_name, success=False, output="", error=f"Unknown tool: {tool_name}")
    return fn(**kwargs)
