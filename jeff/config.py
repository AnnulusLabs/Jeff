"""jeff.config — Hardware-aware configuration.

Steve's rig: AMD 9950X3D, RTX 3090 (24GB VRAM), no MI60 yet.
Models sized for 24GB. Context windows set for real work.

AnnulusLabs LLC · April 2026
"""

# ── VRAM Budget ──────────────────────────────────────────────────
# RTX 3090 = 24GB GDDR6X
# Reserve 2GB for OS/display = 22GB usable
# KV cache eats VRAM at runtime — budget for it

VRAM_TOTAL_GB = 24
VRAM_USABLE_GB = 22

# ── Model Tiers (24GB) ──────────────────────────────────────────
# Tier 1: Big brain, fills VRAM. For complex tasks.
# Tier 2: Medium, leaves room for KV cache. Daily driver.
# Tier 3: Small, fast, cheap. For bulk/batch/forge.

MODELS = {
    # ── Tier 1: Heavy (16-22GB, tight fit) ──────────────────
    "heavy": [
        "deepseek-r1:14b",          # 14B reasoning, ~12GB q4
        "qwen2.5-coder:14b",        # 14B code specialist, ~12GB q4
        "hermes3:8b",                # 8B general, ~6GB q4 (room for big context)
        "gemma3:12b",                # 12B, ~10GB q4
    ],

    # ── Tier 2: Medium (6-10GB, daily driver) ────────────────
    "medium": [
        "hermes3:8b",                # solid all-rounder
        "qwen2.5-coder:7b",         # code focused
        "deepseek-r1:7b",           # reasoning
        "phi4:14b",                  # Microsoft, good at code
    ],

    # ── Tier 3: Light (2-4GB, fast/batch) ────────────────────
    "light": [
        "qwen2.5:3b",               # tiny but capable
        "phi3:mini",                 # 3.8B, fast
        "gemma3:4b",                 # 4B
    ],

    # ── Abliterated (for BranchialAnalyzer) ──────────────────
    "abliterated": [
        # Pull these from huihui-ai on HuggingFace
        # They don't suppress uncomfortable K
        # Critical for honest adversarial review
    ],
}

# ── Domain → Model Routing ───────────────────────────────────────
# Jeff picks the right model for the job

DOMAIN_MODELS = {
    "code":     "qwen2.5-coder:14b",    # code specialist
    "research": "deepseek-r1:14b",       # reasoning for research
    "write":    "hermes3:8b",            # natural language
    "analyze":  "deepseek-r1:14b",       # analytical reasoning
    "plan":     "hermes3:8b",            # planning
    "teach":    "hermes3:8b",            # socratic
    "think":    "deepseek-r1:14b",       # deep reasoning
    "default":  "hermes3:8b",            # fallback
}

# ── Context Windows ──────────────────────────────────────────────
# Bigger context = more VRAM for KV cache
# 8B model @ 64k context ≈ 6GB model + 4GB KV = 10GB total
# 14B model @ 32k context ≈ 12GB model + 3GB KV = 15GB total
# Leave headroom for batched inference

CONTEXT_WINDOWS = {
    "hermes3:8b":           65536,   # 64k — plenty of room
    "qwen2.5-coder:14b":   32768,   # 32k — tight but works
    "deepseek-r1:14b":     32768,   # 32k
    "qwen2.5-coder:7b":    65536,   # 64k — small model, big context
    "deepseek-r1:7b":      65536,   # 64k
    "phi4:14b":            16384,   # 16k — phi4 context is limited
    "qwen2.5:3b":          32768,   # 32k
    "phi3:mini":           32768,   # 32k
    "default":             32768,   # safe default
}

# ── Power-Aware Routing ──────────────────────────────────────────
# EcoFlow Delta 2 reports battery via API (or we check manually)

POWER_ROUTING = {
    "solar_full":    "qwen2.5-coder:14b",  # sun's out, big model
    "solar_partial": "hermes3:8b",          # partly cloudy
    "battery_high":  "hermes3:8b",          # >60%, medium
    "battery_mid":   "qwen2.5:3b",          # 30-60%, small
    "battery_low":   "phi3:mini",           # <30%, tiny
    "grid":          "qwen2.5-coder:14b",   # plugged in, go hard
}

# ── Ollama Connection ────────────────────────────────────────────

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_TIMEOUT = 120  # seconds, some models are slow to load

# ── Jeff Behavior ────────────────────────────────────────────────

JEFF_HOME = "A:\\AI\\jeff-release"
WORKSPACE = "A:\\AI"
KERF_HOME = "A:\\AI\\KERF"
TERMINAL_HOME = "A:\\AI\\kerf-terminal"

# Sense/lore indexes these directories
LORE_ROOTS = [
    "A:\\AI\\KERF",
    "A:\\AI\\jeff-release",
    "A:\\AI\\kerf-terminal",
]

# Blood audit log
AUDIT_DB = "A:\\AI\\jeff-release\\.jeff\\blood\\audit.db"

# Gate strictness
GATE_STRICT = True

# Evolution
EVOLUTION_ENABLED = False  # OFF until stable

# Personality
SYCOPHANCY_FILTER = True
MAX_EXCLAMATION_MARKS = 0
