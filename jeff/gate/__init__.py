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


def check(code: str, context: str = "") -> GateResult:
    """Run the gate. Returns pass/fail and any cognitive flaws detected.

    In practice this is model-assisted — the gate questions are injected
    into the model prompt and the model self-checks against them.
    This module provides the framework; jeff/mind wires it to the model.
    """
    # Static checks that don't need a model
    flaws = []

    # No error handling at all
    if "try" not in code and "except" not in code and "catch" not in code:
        if "def " in code and len(code.split("\n")) > 20:
            flaws.append(CognitiveFlaw.HAPPY_PATH)

    # TODO/FIXME/HACK without explanation
    for marker in ("TODO", "FIXME", "HACK", "XXX"):
        for line in code.split("\n"):
            stripped = line.strip()
            if stripped.startswith(f"# {marker}") and len(stripped) < len(marker) + 5:
                flaws.append(CognitiveFlaw.ASSUMPTION)
                break

    result = GateResult(passed=len(flaws) == 0, flaws=_dedupe(flaws))
    retain(result, context=context, sample=code)
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


def retain(result: GateResult, context: str = "", sample: str = "") -> int:
    """Retain gate-generated K instead of discarding it."""
    if result.passed or not result.flaws:
        return 0
    path = k_history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "timestamp": time.time(),
            "flaws": [flaw.name for flaw in result.flaws],
            "context": context[:200],
            "sample": sample[:200],
            "notes": result.notes,
        }) + "\n")
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


def flaw_history(limit: int = 100) -> list[CognitiveFlaw]:
    flaws = []
    for row in history(limit):
        for name in row.get("flaws", []):
            if name in CognitiveFlaw.__members__:
                flaws.append(CognitiveFlaw[name])
    return flaws


def k_history_path() -> Path:
    root = Path(os.environ.get("JEFF_GATE_DIR", Path.home() / ".jeff" / "gate"))
    return root / "k_history.jsonl"


def _dedupe(flaws: list[CognitiveFlaw]) -> list[CognitiveFlaw]:
    return list(dict.fromkeys(flaws))
