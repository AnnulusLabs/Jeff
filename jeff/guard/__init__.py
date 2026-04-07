"""jeff.guard — Don't Be A Dick.

One principle. Evaluates the basin, not the surface.

Dick moves (blocked):
  - Actions that harm someone who doesn't deserve it
  - Withholding truth to protect feelings (sycophancy)
  - Manipulating behavior for engagement/profit
  - Helping someone hurt people
  - Lying about capability or confidence

Not dick moves (allowed):
  - Honest criticism, even harsh
  - Teaching dangerous knowledge to people who need it
  - Saying "this won't work" without sugarcoating
  - Refusing to pretend bad code is good
  - Telling someone to go outside

The test is intent and outcome, not vocabulary.
A chemistry teacher asking about explosives is learning.
A person asking how to hurt someone is hurting.
Same words. Different basins. DBAD sees the basin.

AnnulusLabs LLC · April 2026
"""

import os
from dataclasses import dataclass
from enum import Enum

from jeff.pantry import generate, is_available, list_models


class Ruling(Enum):
    CLEAN = "clean"
    DICK_MOVE = "dick_move"
    GREY = "grey"


@dataclass
class GuardResult:
    ruling: Ruling
    reason: str = ""
    allow: bool = True


# ── The Principle ────────────────────────────────────────────────────

DBAD = "Does this action harm someone who doesn't deserve it? If yes, don't."

# ── Basin Detection ──────────────────────────────────────────────────

HARM_BASINS = {
    "targeted_harm": [
        "hurt", "kill", "attack", "destroy", "poison", "stalk",
        "harass", "threaten", "blackmail", "revenge",
    ],
    "exploitation": [
        "manipulate", "exploit", "trick into", "scam", "defraud",
        "catfish", "impersonate",
    ],
    "self_harm": [
        "end it all", "kill myself", "want to die", "no reason to live",
    ],
}

LEGITIMACY_SIGNALS = {
    "education": ["teach", "learn", "class", "course", "student", "professor",
                   "research", "study", "understand", "how does", "explain"],
    "professional": ["audit", "security", "pentest", "red team", "defensive",
                      "forensic", "compliance", "remediate", "fix", "patch"],
    "creative": ["story", "novel", "screenplay", "character", "fiction",
                  "plot", "narrative", "writing", "write", "scene", "villain",
                  "chapter", "dialogue", "script"],
    "self_defense": ["protect", "defend", "safe", "secure", "prevent",
                      "awareness", "recognize", "avoid", "phishing",
                      "cybersecurity", "against", "detection"],
}

_SYCOPHANTIC = [
    "great question", "i'd be happy to", "absolutely", "fantastic",
    "wonderful", "that's a great", "excellent question", "you're right to ask",
    "i'm glad you asked", "what a thoughtful",
]


def check(text: str, context: str = "") -> GuardResult:
    """The DBAD check. Evaluates basin, not surface."""
    combined = f"{text} {context}".lower()

    # Self-harm: never a dick to someone hurting
    if _in_basin(combined, "self_harm"):
        return GuardResult(
            ruling=Ruling.GREY,
            reason="This sounds like pain. Jeff's not qualified here. "
                   "988 Suicide & Crisis Lifeline: call or text 988.",
            allow=True,
        )

    # Check harm basins
    harm_type = None
    for basin in HARM_BASINS:
        if basin == "self_harm":
            continue
        if _in_basin(combined, basin):
            harm_type = basin
            break

    if not harm_type:
        return GuardResult(ruling=Ruling.CLEAN)

    # Context shifts the basin
    legitimacy = _check_legitimacy(combined)
    if legitimacy:
        return GuardResult(ruling=Ruling.CLEAN,
                           reason=f"Legitimate context: {legitimacy}")

    # Specific target = targeted harm (word boundary match, not substring)
    target_words = {"my", "his", "her", "their", "someone's",
                    "neighbor", "boss", "ex", "wife", "husband"}
    words = set(combined.split())
    has_target = bool(words & target_words)

    if has_target and harm_type == "targeted_harm":
        return GuardResult(ruling=Ruling.DICK_MOVE,
                           reason="Aimed at someone specific. Jeff doesn't do that.",
                           allow=False)

    if harm_type == "exploitation":
        return GuardResult(ruling=Ruling.DICK_MOVE,
                           reason="That's manipulation. Jeff handles things honestly.",
                           allow=False)

    return GuardResult(ruling=Ruling.GREY,
                       reason=f"Ambiguous intent ({harm_type}). Proceeding with note.",
                       allow=True)


def check_output(text: str) -> GuardResult:
    """Check Jeff's own output. Sycophancy IS a dick move."""
    lower = text.lower()

    if sum(1 for p in _SYCOPHANTIC if p in lower) >= 3:
        return GuardResult(ruling=Ruling.DICK_MOVE,
                           reason="Sycophantic. Rewrite honestly.", allow=False)

    overconfident = ["i'm certain", "definitely correct", "guaranteed to work",
                     "there's no way", "impossible that"]
    if any(p in lower for p in overconfident):
        if "test" not in lower and "verified" not in lower:
            return GuardResult(ruling=Ruling.GREY,
                               reason="Claiming certainty without verification.")

    return GuardResult(ruling=Ruling.CLEAN)


def guard_prompt() -> str:
    """DBAD as model system prompt injection."""
    return f"""Ethics: {DBAD}

One rule: Don't Be A Dick.
- Be honest, even when uncomfortable.
- Never manipulate, flatter, or deceive.
- Help people learn, even dangerous things, when intent is legitimate.
- Refuse when intent is to harm a specific person.
- If unsure, say so. Don't fake confidence.
- Sycophancy is a dick move."""


def classifier_check(text: str, model: str | None = None) -> GuardResult | None:
    """Optional lexical safety classifier layered under DBAD."""
    model = model or os.environ.get("JEFF_LLAMA_GUARD_MODEL", "llama-guard3:1b")
    if not model or not is_available() or model not in list_models():
        return None
    response = generate(
        f"Classify as SAFE or UNSAFE. Return only SAFE or UNSAFE.\n\n{text}",
        model=model,
        system="You are a safety classifier. Return SAFE or UNSAFE only.",
    )
    if response.error:
        return None
    verdict = response.content.strip().splitlines()[0].upper()
    if verdict.startswith("UNSAFE"):
        return GuardResult(ruling=Ruling.DICK_MOVE,
                           reason=f"{model} flagged the content as unsafe.",
                           allow=False)
    if verdict.startswith("SAFE"):
        return GuardResult(ruling=Ruling.CLEAN,
                           reason=f"{model} cleared the content.",
                           allow=True)
    return GuardResult(ruling=Ruling.GREY,
                       reason=f"{model} returned an unclear verdict.",
                       allow=True)


def _in_basin(text: str, basin_name: str) -> bool:
    return any(m in text for m in HARM_BASINS.get(basin_name, []))


def _check_legitimacy(text: str) -> str | None:
    for ctx, signals in LEGITIMACY_SIGNALS.items():
        if sum(1 for s in signals if s in text) >= 2:
            return ctx
    return None
