"""jeff.mind.learn — Continual learning with anti-catastrophic forgetting.

Ported from NOX kerf/mind/learn.py. Strips the ternary gene substrate
and replaces resonance scoring with token-based cosine similarity — no
numpy, no external deps, pure stdlib.

Core mechanisms:
- Elastic Weight Consolidation analog: high-accuracy skills with many
  examples resist overwrite proportional to their reliability.
- Ring buffer per skill with failure-priority eviction (failures carry
  more learning signal than successes).
- Drift detection via sliding window over recent examples — triggers
  alerts when recent accuracy drops vs overall accuracy.
- Rehearsal: weighted sampling of old examples across all skills to
  keep dormant knowledge accessible.
- Consolidation: merge similar skills into the higher-importance one.

AnnulusLabs LLC · April 2026
"""

from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass, field
from typing import Any

_MAX_EXAMPLES = 100
_DRIFT_WINDOW = 20
_DRIFT_THRESHOLD = 0.2
_MERGE_THRESHOLD = 0.8
_EWC_FLOOR = 0.1


@dataclass
class Skill:
    """A learned capability with examples and accuracy tracking."""
    name: str
    tokens: set[str] = field(default_factory=set)
    examples: list[str] = field(default_factory=list)
    outcomes: list[bool] = field(default_factory=list)
    accuracy: float = 0.0
    created: float = 0.0
    last_used: float = 0.0
    active: bool = True

    @property
    def total(self) -> int:
        return len(self.outcomes)

    @property
    def correct(self) -> int:
        return sum(self.outcomes)

    @property
    def importance(self) -> float:
        """Elastic weight consolidation analog.

        High-accuracy skills with many examples are harder to overwrite.
        Returns a value in [_EWC_FLOOR, 1.0].
        """
        if self.total == 0:
            return _EWC_FLOOR
        reliability = self.accuracy * min(self.total / 20.0, 1.0)
        return max(reliability, _EWC_FLOOR)


def _tokenize(text: str) -> set[str]:
    """Simple token set for cosine-style similarity."""
    return set(re.findall(r"[a-z0-9_]+", text.lower()))


def _similarity(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between token sets."""
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def _push_example(skill: Skill, example: str, correct: bool) -> None:
    """Add example to ring buffer with failure-priority eviction."""
    if len(skill.examples) >= _MAX_EXAMPLES:
        # Evict oldest correct example first (failures carry more signal).
        for i, ok in enumerate(skill.outcomes):
            if ok:
                skill.examples.pop(i)
                skill.outcomes.pop(i)
                break
        else:
            # No correct examples to evict — drop oldest.
            skill.examples.pop(0)
            skill.outcomes.pop(0)
    skill.examples.append(example)
    skill.outcomes.append(correct)


def _update_accuracy(skill: Skill) -> None:
    if not skill.outcomes:
        skill.accuracy = 0.0
        return
    skill.accuracy = sum(skill.outcomes) / len(skill.outcomes)


class ContinualLearner:
    """Grows skills over time without catastrophic forgetting.

    Each skill is a named capability with examples, a token set for
    similarity retrieval, and accuracy tracking with drift detection.
    """

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}
        self._error_counts: dict[str, int] = {}

    # ── Core API ──────────────────────────────────────────────────

    def learn(self, skill_name: str, example: str, correct: bool) -> Skill:
        """Record an example for a skill. Creates the skill if new."""
        now = time.time()
        skill = self._skills.get(skill_name)

        if skill is None:
            skill = Skill(
                name=skill_name,
                tokens=_tokenize(skill_name + " " + example),
                created=now,
                last_used=now,
            )
            self._skills[skill_name] = skill
        else:
            # Add new example tokens to the skill's token set for retrieval.
            skill.tokens.update(_tokenize(example))

        _push_example(skill, example, correct)
        _update_accuracy(skill)
        skill.last_used = now
        skill.active = True
        return skill

    def recall(self, query: str) -> list[tuple[Skill, float]]:
        """Find skills relevant to query via token similarity.

        Returns (skill, similarity) pairs sorted by descending similarity.
        Only active skills are returned.
        """
        qtokens = _tokenize(query)
        results: list[tuple[Skill, float]] = []
        for skill in self._skills.values():
            if not skill.active:
                continue
            sim = _similarity(qtokens, skill.tokens)
            if sim > 0:
                results.append((skill, sim))
        results.sort(key=lambda pair: pair[1], reverse=True)
        return results

    def consolidate(self) -> list[tuple[str, str]]:
        """Merge similar skills. Higher-importance skill survives.

        Returns list of (absorbed_name, into_name) pairs.
        """
        active = [s for s in self._skills.values() if s.active]
        merged: list[tuple[str, str]] = []
        absorbed: set[str] = set()

        for i, a in enumerate(active):
            if a.name in absorbed:
                continue
            for b in active[i + 1:]:
                if b.name in absorbed:
                    continue
                sim = _similarity(a.tokens, b.tokens)
                if sim < _MERGE_THRESHOLD:
                    continue
                # Higher importance survives.
                if a.importance >= b.importance:
                    winner, loser = a, b
                else:
                    winner, loser = b, a
                # Absorb examples (respect ring buffer cap).
                for ex, ok in zip(loser.examples, loser.outcomes):
                    _push_example(winner, ex, ok)
                winner.tokens.update(loser.tokens)
                _update_accuracy(winner)
                loser.active = False
                absorbed.add(loser.name)
                merged.append((loser.name, winner.name))
        return merged

    def detect_drift(self, skill_name: str) -> float:
        """Compare recent accuracy to overall accuracy.

        Returns drift magnitude in [0, 1]. 0 = stable, 1 = collapse.
        Values above _DRIFT_THRESHOLD indicate meaningful drift.
        """
        skill = self._skills.get(skill_name)
        if skill is None or skill.total < _DRIFT_WINDOW:
            return 0.0
        recent = skill.outcomes[-_DRIFT_WINDOW:]
        recent_acc = sum(recent) / len(recent)
        overall_acc = skill.accuracy
        drift = max(overall_acc - recent_acc, 0.0)
        return min(drift / max(overall_acc, 1e-9), 1.0)

    def forget(self, skill_name: str) -> bool:
        """Graceful forgetting — mark inactive, preserve data."""
        skill = self._skills.get(skill_name)
        if skill is None:
            return False
        skill.active = False
        return True

    def rehearse(self, n: int = 5) -> list[str]:
        """Sample n random examples weighted toward stale skills."""
        pool: list[tuple[str, float]] = []
        now = time.time()
        for skill in self._skills.values():
            if not skill.active or not skill.examples:
                continue
            staleness = now - skill.last_used + 1.0
            for ex in skill.examples:
                pool.append((ex, staleness))
        if not pool:
            return []
        n = min(n, len(pool))
        weights = [w for _, w in pool]
        total_w = sum(weights)
        if total_w == 0:
            indices = random.sample(range(len(pool)), n)
        else:
            probs = [w / total_w for w in weights]
            indices = _weighted_sample(probs, n)
        return [pool[i][0] for i in indices]

    def skills_report(self) -> dict[str, Any]:
        """Summary statistics across all skills."""
        all_skills = list(self._skills.values())
        active = [s for s in all_skills if s.active]
        inactive = [s for s in all_skills if not s.active]
        accuracies = [s.accuracy for s in active if s.total > 0]
        avg_acc = sum(accuracies) / len(accuracies) if accuracies else 0.0
        drift_alerts = []
        for s in active:
            d = self.detect_drift(s.name)
            if d > _DRIFT_THRESHOLD:
                drift_alerts.append({"skill": s.name, "drift": round(d, 4)})
        return {
            "total_skills": len(all_skills),
            "active": len(active),
            "inactive": len(inactive),
            "avg_accuracy": round(avg_acc, 4),
            "total_examples": sum(s.total for s in all_skills),
            "drift_alerts": drift_alerts,
        }

    # ── Error learning ────────────────────────────────────────────

    ERROR_PATTERNS: dict[str, str] = {
        r"NameError: name '(\w+)' is not defined": "undefined_variable",
        r"ImportError: No module named '(\w+)'": "missing_import",
        r"AttributeError: '(\w+)' object has no attribute '(\w+)'": "wrong_attribute",
        r"TypeError: (\w+)\(\) takes (\d+) positional arguments but (\d+) were given": "wrong_args",
        r"IndentationError": "indentation",
        r"SyntaxError": "syntax",
        r"KeyError: '(\w+)'": "missing_key",
        r"IndexError: list index out of range": "index_bounds",
        r"FileNotFoundError": "missing_file",
        r"ZeroDivisionError": "division_zero",
        r"RecursionError": "infinite_recursion",
        r"MemoryError": "out_of_memory",
        r"TimeoutError": "timeout",
        r"ConnectionError": "network_issue",
    }

    def error_signature(self, error_type: str, error_msg: str) -> str:
        """Create a normalized error signature that generalizes across files."""
        normalized = re.sub(r"line \d+", "line N", error_msg)
        normalized = re.sub(r'"[^"]*\.py"', '"file.py"', normalized)
        normalized = re.sub(r"'[^']*\.py'", "'file.py'", normalized)
        normalized = re.sub(r"0x[0-9a-fA-F]+", "0xADDR", normalized)
        return f"{error_type}:{normalized[:200]}"

    def learn_from_error(self, error_type: str, error_msg: str) -> str:
        """Classify an error into a known category and record it."""
        for pattern, category in self.ERROR_PATTERNS.items():
            if re.search(pattern, error_msg):
                sig = self.error_signature(error_type, error_msg)
                self._error_counts[category] = self._error_counts.get(category, 0) + 1
                self.learn(
                    skill_name=f"error:{category}",
                    example=sig,
                    correct=False,
                )
                return category
        return "unknown"

    def error_frequency(self) -> dict[str, int]:
        """Return error counts by category."""
        return dict(self._error_counts)


def _weighted_sample(probs: list[float], n: int) -> list[int]:
    """Weighted sampling without replacement."""
    remaining = list(enumerate(probs))
    picked: list[int] = []
    for _ in range(n):
        if not remaining:
            break
        total = sum(p for _, p in remaining)
        if total == 0:
            idx, _ = remaining.pop(random.randrange(len(remaining)))
            picked.append(idx)
            continue
        r = random.uniform(0, total)
        acc = 0.0
        for i, (orig_idx, p) in enumerate(remaining):
            acc += p
            if acc >= r:
                picked.append(orig_idx)
                remaining.pop(i)
                break
    return picked
