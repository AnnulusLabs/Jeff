"""jeff.bone.memory — Three-pipeline procedural memory.

Episodic:   what happened (task trajectories, session logs)
Procedural: how to do things (golden paths, tool-use patterns, strategies)
Semantic:   domain knowledge (codebase facts, project conventions)

SQLite-backed, persists across sessions.
Nothing is ever discarded. K is retained. Law IV satisfied.

AnnulusLabs LLC · April 2026
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

from jeff.bone import JEFF_HOME

MEMORY_DIR = JEFF_HOME / "memory"
MEMORY_DB = MEMORY_DIR / "procedural.db"


class Pipeline:
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"
    SEMANTIC = "semantic"


@dataclass
class MemoryEntry:
    id: int = 0
    pipeline: str = Pipeline.EPISODIC
    key: str = ""
    content: str = ""
    context: str = ""
    score: float = 0.0
    hits: int = 0
    created: float = field(default_factory=time.time)
    updated: float = field(default_factory=time.time)
    tags: str = ""

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "pipeline": self.pipeline,
            "key": self.key,
            "content": self.content,
            "context": self.context,
            "score": self.score,
            "hits": self.hits,
            "created": self.created,
            "updated": self.updated,
            "tags": self.tags,
        }


class ProceduralMemory:
    """Three-pipeline memory system. SQLite-backed."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else MEMORY_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.db_path))
        self.db.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline TEXT NOT NULL,
                key TEXT NOT NULL,
                content TEXT NOT NULL,
                context TEXT DEFAULT '',
                score REAL DEFAULT 0.0,
                hits INTEGER DEFAULT 0,
                created REAL,
                updated REAL,
                tags TEXT DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_pipeline ON memories(pipeline);
            CREATE INDEX IF NOT EXISTS idx_key ON memories(key);
            CREATE INDEX IF NOT EXISTS idx_score ON memories(score DESC);
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
                USING fts5(key, content, context, tags);
        """)
        self.db.commit()

    # ── Store ────────────────────────────────────────────────────────

    def store(self, entry: MemoryEntry) -> int:
        """Store a memory. Returns the row ID."""
        now = time.time()
        entry.created = entry.created or now
        entry.updated = now
        cursor = self.db.execute(
            "INSERT INTO memories (pipeline, key, content, context, score, hits, "
            "created, updated, tags) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (entry.pipeline, entry.key, entry.content, entry.context,
             entry.score, entry.hits, entry.created, entry.updated, entry.tags),
        )
        self.db.execute(
            "INSERT INTO memories_fts (rowid, key, content, context, tags) "
            "VALUES (?, ?, ?, ?, ?)",
            (cursor.lastrowid, entry.key, entry.content, entry.context, entry.tags),
        )
        self.db.commit()
        return cursor.lastrowid

    def store_episodic(self, key: str, content: str, context: str = "", tags: str = "") -> int:
        """Store a task trajectory or session event."""
        return self.store(MemoryEntry(
            pipeline=Pipeline.EPISODIC, key=key, content=content,
            context=context, tags=tags,
        ))

    def store_procedural(
        self, key: str, content: str, context: str = "", score: float = 0.5, tags: str = "",
    ) -> int:
        """Store a golden path or tool-use pattern."""
        return self.store(MemoryEntry(
            pipeline=Pipeline.PROCEDURAL, key=key, content=content,
            context=context, score=score, tags=tags,
        ))

    def store_semantic(self, key: str, content: str, context: str = "", tags: str = "") -> int:
        """Store domain knowledge or project convention."""
        return self.store(MemoryEntry(
            pipeline=Pipeline.SEMANTIC, key=key, content=content,
            context=context, tags=tags,
        ))

    # ── Retrieve ─────────────────────────────────────────────────────

    def _row_to_entry(self, row: sqlite3.Row) -> MemoryEntry:
        return MemoryEntry(**dict(row))

    def search(self, query: str, pipeline: str | None = None, limit: int = 20) -> list[MemoryEntry]:
        """Full-text search across memories."""
        try:
            sql = (
                "SELECT m.* FROM memories_fts f "
                "JOIN memories m ON m.id = f.rowid "
                "WHERE memories_fts MATCH ?"
            )
            params: list = [query]
            if pipeline:
                sql += " AND m.pipeline = ?"
                params.append(pipeline)
            sql += " ORDER BY m.score DESC, m.updated DESC LIMIT ?"
            params.append(limit)
            rows = self.db.execute(sql, params).fetchall()
            entries = [self._row_to_entry(row) for row in rows]
            for entry in entries:
                self._record_hit(entry.id)
            return entries
        except Exception:
            return []

    def by_pipeline(self, pipeline: str, limit: int = 50) -> list[MemoryEntry]:
        """Get memories from a specific pipeline."""
        rows = self.db.execute(
            "SELECT * FROM memories WHERE pipeline = ? ORDER BY score DESC, updated DESC LIMIT ?",
            (pipeline, limit),
        ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def by_key(self, key: str, pipeline: str | None = None) -> list[MemoryEntry]:
        """Get memories by exact key."""
        if pipeline:
            rows = self.db.execute(
                "SELECT * FROM memories WHERE key = ? AND pipeline = ? ORDER BY score DESC",
                (key, pipeline),
            ).fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM memories WHERE key = ? ORDER BY score DESC",
                (key,),
            ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def recent(self, pipeline: str | None = None, limit: int = 20) -> list[MemoryEntry]:
        """Get most recent memories."""
        if pipeline:
            rows = self.db.execute(
                "SELECT * FROM memories WHERE pipeline = ? ORDER BY updated DESC LIMIT ?",
                (pipeline, limit),
            ).fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM memories ORDER BY updated DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def top_procedural(self, limit: int = 10) -> list[MemoryEntry]:
        """Get highest-scoring procedural memories (golden paths)."""
        return self.by_pipeline(Pipeline.PROCEDURAL, limit=limit)

    # ── Reinforce ────────────────────────────────────────────────────

    def reinforce(self, entry_id: int, delta: float = 0.1):
        """Bump score for a memory that proved useful."""
        self.db.execute(
            "UPDATE memories SET score = MIN(score + ?, 1.0), updated = ? WHERE id = ?",
            (delta, time.time(), entry_id),
        )
        self.db.commit()

    def penalize(self, entry_id: int, delta: float = 0.1):
        """Lower score for a memory that led astray."""
        self.db.execute(
            "UPDATE memories SET score = MAX(score - ?, 0.0), updated = ? WHERE id = ?",
            (delta, time.time(), entry_id),
        )
        self.db.commit()

    def _record_hit(self, entry_id: int):
        """Track retrieval frequency."""
        self.db.execute(
            "UPDATE memories SET hits = hits + 1 WHERE id = ?", (entry_id,),
        )
        self.db.commit()

    # ── Stats ────────────────────────────────────────────────────────

    def count(self, pipeline: str | None = None) -> int:
        if pipeline:
            return self.db.execute(
                "SELECT COUNT(*) FROM memories WHERE pipeline = ?", (pipeline,),
            ).fetchone()[0]
        return self.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

    def summary(self) -> str:
        total = self.count()
        ep = self.count(Pipeline.EPISODIC)
        pr = self.count(Pipeline.PROCEDURAL)
        se = self.count(Pipeline.SEMANTIC)
        top = self.top_procedural(limit=3)
        lines = [
            f"Memory: {total} entries ({ep} episodic, {pr} procedural, {se} semantic)",
        ]
        if top:
            lines.append("Top golden paths:")
            for m in top:
                lines.append(f"  [{m.score:.2f}] {m.key}")
        return "\n".join(lines)

    def close(self):
        self.db.close()
