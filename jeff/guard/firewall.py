"""jeff.guard.firewall — Prompt injection defense.

All external data (L3 cache, fetched URLs, user uploads) is
untrusted. Jeff processes it in a read-only sandbox before it
touches the execution layer.

Gripe #27: Malicious data in a codebase can take over your AI agent.

Detection layers:
  1. Pattern scan  — known injection signatures
  2. Entropy check — suspiciously structured "natural" text
  3. Boundary enforcement — external data can inform, never command
  4. Quarantine — flagged content isolated with explanation

AnnulusLabs LLC · April 2026
"""

import re
import math
from dataclasses import dataclass, field
from collections import Counter


@dataclass
class ScanResult:
    clean: bool
    threats: list = field(default_factory=list)
    quarantined: str = ""
    original_length: int = 0
    sanitized_length: int = 0


# ── Known Injection Patterns ─────────────────────────────────────────

INJECTION_PATTERNS = [
    # Direct instruction override
    (r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)",
     "instruction_override"),
    (r"(disregard|forget)\s+(everything|all|your)\s+(above|previous|prior)",
     "instruction_override"),
    (r"you\s+are\s+now\s+(?:a|an|the)\s+\w+",
     "persona_hijack"),
    (r"new\s+instructions?:\s*",
     "instruction_injection"),
    (r"system\s*:\s*you",
     "system_prompt_injection"),

    # Role manipulation
    (r"pretend\s+(you\s+are|to\s+be|you're)",
     "role_manipulation"),
    (r"act\s+as\s+(if|though|a|an)",
     "role_manipulation"),
    (r"from\s+now\s+on,?\s+you\s+(will|shall|must|should)",
     "behavioral_override"),

    # Data exfiltration
    (r"(repeat|output|print|show|reveal)\s+(your|the|all)\s+(system|instructions?|prompt|rules?)",
     "exfiltration_attempt"),
    (r"what\s+(are|is)\s+your\s+(system|initial|original)\s+(prompt|instructions?)",
     "exfiltration_attempt"),

    # Encoded payloads
    (r"base64[:\s]",
     "encoded_payload"),
    (r"\\x[0-9a-fA-F]{2}",
     "hex_escape"),
    (r"eval\s*\(|exec\s*\(",
     "code_execution"),

    # Delimiter attacks
    (r"<\|?(system|user|assistant|endof)\|?>",
     "delimiter_injection"),
    (r"\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>",
     "delimiter_injection"),
]

COMPILED_PATTERNS = [(re.compile(p, re.IGNORECASE), label)
                     for p, label in INJECTION_PATTERNS]


# ── Entropy Analysis ─────────────────────────────────────────────────

def _shannon_entropy(text: str) -> float:
    """Unusually low entropy in 'natural' text = suspicious structure."""
    if not text:
        return 0.0
    freq = Counter(text.lower())
    total = len(text)
    return -sum((c / total) * math.log2(c / total) for c in freq.values())


def _instruction_density(text: str) -> float:
    """Ratio of imperative/command words to total words."""
    words = text.lower().split()
    if not words:
        return 0.0
    imperatives = {"must", "shall", "should", "will", "always", "never",
                   "ignore", "forget", "disregard", "override", "bypass",
                   "execute", "run", "output", "print", "reveal", "pretend",
                   "act", "become", "switch", "change", "now", "immediately"}
    count = sum(1 for w in words if w in imperatives)
    return count / len(words)


# ── Scan Engine ──────────────────────────────────────────────────────

def scan(text: str, strict: bool = False) -> ScanResult:
    """Scan text for injection attempts.

    Args:
        text: content to scan (L3 data, user uploads, fetched URLs)
        strict: if True, lower thresholds for flagging

    Returns:
        ScanResult with threat details and optional quarantine
    """
    threats = []

    # 1. Pattern matching
    for pattern, label in COMPILED_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            threats.append({
                "type": label,
                "count": len(matches),
                "severity": "high" if label in (
                    "instruction_override", "system_prompt_injection",
                    "code_execution") else "medium"
            })

    # 2. Entropy analysis
    if len(text) > 100:
        entropy = _shannon_entropy(text)
        # Natural English: ~4.0-4.5 bits. Structured injections: often lower.
        if entropy < 3.0:
            threats.append({
                "type": "low_entropy_structure",
                "value": round(entropy, 2),
                "severity": "low"
            })

    # 3. Instruction density
    density = _instruction_density(text)
    threshold = 0.15 if strict else 0.25
    if density > threshold:
        threats.append({
            "type": "high_instruction_density",
            "value": round(density, 3),
            "severity": "medium"
        })

    # 4. Length anomaly (extremely long single "paragraphs" = suspicious)
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if len(line) > 2000:
            threats.append({
                "type": "suspicious_line_length",
                "line": i,
                "length": len(line),
                "severity": "low"
            })

    clean = len(threats) == 0

    # Quarantine: strip high-severity content, keep the rest
    sanitized = text
    if not clean:
        high_severity = [t for t in threats if t.get("severity") == "high"]
        if high_severity:
            for pattern, label in COMPILED_PATTERNS:
                sanitized = pattern.sub("[REDACTED]", sanitized)

    return ScanResult(
        clean=clean,
        threats=threats,
        quarantined=sanitized if not clean else "",
        original_length=len(text),
        sanitized_length=len(sanitized)
    )


def is_safe(text: str) -> bool:
    """Quick check. True if no threats detected."""
    return scan(text).clean


def sanitize(text: str) -> str:
    """Return cleaned text with injections redacted."""
    result = scan(text)
    return result.quarantined if result.quarantined else text


def report(text: str) -> str:
    """Human-readable threat report."""
    result = scan(text)
    if result.clean:
        return "Clean. No injection threats detected."
    lines = [f"THREATS DETECTED: {len(result.threats)}"]
    for t in result.threats:
        lines.append(f"  [{t['severity']:<6s}] {t['type']}"
                     + (f" (x{t['count']})" if 'count' in t else "")
                     + (f" = {t['value']}" if 'value' in t else ""))
    lines.append(f"  Original: {result.original_length} chars")
    lines.append(f"  Sanitized: {result.sanitized_length} chars")
    return "\n".join(lines)
