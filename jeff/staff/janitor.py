"""jeff.staff.janitor — The janitor checks for rot.

Background agent that periodically scans your local Jeff projects
for bit-rot, outdated dependencies, security patches, and dead code.

Gripe #40: AI builds a tool, you stop using it, it rots.

AnnulusLabs LLC · April 2026
"""

import os
import time
import subprocess
import json
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class RotReport:
    project: str
    issues: list = field(default_factory=list)
    last_commit_days: float = 0
    outdated_deps: list = field(default_factory=list)
    missing_files: list = field(default_factory=list)
    security_flags: list = field(default_factory=list)
    health: str = "unknown"  # "healthy", "stale", "rotting", "dead"


# ── Detectors ────────────────────────────────────────────────────────

def _last_commit_age(cwd: str) -> float:
    """Days since last commit."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct"],
            cwd=cwd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            ts = float(result.stdout.strip())
            return (time.time() - ts) / 86400
    except Exception:
        pass
    return -1


def _check_deps_python(cwd: str) -> list[str]:
    """Check for outdated Python dependencies."""
    outdated = []
    req_file = Path(cwd) / "requirements.txt"
    pyproject = Path(cwd) / "pyproject.toml"

    if not req_file.exists() and not pyproject.exists():
        return ["No dependency file found (requirements.txt or pyproject.toml)"]

    try:
        result = subprocess.run(
            ["pip", "list", "--outdated", "--format=json"],
            capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout:
            packages = json.loads(result.stdout)
            for pkg in packages[:10]:
                outdated.append(
                    f"{pkg['name']}: {pkg['version']} → {pkg['latest_version']}")
    except Exception:
        pass
    return outdated


def _check_expected_files(cwd: str) -> list[str]:
    """Check for files every healthy project should have."""
    missing = []
    expected = [
        ("README.md", "No README — how will future-you know what this does?"),
        ("LICENSE", "No license — legally ambiguous"),
        (".gitignore", "No .gitignore — __pycache__ in the repo"),
    ]
    for filename, msg in expected:
        if not (Path(cwd) / filename).exists():
            missing.append(msg)
    return missing


def _check_security(cwd: str) -> list[str]:
    """Basic security scan."""
    flags = []
    root = Path(cwd)

    # Check for exposed secrets
    secret_patterns = [
        ".env", "credentials.json", "secrets.yaml",
        "id_rsa", "id_ed25519", ".pem",
    ]
    for pattern in secret_patterns:
        for match in root.rglob(pattern):
            if ".git" not in str(match):
                flags.append(f"Potential secret in repo: {match.name}")

    # Check for hardcoded tokens in Python files
    for py in root.rglob("*.py"):
        if "__pycache__" in str(py):
            continue
        try:
            content = py.read_text(errors="ignore")
            for i, line in enumerate(content.split("\n"), 1):
                low = line.lower()
                if any(k in low for k in ["api_key", "secret_key", "password"]):
                    if "=" in line and not line.strip().startswith("#"):
                        if "os.environ" not in line and "getenv" not in line:
                            flags.append(
                                f"{py.name}:{i} — possible hardcoded credential")
        except Exception:
            pass

    return flags[:10]


def _check_dead_code(cwd: str) -> list[str]:
    """Find Python files with no imports (likely dead)."""
    dead = []
    root = Path(cwd)
    py_files = list(root.rglob("*.py"))
    if not py_files:
        return []

    # Build import graph (simplified)
    all_modules = set()
    imported_modules = set()
    for py in py_files:
        if "__pycache__" in str(py) or "__init__" in py.name:
            continue
        all_modules.add(py.stem)
        try:
            content = py.read_text(errors="ignore")
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("from ") or line.startswith("import "):
                    parts = line.split()
                    for part in parts:
                        imported_modules.add(part.split(".")[-1])
        except Exception:
            pass

    orphans = all_modules - imported_modules
    # Filter — don't flag entry points
    entry_points = {"cli", "main", "app", "server", "manage", "__main__"}
    orphans -= entry_points

    for name in list(orphans)[:5]:
        dead.append(f"{name}.py — not imported by any other module")

    return dead


# ── Main Scan ────────────────────────────────────────────────────────

def scan_project(cwd: str = ".") -> RotReport:
    """Full rot scan on a project directory."""
    report = RotReport(project=os.path.basename(os.path.abspath(cwd)))

    # Age
    days = _last_commit_age(cwd)
    report.last_commit_days = days
    if days > 180:
        report.issues.append(f"Last commit: {days:.0f} days ago — project may be abandoned")
    elif days > 30:
        report.issues.append(f"Last commit: {days:.0f} days ago — getting stale")

    # Dependencies
    report.outdated_deps = _check_deps_python(cwd)
    if len(report.outdated_deps) > 5:
        report.issues.append(f"{len(report.outdated_deps)} outdated dependencies")

    # Missing files
    report.missing_files = _check_expected_files(cwd)
    report.issues.extend(report.missing_files)

    # Security
    report.security_flags = _check_security(cwd)
    if report.security_flags:
        report.issues.append(f"{len(report.security_flags)} security concern(s)")

    # Health score
    issue_count = len(report.issues)
    if issue_count == 0:
        report.health = "healthy"
    elif issue_count <= 2:
        report.health = "stale"
    elif issue_count <= 5:
        report.health = "rotting"
    else:
        report.health = "dead"

    return report


def format_report(report: RotReport) -> str:
    """Human-readable rot report."""
    icons = {"healthy": "+", "stale": "~", "rotting": "!", "dead": "X"}
    icon = icons.get(report.health, "?")
    lines = [f"[{icon}] {report.project} — {report.health.upper()}"]

    if report.last_commit_days > 0:
        lines.append(f"    Last commit: {report.last_commit_days:.0f} days ago")

    if report.issues:
        lines.append("    Issues:")
        for issue in report.issues:
            lines.append(f"      - {issue}")

    if report.security_flags:
        lines.append("    Security:")
        for flag in report.security_flags:
            lines.append(f"      - {flag}")

    if report.outdated_deps:
        lines.append(f"    Outdated deps: {len(report.outdated_deps)}")
        for dep in report.outdated_deps[:5]:
            lines.append(f"      - {dep}")

    return "\n".join(lines)


# ── Batch Scan ───────────────────────────────────────────────────────

JANITOR_TEMPLATE = {
    "role": "janitor",
    "tools": ["read", "grep", "glob", "tree"],
    "system_prompt": (
        "You are the janitor. You check for rot. Outdated deps, "
        "missing docs, exposed secrets, dead code, stale commits. "
        "Report honestly. Fix what's easy. Flag what's not."),
    "rank": "staff",
}
