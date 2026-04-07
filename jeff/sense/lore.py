"""jeff.sense.lore — Local lore. Your tribal knowledge.

Indexes your .git history, commit messages, README files, and
inline comments into L2 cache. Jeff learns your weird 10-year-old
internal library by reading your past successes and failures.

Gripe #29: AI knows Python but not YOUR codebase.

AnnulusLabs LLC · April 2026
"""

import re
import sqlite3
import subprocess
import hashlib
import time
from pathlib import Path
from dataclasses import dataclass, field

LORE_DB = Path.home() / ".jeff" / "lore" / "lore.db"


@dataclass
class LoreEntry:
    kind: str       # "commit", "readme", "comment", "config", "pattern"
    content: str
    source: str     # file path or commit hash
    timestamp: float = field(default_factory=time.time)
    relevance: float = 1.0


class LoreIndex:
    """Index local project knowledge into searchable SQLite."""

    def __init__(self, db_path: Path = LORE_DB):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(db_path))
        self._init_db()

    def _init_db(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS lore (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT, content TEXT, source TEXT,
                hash TEXT UNIQUE, timestamp REAL, relevance REAL
            )""")
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_lore_kind ON lore(kind)""")
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_lore_hash ON lore(hash)""")
        self.db.commit()

    def _hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def add(self, entry: LoreEntry):
        h = self._hash(entry.content)
        try:
            self.db.execute(
                "INSERT OR IGNORE INTO lore (kind, content, source, hash, timestamp, relevance) "
                "VALUES (?,?,?,?,?,?)",
                (entry.kind, entry.content[:5000], entry.source,
                 h, entry.timestamp, entry.relevance))
            self.db.commit()
        except sqlite3.Error:
            pass

    _MAX_SEARCH_WORDS = 8

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search lore by keyword. Cap word count, build WHERE statically."""
        words = query.lower().split()[:self._MAX_SEARCH_WORDS]
        if not words:
            return []
        # Build WHERE from a fixed template — no user-influenced SQL identifiers.
        placeholders = " AND ".join(["LOWER(content) LIKE ?"] * len(words))
        sql = (
            "SELECT kind, content, source, relevance FROM lore "
            "WHERE " + placeholders +
            " ORDER BY relevance DESC, timestamp DESC LIMIT ?"
        )
        params = [f"%{w}%" for w in words] + [limit]
        rows = self.db.execute(sql, params).fetchall()
        return [{"kind": r[0], "content": r[1][:500], "source": r[2],
                 "relevance": r[3]} for r in rows]

    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM lore").fetchone()[0]


# ── Git History Indexer ──────────────────────────────────────────────

def index_git_history(cwd: str = ".", max_commits: int = 200) -> int:
    """Index git commit messages. Your project's memory."""
    lore = LoreIndex()
    added = 0
    try:
        result = subprocess.run(
            ["git", "log", f"--max-count={max_commits}",
             "--format=%H|%s|%an|%ad", "--date=unix"],
            cwd=cwd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return 0
        for line in result.stdout.strip().split("\n"):
            if not line or "|" not in line:
                continue
            parts = line.split("|", 3)
            if len(parts) < 2:
                continue
            sha, msg = parts[0], parts[1]
            ts = float(parts[3]) if len(parts) > 3 else time.time()
            # Weight meaningful commits higher
            relevance = 1.0
            if any(w in msg.lower() for w in ["fix", "bug", "critical", "breaking"]):
                relevance = 1.5
            if any(w in msg.lower() for w in ["refactor", "architecture", "design"]):
                relevance = 1.3
            if msg.lower().startswith(("merge", "bump", "update lock")):
                relevance = 0.3
            lore.add(LoreEntry(
                kind="commit", content=msg,
                source=sha[:8], timestamp=ts, relevance=relevance))
            added += 1
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return added


# ── README / Doc Indexer ─────────────────────────────────────────────

def index_docs(cwd: str = ".") -> int:
    """Index README, CHANGELOG, and doc files."""
    lore = LoreIndex()
    added = 0
    doc_patterns = [
        "README*", "CHANGELOG*", "CONTRIBUTING*", "ARCHITECTURE*",
        "docs/*.md", "doc/*.md", "*.md",
    ]
    seen = set()
    root = Path(cwd)
    for pattern in doc_patterns:
        for path in root.glob(pattern):
            if path.name in seen or not path.is_file():
                continue
            seen.add(path.name)
            try:
                content = path.read_text(errors="ignore")[:10000]
                # Split into paragraphs for granularity
                paragraphs = re.split(r"\n\s*\n", content)
                for para in paragraphs:
                    para = para.strip()
                    if len(para) < 20:
                        continue
                    lore.add(LoreEntry(
                        kind="doc", content=para,
                        source=str(path.relative_to(root)),
                        relevance=1.2))
                    added += 1
            except Exception:
                pass
    return added


# ── Code Comment Indexer ─────────────────────────────────────────────

def index_comments(cwd: str = ".", extensions: list = None) -> int:
    """Index code comments — the 'why' behind decisions."""
    lore = LoreIndex()
    added = 0
    extensions = extensions or [".py", ".js", ".ts", ".rs", ".go"]
    root = Path(cwd)

    for ext in extensions:
        for path in root.rglob(f"*{ext}"):
            if "__pycache__" in str(path) or "node_modules" in str(path):
                continue
            try:
                lines = path.read_text(errors="ignore").split("\n")
                comment_block = []
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith("#") or stripped.startswith("//"):
                        comment_block.append(stripped.lstrip("#/ ").strip())
                    elif stripped.startswith('"""') or stripped.startswith("'''"):
                        comment_block.append(stripped.strip("\"' "))
                    else:
                        if comment_block and len(" ".join(comment_block)) > 30:
                            lore.add(LoreEntry(
                                kind="comment",
                                content=" ".join(comment_block),
                                source=str(path.relative_to(root)),
                                relevance=1.0))
                            added += 1
                        comment_block = []
            except Exception:
                pass
    return added


# ── Config Pattern Indexer ───────────────────────────────────────────

def index_configs(cwd: str = ".") -> int:
    """Index project configs — pyproject.toml, package.json, etc."""
    lore = LoreIndex()
    added = 0
    configs = [
        "pyproject.toml", "setup.cfg", "setup.py",
        "package.json", "Cargo.toml", "go.mod",
        "Makefile", "Dockerfile", "docker-compose.yml",
        ".env.example", "requirements.txt",
    ]
    root = Path(cwd)
    for name in configs:
        path = root / name
        if path.exists():
            try:
                content = path.read_text(errors="ignore")[:5000]
                lore.add(LoreEntry(
                    kind="config", content=content,
                    source=name, relevance=1.1))
                added += 1
            except Exception:
                pass
    return added


# ── Full Index ───────────────────────────────────────────────────────

def index_all(cwd: str = ".") -> dict:
    """Index everything. Run once per project, update incrementally."""
    results = {
        "commits": index_git_history(cwd),
        "docs": index_docs(cwd),
        "comments": index_comments(cwd),
        "configs": index_configs(cwd),
    }
    lore = LoreIndex()
    results["total"] = lore.count()
    return results


def ask_lore(query: str, limit: int = 5) -> list[dict]:
    """Search the lore. What does this project know about X?"""
    return LoreIndex().search(query, limit)
