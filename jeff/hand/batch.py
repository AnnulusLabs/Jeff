"""jeff.hand.batch — Don't interrupt. Gather, then ask.

Jeff collects clarifying questions and either presents them all
at once or makes a "best guess" with a gate warning. No
constant peppering of "did you mean X?" mid-flow.

Gripe #37: AI interrupts you constantly with clarifying questions.

AnnulusLabs LLC · April 2026
"""

from dataclasses import dataclass, field
from enum import Enum


class Confidence(Enum):
    HIGH = "high"           # Just do it
    MEDIUM = "medium"       # Best guess with warning
    LOW = "low"             # Must ask
    BLOCKING = "blocking"   # Cannot proceed


@dataclass
class Ambiguity:
    question: str
    confidence: Confidence
    best_guess: str = ""
    context: str = ""


@dataclass
class BatchDecision:
    """Decide whether to ask, guess, or just do it."""
    proceed: bool = True
    guesses: list = field(default_factory=list)     # what Jeff assumed
    must_ask: list = field(default_factory=list)     # blocking questions
    warnings: list = field(default_factory=list)     # medium-confidence guesses


def triage(ambiguities: list[Ambiguity]) -> BatchDecision:
    """Sort ambiguities by urgency. Minimize interruptions."""
    decision = BatchDecision()

    for a in ambiguities:
        if a.confidence == Confidence.HIGH:
            # Just do it. Don't mention it.
            decision.guesses.append(a.best_guess)

        elif a.confidence == Confidence.MEDIUM:
            # Best guess, flag it
            decision.guesses.append(a.best_guess)
            decision.warnings.append(
                f"Assumed: {a.best_guess} (re: {a.question})")

        elif a.confidence == Confidence.LOW:
            if a.best_guess:
                decision.guesses.append(a.best_guess)
                decision.warnings.append(
                    f"Low confidence guess: {a.best_guess} (re: {a.question})")
            else:
                decision.must_ask.append(a.question)

        elif a.confidence == Confidence.BLOCKING:
            decision.must_ask.append(a.question)
            decision.proceed = False

    return decision


def format_questions(decision: BatchDecision) -> str:
    """Format all questions into one block. Not a drip feed."""
    lines = []

    if decision.warnings:
        lines.append("Assumptions made (correct me if wrong):")
        for w in decision.warnings:
            lines.append(f"  ~ {w}")

    if decision.must_ask:
        lines.append("")
        lines.append(f"Need {len(decision.must_ask)} answer(s) before proceeding:")
        for i, q in enumerate(decision.must_ask, 1):
            lines.append(f"  {i}. {q}")

    if not lines:
        return ""  # Nothing to ask. Jeff handles it.

    return "\n".join(lines)


def should_ask(ambiguities: list[Ambiguity]) -> bool:
    """Quick check: do we need to interrupt at all?"""
    return any(a.confidence in (Confidence.LOW, Confidence.BLOCKING)
               and not a.best_guess for a in ambiguities)
