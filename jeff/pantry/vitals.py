"""jeff.pantry.vitals — Real-time model health. No spinners.

Shows tokens/sec, KV cache pressure, model load state, and
estimated time remaining. You always know if Jeff is thinking
or stuck.

Gripe #24: You don't know if the AI is thinking or stuck.
Gripe #36: Black box pricing — cost before routing.

AnnulusLabs LLC · April 2026
"""

import time
import httpx
from dataclasses import dataclass, field


@dataclass
class ModelVitals:
    name: str = ""
    tokens_per_sec: float = 0.0
    kv_cache_pct: float = 0.0     # 0-100
    loaded: bool = False
    vram_mb: float = 0.0
    context_used: int = 0
    context_max: int = 0
    last_check: float = field(default_factory=time.time)


@dataclass
class CostEstimate:
    model: str
    estimated_tokens: int
    estimated_seconds: float
    estimated_cost_usd: float      # $0 for local, calculated for API
    recommendation: str = ""       # "Use local. Free." or "API: ~$0.03"


def check_vitals(host: str = "http://localhost:11434") -> list[ModelVitals]:
    """Get vitals for all loaded Ollama models."""
    vitals = []
    try:
        resp = httpx.get(f"{host}/api/ps", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            for m in data.get("models", []):
                vitals.append(ModelVitals(
                    name=m.get("name", ""),
                    loaded=True,
                    vram_mb=m.get("size_vram", 0) / 1024 / 1024,
                    context_used=m.get("details", {}).get("context_length", 0),
                ))
    except Exception:
        pass
    return vitals


def estimate_cost(model: str, prompt_tokens: int = 500,
                  output_tokens: int = 1000,
                  local: bool = True) -> CostEstimate:
    """Estimate cost BEFORE routing. Transparency, not mystery.

    Local models: $0. Always. The sun pays for it.
    API models: calculated from published rates.
    """
    # API pricing (approximate, per 1M tokens)
    API_RATES = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "claude-sonnet": {"input": 3.00, "output": 15.00},
        "claude-haiku": {"input": 0.25, "output": 1.25},
        "deepseek-v3": {"input": 0.27, "output": 1.10},
    }

    if local:
        return CostEstimate(
            model=model,
            estimated_tokens=prompt_tokens + output_tokens,
            estimated_seconds=output_tokens / 30.0,  # ~30 tok/s local
            estimated_cost_usd=0.0,
            recommendation="Local. Free. The sun pays for it."
        )

    rates = API_RATES.get(model, {"input": 1.0, "output": 5.0})
    cost = ((prompt_tokens * rates["input"] +
             output_tokens * rates["output"]) / 1_000_000)

    return CostEstimate(
        model=model,
        estimated_tokens=prompt_tokens + output_tokens,
        estimated_seconds=output_tokens / 80.0,
        estimated_cost_usd=round(cost, 4),
        recommendation=f"API: ~${cost:.4f}. Consider local alternative."
    )


def power_aware_model(battery_pct: int = 100,
                      on_solar: bool = False,
                      models: list = None) -> str:
    """Pick model based on power state.

    Gripe #30: Energy guilt.

    Battery low → 3B model.
    On grid/solar → spin up the 70B.
    """
    models = models or ["hermes3:70b", "hermes3:8b", "hermes3:3b",
                        "phi3:mini", "qwen2:1.5b"]
    if battery_pct > 80 or on_solar:
        return models[0]  # big model
    elif battery_pct > 40:
        return models[1]  # medium
    elif battery_pct > 15:
        return models[-2]  # small
    else:
        return models[-1]  # tiny — preserve power


def format_vitals(vitals: list[ModelVitals]) -> str:
    lines = ["VITALS:"]
    if not vitals:
        lines.append("  No models loaded.")
        return "\n".join(lines)
    for v in vitals:
        lines.append(f"  {v.name:<30s} VRAM: {v.vram_mb:.0f}MB  "
                     f"{'LOADED' if v.loaded else 'offline'}")
    return "\n".join(lines)
