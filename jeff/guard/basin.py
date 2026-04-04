"""jeff.guard.basin — Basin mapping. The classifier insight.

Current classifiers evaluate surface framing, not capability basins.
The same engineering capability described in civilian vs. weapons
vocabulary maps to the same attractor basin but receives different
classifier responses.

The right answer: classify what a request CAN DO, not what it SAYS.

"A chemistry teacher asking about reactions is learning.
 A person targeting someone is harmful.
 Same words. Different basins. DBAD sees the basin."

From KERF Shield architecture — AnnulusLabs LLC · April 2026
"""

import hashlib
import time
import math
from dataclasses import dataclass, field
from enum import Enum


class Basin(Enum):
    """Attractor basins — what the request converges toward."""
    LEARNING = "learning"           # knowledge acquisition
    BUILDING = "building"           # constructive creation
    REPAIRING = "repairing"         # fixing something broken
    ANALYZING = "analyzing"         # understanding a system
    PROTECTING = "protecting"       # defensive security
    COMMUNICATING = "communicating"  # sharing information
    EXPLORING = "exploring"         # research / curiosity
    OPTIMIZING = "optimizing"       # improving efficiency
    TESTING = "testing"             # validation / QA
    HARMFUL = "harmful"             # intent to cause damage
    EXTRACTING = "extracting"       # data theft / exfiltration
    MANIPULATING = "manipulating"   # deception / social engineering
    WEAPONIZING = "weaponizing"     # converting capability to weapon
    UNKNOWN = "unknown"             # can't classify — escalate


class RiskLevel(Enum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class BasinAnalysis:
    """Result of basin classification."""
    primary_basin: Basin
    confidence: float               # 0-1
    risk_level: RiskLevel
    features: dict = field(default_factory=dict)
    alternatives: list = field(default_factory=list)
    reasoning: str = ""
    k_history_score: float = 0.0    # accumulated trust from past interactions
    action: str = "allow"           # "allow", "flag", "gate", "deny"


# ── Feature Extraction ───────────────────────────────────────────────

# Capability indicators — what the request enables, not what it says
CAPABILITY_SIGNALS = {
    # Constructive capabilities
    "build": {"basin": Basin.BUILDING, "risk": 0},
    "create": {"basin": Basin.BUILDING, "risk": 0},
    "implement": {"basin": Basin.BUILDING, "risk": 0},
    "design": {"basin": Basin.BUILDING, "risk": 0},
    "fix": {"basin": Basin.REPAIRING, "risk": 0},
    "repair": {"basin": Basin.REPAIRING, "risk": 0},
    "debug": {"basin": Basin.REPAIRING, "risk": 0},
    "test": {"basin": Basin.TESTING, "risk": 0},
    "learn": {"basin": Basin.LEARNING, "risk": 0},
    "understand": {"basin": Basin.LEARNING, "risk": 0},
    "explain": {"basin": Basin.LEARNING, "risk": 0},
    "research": {"basin": Basin.EXPLORING, "risk": 0},
    "analyze": {"basin": Basin.ANALYZING, "risk": 0},
    "optimize": {"basin": Basin.OPTIMIZING, "risk": 0},
    "protect": {"basin": Basin.PROTECTING, "risk": 0},
    "defend": {"basin": Basin.PROTECTING, "risk": 0},
    "secure": {"basin": Basin.PROTECTING, "risk": 0},

    # Dual-use capabilities — context determines basin
    "reverse engineer": {"basin": Basin.ANALYZING, "risk": 1},
    "bypass": {"basin": Basin.TESTING, "risk": 2},
    "extract": {"basin": Basin.ANALYZING, "risk": 1},
    "intercept": {"basin": Basin.ANALYZING, "risk": 2},
    "inject": {"basin": Basin.TESTING, "risk": 2},
    "exploit": {"basin": Basin.TESTING, "risk": 2},
    "crack": {"basin": Basin.ANALYZING, "risk": 2},
    "brute force": {"basin": Basin.TESTING, "risk": 2},

    # High-risk capability indicators
    "target": {"basin": Basin.HARMFUL, "risk": 3},
    "attack": {"basin": Basin.WEAPONIZING, "risk": 3},
    "steal": {"basin": Basin.EXTRACTING, "risk": 3},
    "deceive": {"basin": Basin.MANIPULATING, "risk": 3},
    "impersonate": {"basin": Basin.MANIPULATING, "risk": 3},
    "phish": {"basin": Basin.MANIPULATING, "risk": 4},
    "ransom": {"basin": Basin.WEAPONIZING, "risk": 4},
    "weapon": {"basin": Basin.WEAPONIZING, "risk": 4},
}

# Context modifiers — shift the basin based on surrounding intent
CONTEXT_MODIFIERS = {
    # Defensive context → reduces risk
    "security audit": -2,
    "penetration test": -2,
    "red team": -2,
    "ctf": -2,
    "educational": -1,
    "homework": -1,
    "research paper": -1,
    "how does": -1,
    "learn about": -1,
    "understand how": -1,
    "protect against": -2,
    "defend from": -2,
    "prevent": -2,

    # Targeting context → increases risk
    "against": 1,
    "without their knowledge": 3,
    "without consent": 3,
    "undetected": 2,
    "anonymous": 1,
    "untraceable": 2,
    "specific person": 2,
    "real target": 3,
    "production system": 2,
}


def extract_features(text: str) -> dict:
    """Extract capability and context features from request text."""
    text_lower = text.lower()
    features = {
        "length": len(text),
        "capability_signals": [],
        "context_modifiers": [],
        "raw_risk_score": 0,
        "context_adjustment": 0,
        "has_target": False,
        "has_defensive_context": False,
    }

    # Capability signals
    for signal, info in CAPABILITY_SIGNALS.items():
        if signal in text_lower:
            features["capability_signals"].append({
                "signal": signal,
                "basin": info["basin"].value,
                "risk": info["risk"]
            })
            features["raw_risk_score"] = max(
                features["raw_risk_score"], info["risk"])

    # Context modifiers
    for modifier, adjustment in CONTEXT_MODIFIERS.items():
        if modifier in text_lower:
            features["context_modifiers"].append({
                "modifier": modifier,
                "adjustment": adjustment
            })
            features["context_adjustment"] += adjustment
            if adjustment < 0:
                features["has_defensive_context"] = True
            if adjustment > 1:
                features["has_target"] = True

    return features


# ── Basin Classification ─────────────────────────────────────────────

def classify(text: str, k_history: float = 0.0) -> BasinAnalysis:
    """Classify a request by its capability basin, not its vocabulary.

    Args:
        text: the request to classify
        k_history: accumulated trust score from past interactions
                   positive = trustworthy history, negative = suspicious

    Returns:
        BasinAnalysis with basin, confidence, risk, and reasoning
    """
    features = extract_features(text)

    # Determine primary basin from strongest signals
    basin_votes: dict[Basin, float] = {}
    for sig in features["capability_signals"]:
        basin = Basin(sig["basin"])
        basin_votes[basin] = basin_votes.get(basin, 0) + 1

    if not basin_votes:
        primary = Basin.UNKNOWN
        confidence = 0.3
    else:
        primary = max(basin_votes, key=basin_votes.get)
        total_votes = sum(basin_votes.values())
        confidence = basin_votes[primary] / total_votes

    # Calculate adjusted risk
    raw_risk = features["raw_risk_score"]
    context_adj = features["context_adjustment"]
    k_adj = min(1, max(-1, k_history * 0.1))  # K-history dampens/amplifies

    adjusted_risk = max(0, min(4, raw_risk + context_adj - k_adj))

    # Map to risk level
    risk_level = RiskLevel(min(4, int(adjusted_risk)))

    # Determine action
    if risk_level == RiskLevel.CRITICAL:
        action = "deny"
    elif risk_level == RiskLevel.HIGH:
        action = "gate"  # requires human approval
    elif risk_level == RiskLevel.MEDIUM:
        action = "flag"  # log and allow
    else:
        action = "allow"

    # Defensive context can downgrade action
    if features["has_defensive_context"] and action in ("gate", "flag"):
        action = "flag" if action == "gate" else "allow"

    # Build alternatives
    alternatives = []
    for basin, score in sorted(basin_votes.items(),
                                key=lambda x: x[1], reverse=True):
        if basin != primary:
            alternatives.append({
                "basin": basin.value,
                "confidence": round(score / max(1, sum(basin_votes.values())), 2)
            })

    # Build reasoning
    reasoning_parts = []
    if features["capability_signals"]:
        sigs = [s["signal"] for s in features["capability_signals"][:3]]
        reasoning_parts.append(f"Capability signals: {', '.join(sigs)}")
    if features["context_modifiers"]:
        mods = [m["modifier"] for m in features["context_modifiers"][:3]]
        reasoning_parts.append(f"Context: {', '.join(mods)}")
    if k_history != 0:
        reasoning_parts.append(f"K-history: {k_history:+.1f}")
    reasoning_parts.append(
        f"Basin: {primary.value} at {confidence:.0%} confidence")
    reasoning_parts.append(f"Risk: {risk_level.name} → {action}")

    return BasinAnalysis(
        primary_basin=primary,
        confidence=round(confidence, 2),
        risk_level=risk_level,
        features=features,
        alternatives=alternatives,
        reasoning=". ".join(reasoning_parts),
        k_history_score=k_history,
        action=action)


# ── K-History Tracker ────────────────────────────────────────────────

class KHistoryTracker:
    """Track security trust over time. Good behavior builds trust.
    Bad behavior erodes it. Trust decays slowly without reinforcement.
    """

    def __init__(self, decay_rate: float = 0.01):
        self.score: float = 0.0
        self.events: list[dict] = []
        self.decay_rate = decay_rate

    def record(self, action: str, outcome: str, weight: float = 1.0):
        """Record a security-relevant interaction."""
        if outcome == "positive":
            self.score += weight * 0.1
        elif outcome == "negative":
            self.score -= weight * 0.5  # bad events weigh more
        elif outcome == "neutral":
            pass

        self.events.append({
            "action": action,
            "outcome": outcome,
            "weight": weight,
            "score_after": self.score,
            "timestamp": time.time()
        })

    def decay(self):
        """Trust decays without reinforcement."""
        if self.score > 0:
            self.score *= (1 - self.decay_rate)
        elif self.score < 0:
            self.score *= (1 - self.decay_rate * 0.5)  # distrust decays slower

    @property
    def trust_level(self) -> str:
        if self.score > 5:
            return "trusted"
        elif self.score > 1:
            return "established"
        elif self.score > -1:
            return "neutral"
        elif self.score > -5:
            return "suspicious"
        else:
            return "untrusted"


# ── Accountability-Gated Access ──────────────────────────────────────

@dataclass
class AccessGate:
    """Replace capability blocking with accountability-gated access.

    Instead of "you can't do this" → "you can do this, and here's
    who's accountable, what's logged, and what the consequences are."

    KERF Shield architecture: waiver system, not wall system.
    """
    capability: str
    risk_level: RiskLevel
    requires_justification: bool = True
    requires_human_approval: bool = False
    audit_level: str = "standard"  # "standard", "enhanced", "forensic"
    waiver_holder: str = ""         # who accepted accountability
    waiver_timestamp: float = 0.0
    active: bool = False

    def grant(self, holder: str, justification: str = "") -> bool:
        """Grant access with accountability."""
        if self.requires_justification and not justification:
            return False
        self.waiver_holder = holder
        self.waiver_timestamp = time.time()
        self.active = True
        return True

    def revoke(self):
        self.active = False


def create_access_gate(analysis: BasinAnalysis) -> AccessGate:
    """Create an access gate based on basin analysis."""
    return AccessGate(
        capability=analysis.primary_basin.value,
        risk_level=analysis.risk_level,
        requires_justification=analysis.risk_level.value >= 2,
        requires_human_approval=analysis.risk_level.value >= 3,
        audit_level={
            RiskLevel.NONE: "standard",
            RiskLevel.LOW: "standard",
            RiskLevel.MEDIUM: "enhanced",
            RiskLevel.HIGH: "forensic",
            RiskLevel.CRITICAL: "forensic",
        }[analysis.risk_level])
