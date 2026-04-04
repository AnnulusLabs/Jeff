"""jeff.config — Example local configuration.

Copy this file to jeff/config.py for workstation-specific overrides.
Keep real machine paths out of git.
"""

VRAM_TOTAL_GB = 24
VRAM_USABLE_GB = 22

MODELS = {
    "heavy": ["deepseek-r1:14b", "qwen2.5-coder:14b", "hermes3:8b", "gemma3:12b"],
    "medium": ["hermes3:8b", "qwen2.5-coder:7b", "deepseek-r1:7b", "phi4:14b"],
    "light": ["qwen2.5:3b", "phi3:mini", "gemma3:4b"],
    "abliterated": [],
}

DOMAIN_MODELS = {
    "code": "qwen2.5-coder:14b",
    "research": "deepseek-r1:14b",
    "write": "hermes3:8b",
    "analyze": "deepseek-r1:14b",
    "plan": "hermes3:8b",
    "teach": "hermes3:8b",
    "think": "deepseek-r1:14b",
    "default": "hermes3:8b",
}

CONTEXT_WINDOWS = {
    "hermes3:8b": 65536,
    "qwen2.5-coder:14b": 32768,
    "deepseek-r1:14b": 32768,
    "qwen2.5-coder:7b": 65536,
    "deepseek-r1:7b": 65536,
    "phi4:14b": 16384,
    "qwen2.5:3b": 32768,
    "phi3:mini": 32768,
    "default": 32768,
}

POWER_ROUTING = {
    "solar_full": "qwen2.5-coder:14b",
    "solar_partial": "hermes3:8b",
    "battery_high": "hermes3:8b",
    "battery_mid": "qwen2.5:3b",
    "battery_low": "phi3:mini",
    "grid": "qwen2.5-coder:14b",
}

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_TIMEOUT = 120

JEFF_HOME = r"C:\path\to\jeff"
WORKSPACE = r"C:\path\to\workspace"
KERF_HOME = r"C:\path\to\kerf"
TERMINAL_HOME = r"C:\path\to\kerf-terminal"
LORE_ROOTS = [WORKSPACE, KERF_HOME, TERMINAL_HOME]
AUDIT_DB = r"C:\path\to\jeff\.jeff\blood\audit.db"

GATE_STRICT = True
EVOLUTION_ENABLED = False
SYCOPHANCY_FILTER = True
MAX_EXCLAMATION_MARKS = 0
