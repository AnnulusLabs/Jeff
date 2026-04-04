"""jeff.sense — Context prefetch. CPU cache architecture for knowledge.

L1: Model context window (fast, small, current working set)
L2: Local buffer on disk (large, indexed, searchable, persistent)
L3: The internet (infinite, slow, prefetched by background bots)

Prefetch bots infer what Jeff will need next based on conversation
topic, pull it from L3, index it in L2, so the ContextCompiler
can page it into L1 before the model even asks.

Nothing is ever discarded. K is retained. Law IV satisfied.

AnnulusLabs LLC · April 2026
"""

import asyncio
import hashlib
import json
import time
import sqlite3
import logging
from dataclasses import dataclass, field
from pathlib import Path

import httpx

log = logging.getLogger("jeff.sense")

SENSE_DIR = Path.home() / ".jeff" / "sense"
DB_PATH = SENSE_DIR / "memory.db"


@dataclass
class ContextChunk:
    id: str = ""
    content: str = ""
    source: str = ""
    topic: str = ""
    relevance: float = 0.0
    timestamp: float = 0.0
    tokens_est: int = 0
    tier: str = "L2"

    def __post_init__(self):
        if not self.id:
            raw = f"{self.source}:{self.content[:100]}:{time.time()}"
            self.id = hashlib.sha256(raw.encode()).hexdigest()[:16]
        if not self.tokens_est:
            self.tokens_est = len(self.content.split()) * 4 // 3
        if not self.timestamp:
            self.timestamp = time.time()


@dataclass
class TopicProfile:
    primary: str = ""
    secondary: list = field(default_factory=list)
    keywords: list = field(default_factory=list)
    confidence: float = 0.0


class MemoryBuffer:
    """Persistent L2 cache. Everything Jeff has ever seen."""

    def __init__(self, db_path: Path = DB_PATH):
        SENSE_DIR.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(db_path))
        self._init_db()

    def _init_db(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY, content TEXT NOT NULL,
                source TEXT, topic TEXT, relevance REAL DEFAULT 0.0,
                timestamp REAL, tokens_est INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_topic ON chunks(topic);
            CREATE INDEX IF NOT EXISTS idx_relevance ON chunks(relevance DESC);
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
                USING fts5(content, topic, source);
        """)
        self.db.commit()

    def store(self, chunk: ContextChunk):
        try:
            self.db.execute(
                "INSERT OR REPLACE INTO chunks VALUES (?,?,?,?,?,?,?)",
                (chunk.id, chunk.content, chunk.source, chunk.topic,
                 chunk.relevance, chunk.timestamp, chunk.tokens_est))
            self.db.execute(
                "INSERT OR REPLACE INTO chunks_fts VALUES (?,?,?)",
                (chunk.content, chunk.topic, chunk.source))
            self.db.commit()
        except Exception as e:
            log.warning(f"Buffer store failed: {e}")

    def search(self, query: str, limit: int = 20) -> list:
        try:
            rows = self.db.execute("""
                SELECT c.* FROM chunks_fts f JOIN chunks c ON c.content = f.content
                WHERE chunks_fts MATCH ? ORDER BY c.relevance DESC LIMIT ?
            """, (query, limit)).fetchall()
            return [ContextChunk(id=r[0], content=r[1], source=r[2], topic=r[3],
                                 relevance=r[4], timestamp=r[5], tokens_est=r[6])
                    for r in rows]
        except Exception:
            return []

    def by_topic(self, topic: str, limit: int = 50) -> list:
        rows = self.db.execute(
            "SELECT * FROM chunks WHERE topic=? ORDER BY relevance DESC LIMIT ?",
            (topic, limit)).fetchall()
        return [ContextChunk(id=r[0], content=r[1], source=r[2], topic=r[3],
                             relevance=r[4], timestamp=r[5], tokens_est=r[6])
                for r in rows]

    def recent(self, limit: int = 20) -> list:
        rows = self.db.execute(
            "SELECT * FROM chunks ORDER BY timestamp DESC LIMIT ?",
            (limit,)).fetchall()
        return [ContextChunk(id=r[0], content=r[1], source=r[2], topic=r[3],
                             relevance=r[4], timestamp=r[5], tokens_est=r[6])
                for r in rows]

    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    def size_mb(self) -> float:
        return DB_PATH.stat().st_size / (1024 * 1024) if DB_PATH.exists() else 0


# ── Topic Detection ──────────────────────────────────────────────────

TOPIC_KEYWORDS = {
    "game_dev": {"game", "engine", "sprite", "shader", "godot", "unity",
                 "render", "physics", "collision", "player", "level", "mesh"},
    "web_dev": {"html", "css", "react", "api", "endpoint", "frontend",
                "backend", "server", "route", "component", "fetch"},
    "systems": {"kernel", "memory", "thread", "mutex", "syscall", "driver",
                "pointer", "stack", "heap", "interrupt", "allocat"},
    "ml_ai": {"model", "training", "inference", "weights", "tensor",
              "gradient", "loss", "transformer", "attention", "llm", "fine"},
    "security": {"vulnerability", "exploit", "payload", "inject", "auth",
                 "firewall", "encryption", "hash", "certificate", "pentest"},
    "finance": {"market", "stock", "trade", "price", "portfolio",
                "yield", "bond", "equity", "volatility", "hedge"},
    "hardware": {"gpio", "i2c", "spi", "uart", "pwm", "adc", "mcu",
                 "pcb", "solder", "oscilloscope", "schematic"},
    "mesh_net": {"mesh", "node", "packet", "routing", "lora", "ble",
                 "reticulum", "peer", "broadcast", "relay"},
    "physics": {"manifold", "curvature", "invariant", "geodesic",
                "kerf", "entropy", "wavefunction", "hamiltonian", "tensor"},
}

TOPIC_SEARCHES = {
    "game_dev": ["game development patterns", "game engine architecture",
                 "godot 4 docs", "shader programming tutorial"],
    "web_dev": ["web development 2026", "react docs", "fastapi tutorial"],
    "systems": ["systems programming rust", "linux kernel internals"],
    "ml_ai": ["machine learning 2026", "huggingface transformers docs",
              "LLM fine tuning guide", "pytorch tutorial"],
    "security": ["cybersecurity 2026", "OWASP", "CVE recent critical"],
    "finance": ["market analysis", "FRED economic data", "trading strategies"],
    "hardware": ["embedded systems tutorial", "ESP32 programming"],
    "mesh_net": ["reticulum network docs", "LoRa development guide"],
    "physics": ["computational physics", "differential geometry tutorial"],
}


def detect_topic(text: str) -> TopicProfile:
    words = set(text.lower().split())
    scores = {}
    for topic, kw in TOPIC_KEYWORDS.items():
        overlap = len(words & kw)
        if overlap:
            scores[topic] = overlap

    if not scores:
        return TopicProfile(primary="general")

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return TopicProfile(
        primary=ranked[0][0],
        secondary=[t for t, _ in ranked[1:3]],
        keywords=list(words & TOPIC_KEYWORDS.get(ranked[0][0], set())),
        confidence=min(ranked[0][1] / 5, 1.0),
    )


# ── Prefetch ─────────────────────────────────────────────────────────

async def prefetch(topic: str, buffer: MemoryBuffer, max_fetches: int = 5):
    """Pull L3 → L2 for a topic using DuckDuckGo instant answers."""
    searches = TOPIC_SEARCHES.get(topic, [f"{topic} programming guide"])
    async with httpx.AsyncClient(timeout=15) as client:
        for query in searches[:max_fetches]:
            try:
                resp = await client.get("https://api.duckduckgo.com/",
                                        params={"q": query, "format": "json", "no_html": 1})
                data = resp.json()
                abstract = data.get("Abstract", "")
                if abstract and len(abstract) > 50:
                    buffer.store(ContextChunk(content=abstract, topic=topic,
                                             source=data.get("AbstractURL", "ddg"),
                                             relevance=0.7))
                for rt in data.get("RelatedTopics", [])[:5]:
                    text = rt.get("Text", "")
                    if text and len(text) > 30:
                        buffer.store(ContextChunk(content=text, topic=topic,
                                                  source=rt.get("FirstURL", "ddg"),
                                                  relevance=0.5))
            except Exception:
                continue
    log.info(f"Prefetch '{topic}': {buffer.count()} chunks in L2")


# ── Pager (L2 → L1) ─────────────────────────────────────────────────

def page(buffer: MemoryBuffer, topic: TopicProfile,
         query: str = "", token_budget: int = 4000) -> list:
    """Select most relevant L2 chunks to fill L1 context window."""
    candidates = []
    if topic.primary:
        candidates.extend(buffer.by_topic(topic.primary, limit=30))
    if query:
        candidates.extend(buffer.search(query, limit=20))
    candidates.extend(buffer.recent(limit=10))

    # Dedupe
    seen = set()
    unique = []
    for c in candidates:
        if c.id not in seen:
            seen.add(c.id)
            unique.append(c)

    # Rank and fill budget
    unique.sort(key=lambda c: c.relevance, reverse=True)
    selected, tokens = [], 0
    for chunk in unique:
        if tokens + chunk.tokens_est > token_budget:
            break
        selected.append(chunk)
        tokens += chunk.tokens_est
        chunk.tier = "L1"
    return selected


# ── Background Worker ────────────────────────────────────────────────

async def prefetch_worker(buffer: MemoryBuffer, topic_fn, interval: int = 60):
    """Continuously prefetch based on conversation topic shifts."""
    last = ""
    while True:
        try:
            profile = topic_fn()
            if profile.primary and profile.primary != last:
                log.info(f"Topic shift: {last} -> {profile.primary}")
                await prefetch(profile.primary, buffer)
                for s in profile.secondary:
                    await prefetch(s, buffer, max_fetches=2)
                last = profile.primary
        except Exception as e:
            log.debug(f"Prefetch error: {e}")
        await asyncio.sleep(interval)


async def _test():
    buf = MemoryBuffer()
    convo = "building a game engine with custom shaders and physics collision"
    topic = detect_topic(convo)
    print(f"Topic: {topic.primary} ({topic.confidence:.0%})")
    print(f"Keywords: {topic.keywords}")
    print(f"Prefetching...")
    await prefetch(topic.primary, buf, max_fetches=3)
    print(f"L2: {buf.count()} chunks ({buf.size_mb():.1f}MB)")
    chunks = page(buf, topic, query="collision physics", token_budget=2000)
    print(f"Paged {len(chunks)} chunks to L1")
    for c in chunks[:3]:
        print(f"  [{c.relevance}] {c.content[:80]}...")

if __name__ == "__main__":
    asyncio.run(_test())
