"""jeff.mind.instincts — Instinct graph with confidence decay.

Instincts are learned behaviors stored as nodes in a queryable graph
with automatic confidence decay (30-day half-life), reinforcement from
repeated observations, contradiction detection, cross-model portability,
and project scoping with promotion to global after N projects observe
the same pattern.

Ported from NOX kerf/mind/instincts.py. Zero KERF dependencies — pure
stdlib Python. Earns its place at 200 lines.

AnnulusLabs LLC · April 2026
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Iterator


class InstinctScope(Enum):
    PROJECT = auto()
    GLOBAL = auto()


class InstinctDomain(Enum):
    CODE_STYLE = auto()
    TESTING = auto()
    DEBUGGING = auto()
    GIT = auto()
    WORKFLOW = auto()
    SECURITY = auto()
    PERFORMANCE = auto()
    ARCHITECTURE = auto()
    GENERAL = auto()


@dataclass
class Instinct:
    """An atomic learned behavior with confidence scoring."""
    id: str
    trigger: str
    action: str
    domain: InstinctDomain = InstinctDomain.GENERAL
    scope: InstinctScope = InstinctScope.PROJECT
    project_id: str = ""
    confidence: float = 0.5
    observations: int = 1
    reinforcements: int = 0
    contradictions: int = 0
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    last_reinforced: float = 0.0
    evidence: list[str] = field(default_factory=list)
    source_models: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)

    @property
    def effective_confidence(self) -> float:
        """Confidence after exponential decay (half-life 30 days)."""
        days_since_seen = (time.time() - self.last_seen) / 86400
        decay = math.exp(-0.693 * days_since_seen / 30.0)
        return self.confidence * decay

    def reinforce(self, evidence: str = "", model_id: str = "") -> None:
        self.reinforcements += 1
        self.observations += 1
        self.last_seen = time.time()
        self.last_reinforced = time.time()
        if evidence:
            self.evidence.append(evidence[:500])
        if model_id:
            self.source_models.add(model_id)
        self.confidence = min(0.95, self.confidence + 0.05 * (1 - self.confidence))

    def contradict(self, evidence: str = "") -> None:
        self.contradictions += 1
        self.last_seen = time.time()
        if evidence:
            self.evidence.append(f"[CONTRADICTION] {evidence[:500]}")
        self.confidence = max(0.1, self.confidence - 0.15)

    def promote_to_global(self) -> None:
        self.scope = InstinctScope.GLOBAL
        self.project_id = ""


class InstinctGraph:
    """Queryable graph of learned instincts with O(1) lookup and domain filtering."""

    def __init__(self):
        self._instincts: dict[str, Instinct] = {}
        self._by_project: dict[str, set[str]] = {}
        self._by_domain: dict[InstinctDomain, set[str]] = {}
        self._global: set[str] = set()

    def observe(
        self, trigger: str, action: str,
        domain: InstinctDomain = InstinctDomain.GENERAL,
        project_id: str = "", evidence: str = "", model_id: str = "",
    ) -> Instinct:
        """Record an observation. Creates or reinforces matching instinct."""
        inst_id = self._make_id(trigger, action, project_id)
        if inst_id in self._instincts:
            inst = self._instincts[inst_id]
            inst.reinforce(evidence, model_id)
            return inst

        inst = Instinct(
            id=inst_id, trigger=trigger, action=action, domain=domain,
            scope=InstinctScope.PROJECT if project_id else InstinctScope.GLOBAL,
            project_id=project_id,
            evidence=[evidence] if evidence else [],
            source_models={model_id} if model_id else set(),
        )
        self._instincts[inst_id] = inst
        self._index(inst)
        return inst

    def active_for(
        self, project_id: str = "", domain: InstinctDomain | None = None,
        min_confidence: float = 0.5, limit: int = 50,
    ) -> list[Instinct]:
        """Get active instincts above confidence threshold."""
        candidates: set[str] = set()
        if project_id and project_id in self._by_project:
            candidates.update(self._by_project[project_id])
        candidates.update(self._global)
        if domain and domain in self._by_domain:
            candidates = candidates.intersection(self._by_domain[domain])

        result = []
        for inst_id in candidates:
            inst = self._instincts.get(inst_id)
            if inst and inst.effective_confidence >= min_confidence:
                result.append(inst)
        result.sort(key=lambda i: i.effective_confidence, reverse=True)
        return result[:limit]

    def compile_for_context(
        self, project_id: str = "", min_confidence: float = 0.5,
        max_tokens: int = 2000,
    ) -> list[dict[str, Any]]:
        """Compile active instincts for prompt injection, budgeted by tokens."""
        instincts = self.active_for(project_id=project_id, min_confidence=min_confidence)
        compiled = []
        token_count = 0
        for inst in instincts:
            entry = {
                "id": inst.id, "trigger": inst.trigger,
                "action": inst.action,
                "confidence": round(inst.effective_confidence, 2),
                "domain": inst.domain.name.lower(),
            }
            est_tokens = (len(inst.trigger) + len(inst.action)) // 4 + 20
            if token_count + est_tokens > max_tokens:
                break
            compiled.append(entry)
            token_count += est_tokens
        return compiled

    def promote_if_eligible(self, min_projects: int = 2) -> list[Instinct]:
        """Promote project instincts to global after N projects observe them."""
        pattern_projects: dict[str, set[str]] = {}
        for inst in self._instincts.values():
            if inst.scope == InstinctScope.PROJECT and inst.project_id:
                key = f"{inst.trigger}|{inst.action}"
                if key not in pattern_projects:
                    pattern_projects[key] = set()
                pattern_projects[key].add(inst.project_id)

        promoted = []
        for key, projects in pattern_projects.items():
            if len(projects) >= min_projects:
                trigger, action = key.split("|", 1)
                global_inst = self.observe(
                    trigger=trigger, action=action, project_id="",
                    evidence=f"Promoted: seen in {len(projects)} projects",
                )
                global_inst.promote_to_global()
                promoted.append(global_inst)
        return promoted

    def garbage_collect(self, min_confidence: float = 0.1) -> int:
        """Remove instincts that have decayed below threshold."""
        to_remove = [
            inst_id for inst_id, inst in self._instincts.items()
            if inst.effective_confidence < min_confidence
        ]
        for inst_id in to_remove:
            inst = self._instincts.pop(inst_id)
            self._deindex(inst)
        return len(to_remove)

    def __len__(self) -> int:
        return len(self._instincts)

    def __iter__(self) -> Iterator[Instinct]:
        return iter(self._instincts.values())

    def _make_id(self, trigger: str, action: str, project_id: str) -> str:
        content = f"{project_id}:{trigger}:{action}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _index(self, inst: Instinct) -> None:
        if inst.project_id:
            if inst.project_id not in self._by_project:
                self._by_project[inst.project_id] = set()
            self._by_project[inst.project_id].add(inst.id)
        if inst.scope == InstinctScope.GLOBAL:
            self._global.add(inst.id)
        if inst.domain not in self._by_domain:
            self._by_domain[inst.domain] = set()
        self._by_domain[inst.domain].add(inst.id)

    def _deindex(self, inst: Instinct) -> None:
        if inst.project_id and inst.project_id in self._by_project:
            self._by_project[inst.project_id].discard(inst.id)
        self._global.discard(inst.id)
        if inst.domain in self._by_domain:
            self._by_domain[inst.domain].discard(inst.id)
