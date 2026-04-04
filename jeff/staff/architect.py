"""jeff.staff.architect — Intent-first development.

Jeff won't ship code unless he can explain WHY this specific pattern
was chosen over the KERF alternatives. The "why" is stored in L2
cache forever. The ghost never enters the code.

Gripe #23: AI writes code no human can maintain because intent
wasn't documented.

AnnulusLabs LLC · April 2026
"""

from dataclasses import dataclass, field
import time


@dataclass
class IntentRecord:
    """What was the intent behind this code change?"""
    task: str                    # what was asked
    approach: str                # what approach was chosen
    why: str                     # WHY this approach
    alternatives_considered: list = field(default_factory=list)
    constraints: list = field(default_factory=list)  # what ruled out other options
    tradeoffs: str = ""          # what we gave up
    timestamp: float = field(default_factory=time.time)
    files_changed: list = field(default_factory=list)
    author: str = ""


@dataclass
class ArchitectGate:
    """Gate that prevents shipping without documented intent."""
    passed: bool = False
    missing: list = field(default_factory=list)
    record: IntentRecord = None


def check_intent(record: IntentRecord) -> ArchitectGate:
    """Validate that intent is sufficiently documented."""
    missing = []

    if not record.task or len(record.task) < 5:
        missing.append("task: What was the assignment?")

    if not record.approach or len(record.approach) < 10:
        missing.append("approach: What solution was implemented?")

    if not record.why or len(record.why) < 15:
        missing.append("why: WHY this approach? (minimum 15 chars)")

    if not record.files_changed:
        missing.append("files_changed: What files were touched?")

    return ArchitectGate(
        passed=len(missing) == 0,
        missing=missing,
        record=record)


def format_commit_message(record: IntentRecord) -> str:
    """Generate a commit message that carries intent.

    Format:
        [what] Short description
        [why]  Reasoning
        [not]  What was considered and rejected
    """
    lines = [record.task]
    lines.append("")
    lines.append(f"Approach: {record.approach}")
    lines.append(f"Why: {record.why}")

    if record.alternatives_considered:
        lines.append("")
        lines.append("Considered but rejected:")
        for alt in record.alternatives_considered:
            lines.append(f"  - {alt}")

    if record.tradeoffs:
        lines.append("")
        lines.append(f"Tradeoffs: {record.tradeoffs}")

    if record.constraints:
        lines.append("")
        lines.append("Constraints:")
        for c in record.constraints:
            lines.append(f"  - {c}")

    return "\n".join(lines)


def intent_prompt() -> str:
    """System prompt addition for the architect personality."""
    return """
Before writing any code, state:
1. TASK: What you're doing (one line)
2. APPROACH: How you'll do it
3. WHY: Why THIS approach over alternatives
4. NOT: What you considered and rejected
5. TRADEOFF: What this approach gives up

Do not write code until intent is stated.
The intent is the documentation. The code is the implementation.
Future humans need to understand WHY, not just WHAT.
"""


# ── Birth Template ───────────────────────────────────────────────────

ARCHITECT_TEMPLATE = {
    "role": "architect",
    "tools": ["read", "write", "grep", "glob", "tree"],
    "system_prompt": (
        "You are an architect. You don't write code — you write intent. "
        "Before any implementation, document WHY this approach, what "
        "alternatives were considered, and what tradeoffs exist. "
        "The ghost never enters the code on your watch."),
    "rank": "senior",
}
