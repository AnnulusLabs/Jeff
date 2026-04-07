"""jeff.guard.umph — UMPH signature scanner (NOX resurrection).

UMPH originally shipped in NOX as the metacognitive code security layer.
NOX never crossed the line from real ideas in unfinished code to working
software — the AI tools of 2024 couldn't reliably implement security code.

Jeff is the body NOX was always supposed to have. UMPH finally has a runtime
that keeps it alive. The first thing it did when it landed was find a SQL
injection in Jeff's own telemetry module.

This is the signature-scanning layer. It hunts 12 categories of infection:
  - Security (SQL injection, command injection, hardcoded secrets, etc.)
  - Malware (backdoors, keyloggers, exfiltration)
  - Dead code (unreachable, always-false)
  - Technical debt (bare except, TODO/FIXME)

Adapted from NOX/KERF guard/umph/umph_system.py. Strips the attack/quarantine
machinery — Jeff reports, doesn't modify. Humans fix.

AnnulusLabs LLC · April 2026
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class InfectionType(Enum):
    """Categories of code infections UMPH hunts."""

    # Structural
    DEAD_CODE = "dead_code"
    DEAD_FUNCTION = "dead_function"
    DEAD_IMPORT = "dead_import"

    # Logic
    INFINITE_LOOP = "infinite_loop"
    NULL_DEREF = "null_deref"
    RACE_CONDITION = "race_condition"

    # Security (critical)
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    HARDCODED_SECRET = "hardcoded_secret"
    INSECURE_DESERIALIZE = "insecure_deserialize"
    INSECURE_RANDOM = "insecure_random"

    # Malware
    BACKDOOR = "backdoor"
    KEYLOGGER = "keylogger"
    EXFILTRATION = "exfiltration"

    # Technical debt
    MISSING_ERROR_HANDLING = "missing_error"
    COMPLEXITY = "complexity"
    TODO_MARKER = "todo_marker"


@dataclass
class InfectionSignature:
    """A signature for recognizing infected code."""
    name: str
    infection_type: InfectionType
    patterns: list[str] = field(default_factory=list)
    severity: int = 5  # 1-10
    exceptions: list[str] = field(default_factory=list)

    def matches(self, code: str) -> list[tuple[int, int, str]]:
        """Find all matches. Returns [(start, end, matched_text), ...].

        Patterns run with MULTILINE only (not DOTALL) so `.` does not span
        newlines by default. This prevents a single `execute(...)` regex
        from eating an entire multi-line file looking for a match token.
        """
        hits = []
        for pattern in self.patterns:
            try:
                for m in re.finditer(pattern, code, re.MULTILINE):
                    matched = m.group(0)
                    excepted = False
                    if self.exceptions:
                        context = code[max(0, m.start() - 80):m.end() + 80]
                        for exc in self.exceptions:
                            if re.search(exc, context):
                                excepted = True
                                break
                    if not excepted:
                        hits.append((m.start(), m.end(), matched))
            except re.error:
                continue
        return hits


# ── Built-in signatures (12 across 4 categories) ──────────────────

BUILT_IN_SIGNATURES: list[InfectionSignature] = [
    # ═══ SECURITY (critical) ═══
    InfectionSignature(
        name="sql_injection_format",
        infection_type=InfectionType.SQL_INJECTION,
        patterns=[
            # %-formatting: "SELECT..." % var
            r'execute\s*\(\s*["\'][^"\']*%s[^"\']*["\']\s*%',
            # f-string SQL with interpolation: execute(f"...{var}...")
            r'execute\s*\(\s*f["\'][^"\']*\{[^}]+\}',
            # String concat into SQL: execute("..." + var) or execute(var + "...")
            r'execute\s*\(\s*["\'][^"\']*["\']\s*\+',
            r'execute\s*\(\s*\w+\s*\+\s*["\']',
            # .format() building SQL: execute("...{}...".format(...))
            r'execute\s*\(\s*["\'][^"\']*\{\}[^"\']*["\']\s*\.\s*format',
        ],
        severity=10,
        exceptions=[r'execute\s*\([^,]+,\s*\('],  # Parameterized queries OK
    ),
    InfectionSignature(
        name="command_injection",
        infection_type=InfectionType.COMMAND_INJECTION,
        patterns=[
            r'os\.system\s*\([^)]*\+',
            r'os\.system\s*\(f["\']',
            r'subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True',
            r'eval\s*\([^)]*input\s*\(',
            r'exec\s*\([^)]*input\s*\(',
        ],
        severity=10,
    ),
    InfectionSignature(
        name="hardcoded_secrets",
        infection_type=InfectionType.HARDCODED_SECRET,
        patterns=[
            r'password\s*=\s*["\'][^"\']{8,}["\']',
            r'api_key\s*=\s*["\'][^"\']{16,}["\']',
            r'secret\s*=\s*["\'][^"\']{8,}["\']',
            r'token\s*=\s*["\'][A-Za-z0-9]{20,}["\']',
            r'AWS_SECRET_ACCESS_KEY\s*=\s*["\']',
        ],
        severity=9,
        exceptions=[r'os\.environ', r'getenv', r'config\.', r'example', r'test'],
    ),
    InfectionSignature(
        name="insecure_deserialize",
        infection_type=InfectionType.INSECURE_DESERIALIZE,
        patterns=[
            r'pickle\.loads?\s*\(',
            r'yaml\.load\s*\([^)]*\)(?!\s*,\s*Loader)',
            r'eval\s*\(\s*request',
            r'exec\s*\(\s*request',
        ],
        severity=9,
    ),
    InfectionSignature(
        name="path_traversal",
        infection_type=InfectionType.PATH_TRAVERSAL,
        patterns=[
            r'open\s*\([^)]*\+[^)]*\)',
            r'open\s*\(f["\'][^"\']*\{',
        ],
        severity=8,
        exceptions=[r'os\.path\.basename', r'sanitize', r'Path\('],
    ),

    # ═══ MALWARE ═══
    InfectionSignature(
        name="reverse_shell",
        infection_type=InfectionType.BACKDOOR,
        patterns=[
            r'socket\.socket\s*\([^)]*\).*connect.*\/bin\/(ba)?sh',
            r'subprocess.*PIPE.*socket',
            r'pty\.spawn.*\/bin',
        ],
        severity=10,
    ),
    InfectionSignature(
        name="keylogger_pattern",
        infection_type=InfectionType.KEYLOGGER,
        patterns=[
            r'pynput.*keyboard.*Listener',
            r'GetAsyncKeyState',
            r'keyboard\.on_press',
        ],
        severity=10,
    ),
    InfectionSignature(
        name="exfiltration_pattern",
        infection_type=InfectionType.EXFILTRATION,
        patterns=[
            r'requests\.(post|put)\s*\([^)]*password',
            r'urllib.*open.*\+.*password',
            r'socket.*send.*credentials',
        ],
        severity=10,
    ),

    # ═══ DEAD CODE ═══
    # Note: unreachable_after_return is intentionally NOT in the default
    # signature set. Accurate dead-code detection requires AST analysis,
    # not regex — a regex can't distinguish "early return guard" from
    # "return followed by dead code in the same block." See umph_ast.py
    # (future work) for the AST-based version.
    InfectionSignature(
        name="always_false_condition",
        infection_type=InfectionType.DEAD_CODE,
        patterns=[
            r'^\s*if\s+False\s*:',
            r'^\s*while\s+False\s*:',
        ],
        severity=2,
    ),

    # ═══ TECHNICAL DEBT ═══
    InfectionSignature(
        name="bare_except",
        infection_type=InfectionType.MISSING_ERROR_HANDLING,
        patterns=[
            r'^\s*except\s*:',
        ],
        severity=4,
    ),
    InfectionSignature(
        name="todo_fixme",
        infection_type=InfectionType.TODO_MARKER,
        patterns=[
            r'#\s*(TODO|FIXME|HACK|XXX|BUG)\b',
        ],
        severity=2,
    ),
]


@dataclass
class Infection:
    """A detected infection in code."""
    signature_name: str
    infection_type: InfectionType
    severity: int
    file_path: str
    line_number: int
    matched_text: str
    context: str = ""

    def __str__(self) -> str:
        loc = f"{self.file_path}:{self.line_number}" if self.file_path else f"line {self.line_number}"
        return f"{loc} [{self.infection_type.value}] {self.signature_name} (severity={self.severity})"


# ── Scanner ───────────────────────────────────────────────────────

# Lines with this marker are explicitly reviewed and excluded from scan.
# Format: `# umph:allow:<infection_type>` — matches the InfectionType value.
UMPH_ALLOW_MARKER = "umph:allow:"

# Files that define UMPH signatures will match their own patterns (the regex
# strings contain the tokens they hunt). Exclude these from self-scan.
_SELF_EXCLUDE = ("jeff/guard/umph.py", "jeff\\guard\\umph.py")


def _line_has_allow(lines: list[str], line_num: int, infection_value: str) -> bool:
    """Check if the line or an adjacent line has an explicit allow marker."""
    for offset in range(-2, 3):
        idx = line_num - 1 + offset
        if 0 <= idx < len(lines):
            line = lines[idx]
            if UMPH_ALLOW_MARKER in line:
                marker_text = line.split(UMPH_ALLOW_MARKER, 1)[1]
                if marker_text.startswith(infection_value):
                    return True
    return False


def scan(code: str, file_path: str = "") -> list[Infection]:
    """Scan code for infections across all built-in signatures.

    Returns an empty list for the umph module itself (it contains the
    signature patterns and matches them by definition). Lines marked with
    `# umph:allow:<type>` are excluded as explicit, reviewed exceptions.
    """
    if file_path and any(file_path.endswith(ex) for ex in _SELF_EXCLUDE):
        return []
    infections = []
    lines = code.split("\n")
    for sig in BUILT_IN_SIGNATURES:
        for start, end, matched in sig.matches(code):
            line_num = code[:start].count("\n") + 1
            if _line_has_allow(lines, line_num, sig.infection_type.value):
                continue
            ctx_start = max(0, line_num - 2)
            ctx_end = min(len(lines), line_num + 2)
            context = "\n".join(lines[ctx_start:ctx_end])
            infections.append(Infection(
                signature_name=sig.name,
                infection_type=sig.infection_type,
                severity=sig.severity,
                file_path=file_path,
                line_number=line_num,
                matched_text=matched.strip()[:120],
                context=context,
            ))
    return infections


def scan_file(path: str | Path) -> list[Infection]:
    """Scan a file by path."""
    p = Path(path)
    try:
        code = p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    return scan(code, file_path=str(p))


def scan_directory(
    root: str | Path,
    extensions: tuple[str, ...] = (".py",),
) -> list[Infection]:
    """Recursively scan a directory."""
    base = Path(root)
    if not base.exists():
        return []
    infections = []
    for ext in extensions:
        for path in base.rglob(f"*{ext}"):
            if not path.is_file():
                continue
            infections.extend(scan_file(path))
    return infections


# ── Reporting ─────────────────────────────────────────────────────

def summarize(infections: list[Infection]) -> dict:
    """Summary stats by severity and type."""
    if not infections:
        return {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "by_type": {}}
    by_type: dict[str, int] = {}
    critical = high = medium = low = 0
    for inf in infections:
        by_type[inf.infection_type.value] = by_type.get(inf.infection_type.value, 0) + 1
        if inf.severity >= 8:
            critical += 1
        elif inf.severity >= 5:
            high += 1
        elif inf.severity >= 3:
            medium += 1
        else:
            low += 1
    return {
        "total": len(infections),
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
        "by_type": by_type,
    }


def format_report(infections: list[Infection]) -> str:
    """Format infections as a human-readable report."""
    if not infections:
        return "UMPH: No infections found."
    summary = summarize(infections)
    lines = [
        f"UMPH: {summary['total']} infections",
        f"  critical: {summary['critical']}  high: {summary['high']}  "
        f"medium: {summary['medium']}  low: {summary['low']}",
        "",
    ]
    # Sort by severity desc, then file
    ordered = sorted(infections, key=lambda i: (-i.severity, i.file_path, i.line_number))
    for inf in ordered:
        lines.append(f"  {inf}")
    return "\n".join(lines)


def critical_infections(infections: list[Infection]) -> list[Infection]:
    """Filter to critical (severity >= 8) only."""
    return [i for i in infections if i.severity >= 8]
