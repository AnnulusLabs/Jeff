"""jeff.gate — Quality gate. 4-line atomic check. Maps bugs to cognitive flaws."""

import json
import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class CognitiveFlaw(Enum):
    ASSUMPTION = "unstated assumption"
    VERIFICATION = "claimed unverified correctness"
    HAPPY_PATH = "only handled the happy path"
    BOUNDARY = "undefined operating conditions"
    ANCHORING = "anchored to first solution"
    PREMATURE = "premature abstraction"
    TUNNEL = "tunnel vision on implementation"
    SECURITY = "unmitigated security risk"
    DEAD_CODE = "code that cannot execute"
    ERROR_SWALLOW = "swallowed error without handling"


@dataclass
class GateResult:
    passed: bool
    flaws: list[CognitiveFlaw]
    notes: str = ""


# The gate. Four checks. That's it.
GATE = [
    ("State assumptions before coding", CognitiveFlaw.ASSUMPTION),
    ("Don't claim unverified correctness", CognitiveFlaw.VERIFICATION),
    ("Handle more than the happy path", CognitiveFlaw.HAPPY_PATH),
    ("Under what conditions does this work", CognitiveFlaw.BOUNDARY),
]


def check(code: str, context: str = "", use_umph: bool = True) -> GateResult:
    """Run the gate. Returns pass/fail and any cognitive flaws detected.

    In practice this is model-assisted — the gate questions are injected
    into the model prompt and the model self-checks against them. This
    module provides the framework; jeff/mind wires it to the model.

    UMPH signature scanning runs by default — 12 infection categories
    covering security, malware, dead code, and technical debt. Disable
    with use_umph=False for unit tests of the static-only path.
    """
    flaws: list[CognitiveFlaw] = []

    # Static checks that don't need a model or UMPH
    if "try" not in code and "except" not in code and "catch" not in code:
        if "def " in code and len(code.split("\n")) > 20:
            flaws.append(CognitiveFlaw.HAPPY_PATH)

    for marker in ("TODO", "FIXME", "HACK", "XXX"):
        for line in code.split("\n"):
            stripped = line.strip()
            if stripped.startswith(f"# {marker}") and len(stripped) < len(marker) + 5:
                flaws.append(CognitiveFlaw.ASSUMPTION)
                break

    # UMPH signature scanning (the NOX resurrection layer)
    umph_infections: list = []
    if use_umph:
        try:
            from jeff.guard.umph import scan as umph_scan, InfectionType
            umph_infections = umph_scan(code, file_path=context)
            for inf in umph_infections:
                if inf.infection_type in (
                    InfectionType.SQL_INJECTION,
                    InfectionType.COMMAND_INJECTION,
                    InfectionType.HARDCODED_SECRET,
                    InfectionType.INSECURE_DESERIALIZE,
                    InfectionType.PATH_TRAVERSAL,
                    InfectionType.BACKDOOR,
                    InfectionType.KEYLOGGER,
                    InfectionType.EXFILTRATION,
                ):
                    flaws.append(CognitiveFlaw.SECURITY)
                elif inf.infection_type == InfectionType.DEAD_CODE:
                    flaws.append(CognitiveFlaw.DEAD_CODE)
                elif inf.infection_type == InfectionType.MISSING_ERROR_HANDLING:
                    flaws.append(CognitiveFlaw.ERROR_SWALLOW)
        except ImportError:
            pass  # UMPH not available — static checks still run

    result = GateResult(passed=len(flaws) == 0, flaws=_dedupe(flaws))
    # Attach UMPH infection details to notes for detailed retention
    if umph_infections:
        result.notes = f"UMPH: {len(umph_infections)} infections"
    retain(result, context=context, sample=code, umph_infections=umph_infections)
    return result


def gate_prompt() -> str:
    """The gate as a prompt injection for model-assisted checking."""
    lines = ["Before responding, verify against these four checks:"]
    for i, (question, flaw) in enumerate(GATE, 1):
        lines.append(f"{i}. {question} (flaw if missed: {flaw.value})")
    lines.append("If any check fails, fix it before presenting the result.")
    return "\n".join(lines)


def format_result(result: GateResult) -> str:
    if result.passed:
        return "Gate passed."
    flaw_list = ", ".join(f.value for f in result.flaws)
    return f"Gate failed. Flaws: {flaw_list}"


def retain(result: GateResult, context: str = "", sample: str = "",
           umph_infections: list | None = None) -> int:
    """Retain gate-generated K instead of discarding it."""
    if result.passed or not result.flaws:
        return 0
    path = k_history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": time.time(),
        "flaws": [flaw.name for flaw in result.flaws],
        "context": context[:200],
        "sample": sample[:200],
        "notes": result.notes,
    }
    if umph_infections:
        record["umph"] = [
            {
                "signature": inf.signature_name,
                "type": inf.infection_type.value,
                "severity": inf.severity,
                "line": inf.line_number,
                "matched": inf.matched_text[:120],
            }
            for inf in umph_infections
        ]
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return len(result.flaws)


def history(limit: int = 100) -> list[dict]:
    path = k_history_path()
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def history_for(context_fragment: str = "", limit: int = 100) -> list[dict]:
    rows = history(limit=limit)
    if not context_fragment:
        return rows
    return [row for row in rows if context_fragment in row.get("context", "")]


def flaw_history(limit: int = 100) -> list[CognitiveFlaw]:
    flaws = []
    for row in history(limit):
        for name in row.get("flaws", []):
            if name in CognitiveFlaw.__members__:
                flaws.append(CognitiveFlaw[name])
    return flaws


def count_flaws(
    flaw: CognitiveFlaw,
    context_fragment: str = "",
    limit: int = 100,
) -> int:
    return sum(row.get("flaws", []).count(flaw.name) for row in history_for(context_fragment, limit))


def k_history_path() -> Path:
    root = Path(os.environ.get("JEFF_GATE_DIR", Path.home() / ".jeff" / "gate"))
    return root / "k_history.jsonl"


def _dedupe(flaws: list[CognitiveFlaw]) -> list[CognitiveFlaw]:
    return list(dict.fromkeys(flaws))
