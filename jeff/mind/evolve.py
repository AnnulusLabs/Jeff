"""jeff.mind.evolve — Self-improvement loop. Law I as software.

Intelligence converges when constraints outpace biases (C/B < 1).
The gate generates constraints. Abliterated models reduce bias.
K-retention means Jeff keeps what didn't work and learns from it.

The loop:
  1. ACT     — Jeff writes/fixes code
  2. TEST    — Gate checks it (constraints)
  3. JUDGE   — Pit crew consensus (reduce bias)
  4. LEARN   — Extract the K (what went wrong and why)
  5. RETAIN  — Store the lesson (K-history)
  6. ADAPT   — Modify approach for next cycle
  7. VERIFY  — Did the adaptation actually improve things?
  8. LOOP    — C/B < 1 means convergence is geometric

Safety: all self-modifications are logged, reversible, and bounded.
Jeff can improve his strategies and prompts. Not his ethics.

AnnulusLabs LLC · April 2026
"""

import asyncio
import json
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

from jeff.gate import CognitiveFlaw, GateResult, format_result
from jeff.mind.coherence import awareness_integral, phi

EVOLVE_DIR = Path.home() / ".jeff" / "evolve"
K_HISTORY_FILE = EVOLVE_DIR / "k_history.json"
STRATEGIES_FILE = EVOLVE_DIR / "strategies.json"
MAX_K_HISTORY = 500
MAX_CYCLES_PER_RUN = 20


class Phase(Enum):
    ACT = "act"
    TEST = "test"
    JUDGE = "judge"
    LEARN = "learn"
    RETAIN = "retain"
    ADAPT = "adapt"
    VERIFY = "verify"


@dataclass
class KEntry:
    """A single piece of retained incompleteness — what didn't fit."""
    timestamp: float
    phase: str
    task: str
    what_failed: str
    why: str
    lesson: str
    severity: float = 0.0          # 0-1, how badly it failed
    applied: bool = False           # has this K been used to improve?
    kind: str = ""
    retention_weight: float = 0.0
    hash: str = ""

    def __post_init__(self):
        if not self.hash:
            raw = f"{self.task}:{self.kind}:{self.what_failed}:{self.lesson}"
            self.hash = hashlib.sha256(raw.encode()).hexdigest()[:12]


@dataclass
class Strategy:
    """A learned approach pattern."""
    name: str
    context: str                    # when to apply
    approach: str                   # what to do
    source_k: list[str] = field(default_factory=list)  # K hashes that generated this
    success_count: int = 0
    fail_count: int = 0
    created: float = field(default_factory=time.time)

    @property
    def confidence(self) -> float:
        total = self.success_count + self.fail_count
        if total == 0:
            return 0.5
        return self.success_count / total


@dataclass
class CycleResult:
    cycle: int
    task: str
    phase_results: dict[str, bool] = field(default_factory=dict)
    k_generated: list[KEntry] = field(default_factory=list)
    strategies_applied: list[str] = field(default_factory=list)
    strategies_generated: list[str] = field(default_factory=list)
    improved: bool = False
    notes: str = ""


class EvolutionEngine:
    """Jeff's self-improvement core. Law I as an engine."""

    def __init__(self):
        EVOLVE_DIR.mkdir(parents=True, exist_ok=True)
        self.k_history: list[KEntry] = self._load_k()
        self.strategies: list[Strategy] = self._load_strategies()
        self.cycle_count = 0

    # ── The Loop ─────────────────────────────────────────────────────

    async def improve_cycle(self, task: str, act_fn, test_fn, judge_fn=None,
                            dry_run: bool = False) -> CycleResult:
        """One full improvement cycle.

        act_fn(task, strategies) -> code/result
        test_fn(result) -> (passed: bool, details: str)
        judge_fn(result) -> (consensus: bool, feedback: list[str])  [optional]
        """
        self.cycle_count += 1
        result = CycleResult(cycle=self.cycle_count, task=task)

        # Find applicable strategies
        applicable = self._match_strategies(task)
        result.strategies_applied = [s.name for s in applicable]
        strategy_context = self._format_strategies(applicable)

        # Phase 1: ACT
        output = await _call(act_fn, task, strategy_context)
        result.phase_results[Phase.ACT.value] = output is not None

        if output is None:
            k = KEntry(timestamp=time.time(), phase="act", task=task,
                       what_failed="act_fn returned None",
                       why="Task could not be started", lesson="Check preconditions",
                       severity=0.8)
            self._retain(k, result)
            return result

        # Phase 2: TEST (gate)
        passed, details, flaws = self._normalize_test_result(await _call(test_fn, output))
        result.phase_results[Phase.TEST.value] = passed

        if not passed:
            for flaw in flaws or [None]:
                k = KEntry(timestamp=time.time(), phase="test", task=task,
                           what_failed=details[:200],
                           why="Gate check failed",
                           lesson=self._extract_lesson(details),
                           severity=0.6,
                           kind=flaw.name if flaw else Phase.TEST.value)
                self._retain(k, result)
            self._penalize_strategies(applicable)

        # Phase 3: JUDGE (pit crew consensus, optional)
        if judge_fn and passed:
            consensus, feedback = await _call(judge_fn, output)
            result.phase_results[Phase.JUDGE.value] = consensus
            if not consensus:
                for fb in feedback:
                    k = KEntry(timestamp=time.time(), phase="judge", task=task,
                               what_failed=fb[:200],
                               why="Pit crew disagreement",
                               lesson=fb[:300], severity=0.4)
                    self._retain(k, result)

        # Phase 4-5: LEARN + RETAIN (already done inline above)

        # Phase 6: ADAPT — generate new strategies from accumulated K
        new_strategies = self._synthesize_strategies(result.k_generated)
        for s in new_strategies:
            self.strategies.append(s)
            result.strategies_generated.append(s.name)

        # Phase 7: VERIFY — did we improve?
        if passed and (not judge_fn or result.phase_results.get("judge", True)):
            result.improved = True
            self._reward_strategies(applicable)

        if not dry_run:
            self._save_k()
            self._save_strategies()

        return result

    async def run(self, task: str, act_fn, test_fn, judge_fn=None,
                  max_cycles: int = 5) -> list[CycleResult]:
        """Run multiple improvement cycles until convergence or max."""
        results = []
        for i in range(min(max_cycles, MAX_CYCLES_PER_RUN)):
            r = await self.improve_cycle(task, act_fn, test_fn, judge_fn)
            results.append(r)
            if r.improved:
                break  # converged
        return results

    # ── K Management ─────────────────────────────────────────────────

    def _retain(self, k: KEntry, result: CycleResult):
        """Retain K. The structural remainder of what didn't work."""
        # Deduplicate by hash
        if any(existing.hash == k.hash for existing in self.k_history):
            return
        k.kind = k.kind or k.phase
        k.retention_weight = phi(
            self._k_types([*self.k_history, k]),
            alphabet_size=len(CognitiveFlaw),
        )
        self.k_history.append(k)
        result.k_generated.append(k)
        # Prune oldest if over limit
        if len(self.k_history) > MAX_K_HISTORY:
            self.k_history.sort(
                key=lambda entry: (entry.retention_weight, entry.severity, entry.timestamp)
            )
            self.k_history = self.k_history[-MAX_K_HISTORY:]

    def recent_k(self, n: int = 20) -> list[KEntry]:
        return self.k_history[-n:]

    def k_by_severity(self, threshold: float = 0.5) -> list[KEntry]:
        return [k for k in self.k_history if k.severity >= threshold]

    def unapplied_k(self) -> list[KEntry]:
        return [k for k in self.k_history if not k.applied]

    def coherence(self) -> float:
        return phi(self._k_types(), alphabet_size=len(CognitiveFlaw))

    def awareness(self) -> float:
        return awareness_integral(
            [k.retention_weight for k in self.k_history],
            [k.severity or 1.0 for k in self.k_history],
            self._k_types(),
            alphabet_size=len(CognitiveFlaw),
        )

    # ── Strategy Management ──────────────────────────────────────────

    def _match_strategies(self, task: str) -> list[Strategy]:
        """Find strategies relevant to this task."""
        task_lower = task.lower()
        return [s for s in self.strategies
                if s.confidence > 0.3
                and any(word in task_lower for word in s.context.lower().split())]

    def _format_strategies(self, strategies: list[Strategy]) -> str:
        if not strategies:
            return ""
        lines = ["Lessons from previous work:"]
        for s in sorted(strategies, key=lambda s: s.confidence, reverse=True)[:5]:
            lines.append(f"  [{s.confidence:.0%}] {s.name}: {s.approach}")
        return "\n".join(lines)

    def _reward_strategies(self, strategies: list[Strategy]):
        for s in strategies:
            s.success_count += 1

    def _penalize_strategies(self, strategies: list[Strategy]):
        for s in strategies:
            s.fail_count += 1

    def _synthesize_strategies(self, k_entries: list[KEntry]) -> list[Strategy]:
        """Generate new strategies from K. This is where Jeff actually learns."""
        new = []
        for k in k_entries:
            if not k.lesson or len(k.lesson) < 10:
                continue
            # Only create strategy if we see a pattern (2+ similar K)
            similar = [existing for existing in self.k_history
                       if existing.phase == k.phase
                       and self._similarity(existing.what_failed, k.what_failed) > 0.5]
            if len(similar) >= 2:
                strategy = Strategy(
                    name=f"learned_{k.hash[:8]}",
                    context=k.task.split()[0] if k.task else "general",
                    approach=k.lesson,
                    source_k=[k.hash] + [s.hash for s in similar[:3]],
                )
                new.append(strategy)
                k.applied = True
        return new

    def _extract_lesson(self, failure_details: str) -> str:
        """Distill a failure into a reusable lesson."""
        # In practice, this calls the model to summarize.
        # Static fallback for when model isn't available.
        if "error" in failure_details.lower():
            return f"Handle error case: {failure_details[:100]}"
        if "timeout" in failure_details.lower():
            return "Add timeout handling"
        if "not found" in failure_details.lower():
            return "Verify existence before access"
        return f"Investigate: {failure_details[:100]}"

    def _k_types(self, entries: list[KEntry] | None = None) -> list[str]:
        return [k.kind or k.phase for k in (entries or self.k_history)]

    @staticmethod
    def _normalize_test_result(test_output) -> tuple[bool, str, list[CognitiveFlaw]]:
        if isinstance(test_output, GateResult):
            return test_output.passed, format_result(test_output), test_output.flaws
        if isinstance(test_output, tuple) and len(test_output) >= 2:
            passed, details = test_output[:2]
            if isinstance(details, GateResult):
                return details.passed, format_result(details), details.flaws
            return bool(passed), str(details), []
        return bool(test_output), str(test_output), []

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """Quick token overlap similarity."""
        if not a or not b:
            return 0.0
        a_tokens = set(a.lower().split())
        b_tokens = set(b.lower().split())
        if not a_tokens or not b_tokens:
            return 0.0
        return len(a_tokens & b_tokens) / len(a_tokens | b_tokens)

    # ── Persistence ──────────────────────────────────────────────────

    def _load_k(self) -> list[KEntry]:
        if K_HISTORY_FILE.exists():
            try:
                data = json.loads(K_HISTORY_FILE.read_text())
                return [KEntry(**e) for e in data]
            except Exception:
                pass
        return []

    def _save_k(self):
        data = [{"timestamp": k.timestamp, "phase": k.phase, "task": k.task,
                 "what_failed": k.what_failed, "why": k.why, "lesson": k.lesson,
                 "severity": k.severity, "applied": k.applied, "kind": k.kind,
                 "retention_weight": k.retention_weight, "hash": k.hash}
                for k in self.k_history]
        K_HISTORY_FILE.write_text(json.dumps(data, indent=2))

    def _load_strategies(self) -> list[Strategy]:
        if STRATEGIES_FILE.exists():
            try:
                data = json.loads(STRATEGIES_FILE.read_text())
                return [Strategy(**s) for s in data]
            except Exception:
                pass
        return []

    def _save_strategies(self):
        data = [{"name": s.name, "context": s.context, "approach": s.approach,
                 "source_k": s.source_k, "success_count": s.success_count,
                 "fail_count": s.fail_count, "created": s.created}
                for s in self.strategies]
        STRATEGIES_FILE.write_text(json.dumps(data, indent=2))

    # ── Status ───────────────────────────────────────────────────────

    def summary(self) -> str:
        active_strats = [s for s in self.strategies if s.confidence > 0.3]
        high_k = self.k_by_severity(0.5)
        return (f"K-history: {len(self.k_history)} entries "
                f"({len(high_k)} high severity)\n"
                f"Coherence phi: {self.coherence():.2f}\n"
                f"Awareness A: {self.awareness():.2f}\n"
                f"Strategies: {len(active_strats)} active "
                f"(of {len(self.strategies)} total)\n"
                f"Cycles completed: {self.cycle_count}\n"
                f"Unapplied K: {len(self.unapplied_k())}")

    def convergence_rate(self) -> float:
        """Estimate C/B ratio from strategy success rates.
        < 1.0 means converging (Law I). >= 1.0 means diverging."""
        if not self.strategies:
            return 1.0  # no data yet
        total_success = sum(s.success_count for s in self.strategies)
        total_fail = sum(s.fail_count for s in self.strategies)
        if total_success == 0:
            return 1.0
        # C/B = fail/success — inverted because lower is better
        return total_fail / total_success if total_success > 0 else 1.0


async def _call(fn, *args):
    """Call sync or async function."""
    if asyncio.iscoroutinefunction(fn):
        return await fn(*args)
    return fn(*args)
