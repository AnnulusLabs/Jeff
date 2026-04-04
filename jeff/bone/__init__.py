"""jeff.bone — Session persistence. The skeleton that holds state across runs."""

import json
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict

JEFF_HOME = Path.home() / ".jeff"
SESSIONS_DIR = JEFF_HOME / "sessions"
CONFIG_PATH = JEFF_HOME / "config.json"


@dataclass
class Message:
    role: str  # user, assistant, system, tool
    content: str
    tool: str | None = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class Session:
    id: str
    cwd: str
    messages: list[Message] = field(default_factory=list)
    model: str = "hermes3:8b"
    tokens_in: int = 0
    tokens_out: int = 0
    created: float = field(default_factory=time.time)
    updated: float = field(default_factory=time.time)

    def add(self, role: str, content: str, tool: str | None = None):
        self.messages.append(Message(role=role, content=content, tool=tool))
        self.updated = time.time()

    def history(self, limit: int | None = None) -> list[dict]:
        msgs = self.messages[-limit:] if limit else self.messages
        return [{"role": m.role, "content": m.content} for m in msgs]

    def cost_summary(self) -> str:
        return f"{self.tokens_in} in / {self.tokens_out} out"


def init():
    """Create Jeff's home."""
    JEFF_HOME.mkdir(exist_ok=True)
    SESSIONS_DIR.mkdir(exist_ok=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps({"model": "hermes3:8b"}, indent=2))


def save_session(session: Session):
    path = SESSIONS_DIR / f"{session.id}.json"
    data = {
        "id": session.id,
        "cwd": session.cwd,
        "model": session.model,
        "tokens_in": session.tokens_in,
        "tokens_out": session.tokens_out,
        "created": session.created,
        "updated": session.updated,
        "messages": [asdict(m) for m in session.messages],
    }
    path.write_text(json.dumps(data, indent=2))


def load_session(session_id: str) -> Session | None:
    path = SESSIONS_DIR / f"{session_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    session = Session(
        id=data["id"], cwd=data["cwd"], model=data.get("model", "hermes3:8b"),
        tokens_in=data.get("tokens_in", 0), tokens_out=data.get("tokens_out", 0),
        created=data.get("created", 0), updated=data.get("updated", 0),
    )
    session.messages = [Message(**m) for m in data.get("messages", [])]
    return session


def list_sessions() -> list[str]:
    return sorted(p.stem for p in SESSIONS_DIR.glob("*.json"))


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def save_config(config: dict):
    CONFIG_PATH.write_text(json.dumps(config, indent=2))


def session_path(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"
