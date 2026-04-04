"""jeff.mind.deadends — Failed path memory.

If a specific logic branch hits the gate and fails twice, Jeff is
forbidden from attempting that approach again in the same session.

"I tried that. It didn't work. Moving on."

Gripe #28: AI tries the same failing solution five times in a row.

AnnulusLabs LLC · April 2026
"""

import hashlib
import time
from dataclasses import dataclass, field


@dataclass
class DeadEnd:
    approach_hash: str
    description: str
    failure_reason: str
    attempts: int = 1
    first_failed: float = field(default_factory=time.time)
    last_failed: float = field(default_factory=time.time)


class DeadEndTracker:
    """Remembers what didn't work. Prevents loops."""

    def __init__(self, max_attempts: int = 2, ttl_hours: float = 24.0):
        self.max_attempts = max_attempts
        self.ttl = ttl_hours * 3600
        self.dead_ends: dict[str, DeadEnd] = {}  # hash → DeadEnd
        self.session_bans: set[str] = set()       # hashes banned this session

    def _hash(self, approach: str) -> str:
        """Hash the approach description to detect similar attempts."""
        normalized = " ".join(approach.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:12]

    def record_failure(self, approach: str, reason: str) -> DeadEnd:
        """Record a failed approach. Returns the DeadEnd entry."""
        h = self._hash(approach)

        if h in self.dead_ends:
            de = self.dead_ends[h]
            de.attempts += 1
            de.last_failed = time.time()
            de.failure_reason = reason
        else:
            de = DeadEnd(approach_hash=h, description=approach,
                        failure_reason=reason)
            self.dead_ends[h] = de

        if de.attempts >= self.max_attempts:
            self.session_bans.add(h)

        return de

    def is_banned(self, approach: str) -> bool:
        """Check if this approach has been banned."""
        h = self._hash(approach)
        if h in self.session_bans:
            de = self.dead_ends.get(h)
            if de and (time.time() - de.last_failed) > self.ttl:
                self.session_bans.discard(h)
                return False
            return True
        return False

    def check(self, approach: str) -> dict:
        """Check an approach before attempting it."""
        h = self._hash(approach)
        if h in self.session_bans:
            de = self.dead_ends[h]
            return {
                "allowed": False,
                "reason": f"Dead end: tried {de.attempts} times. "
                          f"Last failure: {de.failure_reason}",
                "suggestion": "Try a different approach."
            }
        if h in self.dead_ends:
            de = self.dead_ends[h]
            return {
                "allowed": True,
                "warning": f"Previously failed {de.attempts} time(s): "
                          f"{de.failure_reason}. "
                          f"{self.max_attempts - de.attempts} attempt(s) remaining."
            }
        return {"allowed": True}

    def alternatives(self, banned_approach: str) -> str:
        """Suggest: you tried X and it failed. What else?"""
        h = self._hash(banned_approach)
        de = self.dead_ends.get(h)
        if not de:
            return "No history for this approach."
        return (f"Banned: {de.description}\n"
                f"Reason: {de.failure_reason}\n"
                f"Attempts: {de.attempts}\n"
                f"Try a structurally different approach.")

    def clear_session(self):
        """Reset session bans. Dead ends remain in memory."""
        self.session_bans.clear()

    def summary(self) -> str:
        banned = len(self.session_bans)
        total = len(self.dead_ends)
        lines = [f"DEAD ENDS: {total} tracked, {banned} banned this session"]
        for h, de in self.dead_ends.items():
            status = "BANNED" if h in self.session_bans else "warned"
            lines.append(f"  [{status:<6s}] {de.description[:50]} "
                        f"({de.attempts}x: {de.failure_reason[:40]})")
        return "\n".join(lines)
