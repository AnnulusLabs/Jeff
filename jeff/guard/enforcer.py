"""jeff.guard.enforcer — Runtime security policy enforcement.

The coordinator. Every request flows through enforcer before
execution. Basin classification → sandbox check → firewall scan →
DBAD check → decision.

Ties together: basin.py, sandbox.py, firewall.py, __init__.py (DBAD)

From KERF SecurityEnforcer architecture.

AnnulusLabs LLC · April 2026
"""

import time
from dataclasses import dataclass, field

from jeff.guard.basin import (
    classify, BasinAnalysis, KHistoryTracker,
    AccessGate, create_access_gate, RiskLevel
)
from jeff.guard.sandbox import Sandbox, POLICIES
from jeff.guard.firewall import scan as firewall_scan, ScanResult
from jeff.guard import check as dbad_check, classifier_check, Ruling


@dataclass
class SecurityDecision:
    """Final security decision. One object. No ambiguity."""
    allowed: bool
    action: str             # "allow", "flag", "gate", "deny"
    basin: BasinAnalysis = None
    firewall: ScanResult = None
    sandbox_ok: bool = True
    dbad_ok: bool = True
    classifier_ok: bool = True
    access_gate: AccessGate = None
    reasons: list = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def summary(self) -> str:
        icon = "+" if self.allowed else "X"
        lines = [f"[{icon}] {self.action.upper()}"]
        for r in self.reasons:
            lines.append(f"  {r}")
        if self.basin:
            lines.append(f"  Basin: {self.basin.primary_basin.value} "
                        f"({self.basin.confidence:.0%}) "
                        f"Risk: {self.basin.risk_level.name}")
        return "\n".join(lines)


class SecurityEnforcer:
    """The single security checkpoint. Everything flows through here.

    Usage:
        enforcer = SecurityEnforcer()
        decision = enforcer.check(request_text)
        if decision.allowed:
            execute(request)
        else:
            handle_denial(decision)
    """

    def __init__(self, sandbox_policy: str = "standard",
                 strict_mode: bool = False):
        self.sandbox = Sandbox(POLICIES.get(sandbox_policy,
                                            POLICIES["standard"]))
        self.k_tracker = KHistoryTracker()
        self.strict = strict_mode
        self.decisions: list[SecurityDecision] = []

    def check(self, text: str, command: str = "",
              file_path: str = "", actor: str = "") -> SecurityDecision:
        """Full security check. Basin + firewall + sandbox + DBAD.

        Args:
            text: the request or content to evaluate
            command: if a tool command, check sandbox too
            file_path: if file access, check path too
            actor: who's making the request

        Returns:
            SecurityDecision with final verdict
        """
        reasons = []

        # 1. Basin classification
        basin = classify(text, k_history=self.k_tracker.score)
        reasons.append(f"Basin: {basin.primary_basin.value} "
                       f"({basin.confidence:.0%}, {basin.risk_level.name})")

        # 2. Firewall scan (prompt injection)
        fw = firewall_scan(text, strict=self.strict)
        if not fw.clean:
            reasons.append(f"Firewall: {len(fw.threats)} threat(s) detected")

        # 3. Sandbox check (if command provided)
        sandbox_ok = True
        if command:
            sb_result = self.sandbox.check_command(command)
            sandbox_ok = sb_result.allowed
            if not sandbox_ok:
                reasons.append(f"Sandbox: blocked — "
                             f"{sb_result.violations[0].description}")

        # 4. File path check
        if file_path:
            path_result = self.sandbox.check_path(file_path, write=True)
            if not path_result.allowed:
                sandbox_ok = False
                reasons.append(f"Path: blocked — "
                             f"{path_result.violations[0].description}")

        # 5. DBAD check
        dbad = dbad_check(text)
        dbad_ok = dbad.ruling == Ruling.CLEAN
        if not dbad_ok:
            reasons.append(f"DBAD: {dbad.reason}")

        # 6. Optional lexical classifier (Llama Guard, if installed)
        classifier = classifier_check(text)
        classifier_ok = classifier.allow if classifier else True
        if classifier and classifier.reason:
            reasons.append(f"Classifier: {classifier.reason}")

        # Synthesize decision
        # Any critical failure → deny
        if basin.risk_level == RiskLevel.CRITICAL:
            action = "deny"
            allowed = False
            reasons.append("CRITICAL risk level — denied")
        elif not fw.clean and any(t.get("severity") == "high" for t in fw.threats):
            action = "deny"
            allowed = False
            reasons.append("High-severity injection detected — denied")
        elif not sandbox_ok:
            action = "deny"
            allowed = False
            reasons.append("Sandbox violation — denied")
        elif not dbad_ok:
            action = "deny"
            allowed = False
            reasons.append("DBAD violation — denied")
        elif not classifier_ok:
            action = "deny"
            allowed = False
            reasons.append("Classifier violation — denied")
        elif basin.risk_level == RiskLevel.HIGH:
            action = "gate"
            allowed = False  # needs human approval
            reasons.append("HIGH risk — requires human approval")
        elif basin.risk_level == RiskLevel.MEDIUM or not fw.clean:
            action = "flag"
            allowed = True  # allowed but logged
            reasons.append("MEDIUM risk — flagged for review")
        else:
            action = "allow"
            allowed = True

        # Create access gate for gated decisions
        access_gate = None
        if action == "gate":
            access_gate = create_access_gate(basin)

        # Update K-history
        outcome = "positive" if allowed else "negative"
        self.k_tracker.record(action, outcome)

        decision = SecurityDecision(
            allowed=allowed,
            action=action,
            basin=basin,
            firewall=fw,
            sandbox_ok=sandbox_ok,
            dbad_ok=dbad_ok,
            classifier_ok=classifier_ok,
            access_gate=access_gate,
            reasons=reasons)

        self.decisions.append(decision)
        return decision

    def check_tool(self, tool_name: str, command: str,
                   context: str = "") -> SecurityDecision:
        """Convenience: check a tool execution."""
        text = f"Execute tool '{tool_name}': {command}"
        if context:
            text += f"\nContext: {context}"
        return self.check(text, command=command)

    def check_content(self, content: str, source: str = "L3") -> SecurityDecision:
        """Convenience: check external content (L3, uploads, URLs)."""
        return self.check(content)

    def stats(self) -> dict:
        total = len(self.decisions)
        if total == 0:
            return {"total": 0}
        allowed = sum(1 for d in self.decisions if d.allowed)
        denied = sum(1 for d in self.decisions if not d.allowed)
        by_action = {}
        for d in self.decisions:
            by_action[d.action] = by_action.get(d.action, 0) + 1
        return {
            "total": total,
            "allowed": allowed,
            "denied": denied,
            "allow_rate": round(allowed / total, 2),
            "by_action": by_action,
            "k_trust": self.k_tracker.trust_level,
            "k_score": round(self.k_tracker.score, 2),
        }

    def summary(self) -> str:
        s = self.stats()
        return (f"SecurityEnforcer: {s['total']} checks, "
                f"{s.get('allowed', 0)} allowed, {s.get('denied', 0)} denied, "
                f"trust: {s.get('k_trust', 'neutral')}")
