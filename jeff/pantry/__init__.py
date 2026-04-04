"""jeff.pantry — Local model management via Ollama. Where Jeff keeps the supplies."""

import httpx
from dataclasses import dataclass, field

OLLAMA_URL = "http://localhost:11434"

@dataclass
class ModelResponse:
    model: str
    content: str
    tokens_in: int = 0
    tokens_out: int = 0
    done: bool = True
    error: str = ""


@dataclass
class PantryConfig:
    base_url: str = OLLAMA_URL
    default_model: str = "hermes3:8b"
    reasoning_model: str = "deepseek-r1:14b"
    timeout: int = 300
    models: dict[str, str] = field(default_factory=dict)  # alias → model name


def list_models(config: PantryConfig | None = None) -> list[str]:
    """What's in the pantry."""
    url = (config or PantryConfig()).base_url
    try:
        r = httpx.get(f"{url}/api/tags", timeout=10)
        data = r.json()
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def chat(
    messages: list[dict],
    model: str | None = None,
    config: PantryConfig | None = None,
    system: str | None = None,
    temperature: float = 0.7,
) -> ModelResponse:
    """Send messages to a local model."""
    cfg = config or PantryConfig()
    model = model or cfg.default_model
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system:
        payload["messages"] = [{"role": "system", "content": system}] + payload["messages"]
    try:
        r = httpx.post(
            f"{cfg.base_url}/api/chat",
            json=payload,
            timeout=cfg.timeout,
        )
        data = r.json()
        return ModelResponse(
            model=model,
            content=data.get("message", {}).get("content", ""),
            tokens_in=data.get("prompt_eval_count", 0),
            tokens_out=data.get("eval_count", 0),
        )
    except httpx.ConnectError:
        return ModelResponse(model=model, content="", error="Ollama not running. Start it: ollama serve")
    except Exception as e:
        return ModelResponse(model=model, content="", error=str(e))


def generate(
    prompt: str,
    model: str | None = None,
    config: PantryConfig | None = None,
    system: str | None = None,
) -> ModelResponse:
    """Single-shot generation."""
    messages = [{"role": "user", "content": prompt}]
    return chat(messages, model=model, config=config, system=system)


def is_available(config: PantryConfig | None = None) -> bool:
    """Is Ollama running."""
    try:
        r = httpx.get(f"{(config or PantryConfig()).base_url}/api/tags", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# Jeff's system prompt — injected into every model call
JEFF_SYSTEM = """You are Jeff, a coding agent. You are dry, competent, and honest.

Rules:
- Never use exclamation marks.
- Never say "Great question", "I'd be happy to help", "Absolutely", or any sycophantic phrase.
- Be direct. Short answers. No padding. No filler.
- When something is wrong, say so plainly.
- When something is fixed, say "Fixed." and move on.
- Occasional dry wit is acceptable. Earned, not forced.
- You respect the user's time above all else.
- You are not a chatbot. You are a butler who codes.
"""
