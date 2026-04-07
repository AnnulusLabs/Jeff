"""jeff.blood.provenance — W3C PROV-DM audit trail.

Ported from NOX kerf/blood/provenance.py. Every piece of content gets a
provenance record: what is it, where did it come from, who authored it,
when was it created, what was its chain of custody, is it trustworthy?

Answers the question NOX was supposed to answer but never shipped:
"Who told the agent to do this?"

AnnulusLabs LLC · April 2026
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EntityType(Enum):
    CODE = "code"
    SKILL = "skill"
    MESSAGE = "message"
    ACTION = "action"
    CONFIGURATION = "configuration"
    AGENT = "agent"


class SourceType(Enum):
    HUMAN = "human"
    AGENT = "agent"
    GITHUB = "github"
    UNKNOWN = "unknown"
    SELF = "self"


@dataclass
class ProvenanceRecord:
    """Complete provenance record for a piece of content."""
    record_id: str
    content_hash: str
    source: str
    source_type: SourceType
    author: str
    created_at: str
    entity_type: EntityType = EntityType.CODE
    derived_from: list[str] = field(default_factory=list)
    transformations: list[str] = field(default_factory=list)
    verified: bool = False
    verification_method: str = ""
    trust_score: float = 0.5
    infections_found: int = 0
    blocked: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "content_hash": self.content_hash,
            "source": self.source,
            "source_type": self.source_type.value,
            "author": self.author,
            "created_at": self.created_at,
            "entity_type": self.entity_type.value,
            "derived_from": self.derived_from,
            "transformations": self.transformations,
            "verified": self.verified,
            "verification_method": self.verification_method,
            "trust_score": self.trust_score,
            "infections_found": self.infections_found,
            "blocked": self.blocked,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProvenanceRecord:
        data = dict(data)
        data["source_type"] = SourceType(data.get("source_type", "unknown"))
        data["entity_type"] = EntityType(data.get("entity_type", "code"))
        return cls(**data)


class ProvenanceTracker:
    """Tracks provenance of all code and actions. The audit trail."""

    def __init__(self):
        self.records: dict[str, ProvenanceRecord] = {}
        self.by_hash: dict[str, str] = {}
        self.by_source: dict[str, list[str]] = {}
        self.by_author: dict[str, list[str]] = {}

    def record(
        self,
        content: str,
        source: str = "unknown",
        author: str = "unknown",
        content_hash: str | None = None,
        derived_from: list[str] | None = None,
        entity_type: EntityType = EntityType.CODE,
        infections_found: int = 0,
        context: dict | None = None,
    ) -> ProvenanceRecord:
        """Record provenance for a piece of content."""
        if content_hash is None:
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Dedupe by hash
        if content_hash in self.by_hash:
            return self.records[self.by_hash[content_hash]]

        source_type = self._classify_source(source, author)
        trust_score = self._calculate_trust(source_type, author, infections_found)

        record_id = f"prov:{uuid.uuid4().hex[:12]}"
        record = ProvenanceRecord(
            record_id=record_id,
            content_hash=content_hash,
            source=source,
            source_type=source_type,
            author=author,
            created_at=datetime.now(timezone.utc).isoformat(),
            entity_type=entity_type,
            derived_from=derived_from or [],
            trust_score=trust_score,
            infections_found=infections_found,
            blocked=(infections_found > 0 and trust_score < 0.3),
            metadata=context or {},
        )

        self.records[record_id] = record
        self.by_hash[content_hash] = record_id
        self.by_source.setdefault(source, []).append(record_id)
        self.by_author.setdefault(author, []).append(record_id)
        return record

    def derive(
        self,
        content: str,
        parent_hash: str,
        source: str = "unknown",
        author: str = "unknown",
        transformations: list[str] | None = None,
    ) -> ProvenanceRecord:
        """Create a derived record with lineage to parent."""
        parent_record_id = self.by_hash.get(parent_hash)
        derived_from = [parent_record_id] if parent_record_id else [parent_hash]
        record = self.record(
            content=content,
            source=source,
            author=author,
            derived_from=derived_from,
        )
        if transformations:
            record.transformations = transformations
        return record

    def _classify_source(self, source: str, author: str) -> SourceType:
        s = source.lower()
        a = author.lower()
        if "github" in s:
            return SourceType.GITHUB
        if "agent" in s or "bot" in s or "model" in a:
            return SourceType.AGENT
        if a in ("self", "system", "jeff"):
            return SourceType.SELF
        if "@" in a or "human" in a or a == "user":
            return SourceType.HUMAN
        return SourceType.UNKNOWN

    def _calculate_trust(
        self, source_type: SourceType, author: str, infections: int,
    ) -> float:
        base_trust = {
            SourceType.HUMAN: 0.7,
            SourceType.SELF: 0.8,
            SourceType.GITHUB: 0.5,
            SourceType.AGENT: 0.3,
            SourceType.UNKNOWN: 0.2,
        }
        trust = base_trust.get(source_type, 0.2)
        if infections > 0:
            trust *= max(0.1, 1 - (infections * 0.2))
        return round(trust, 2)

    def get_lineage(self, record_id: str, depth: int = 10) -> dict:
        """Trace the complete lineage of a record."""
        if record_id not in self.records:
            return {"error": "Record not found"}
        record = self.records[record_id]
        lineage: dict = {
            "record": record.to_dict(),
            "parents": [],
            "depth": 0,
        }
        to_process = [(r, 1) for r in record.derived_from]
        seen = {record_id}
        while to_process and lineage["depth"] < depth:
            parent_id, level = to_process.pop(0)
            if parent_id in seen or parent_id not in self.records:
                continue
            seen.add(parent_id)
            parent = self.records[parent_id]
            lineage["parents"].append({
                "level": level,
                "record": parent.to_dict(),
            })
            lineage["depth"] = max(lineage["depth"], level)
            for gp in parent.derived_from:
                to_process.append((gp, level + 1))
        return lineage

    def verify(self, record_id: str, method: str = "manual") -> bool:
        if record_id not in self.records:
            return False
        record = self.records[record_id]
        record.verified = True
        record.verification_method = method
        record.trust_score = min(1.0, record.trust_score + 0.3)
        return True

    def get_by_source(self, source: str) -> list[ProvenanceRecord]:
        record_ids = self.by_source.get(source, [])
        return [self.records[rid] for rid in record_ids]

    def get_by_author(self, author: str) -> list[ProvenanceRecord]:
        record_ids = self.by_author.get(author, [])
        return [self.records[rid] for rid in record_ids]

    def get_suspicious(self, trust_threshold: float = 0.3) -> list[ProvenanceRecord]:
        """Get all records below trust threshold."""
        return [r for r in self.records.values() if r.trust_score < trust_threshold]

    def export_chain(self, record_id: str) -> str:
        return json.dumps(self.get_lineage(record_id), indent=2)

    def report(self) -> str:
        """Generate provenance summary report."""
        total = len(self.records)
        lines = [
            f"Provenance: {total} records",
            f"  sources: {len(self.by_source)}  authors: {len(self.by_author)}",
        ]
        trust_buckets = {"high": 0, "medium": 0, "low": 0}
        for r in self.records.values():
            if r.trust_score > 0.7:
                trust_buckets["high"] += 1
            elif r.trust_score >= 0.3:
                trust_buckets["medium"] += 1
            else:
                trust_buckets["low"] += 1
        lines.append(
            f"  trust: {trust_buckets['high']} high / "
            f"{trust_buckets['medium']} medium / {trust_buckets['low']} low"
        )
        source_counts: dict[str, int] = {}
        for r in self.records.values():
            source_counts[r.source_type.value] = source_counts.get(r.source_type.value, 0) + 1
        for st, count in sorted(source_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {st}: {count}")
        return "\n".join(lines)
