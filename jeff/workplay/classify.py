"""jeff.workplay.classify — PR → cognitive basin mapping.

Classifies pull requests into the basin that best describes
the cognitive task required to review them. Each basin maps
to a game template.

KERF is inspectable, not mystical. Every classification includes
confidence, features, alternatives, and plain-English reason.

AnnulusLabs LLC · April 2026
"""

import re
from dataclasses import dataclass, field


@dataclass
class PRFeatures:
    """Extracted features from a pull request."""
    files_changed: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    has_tests: bool = False
    has_config: bool = False
    has_docs: bool = False
    has_migration: bool = False
    has_security_files: bool = False
    file_types: list = field(default_factory=list)
    title_keywords: list = field(default_factory=list)
    complexity: str = "low"  # low, medium, high


@dataclass
class Classification:
    """Basin classification result with full explainability."""
    basin: str
    template: str
    fidelity_tier: int          # 1=full, 2=framed, 3=passthrough
    confidence: float
    title: str                  # game mission title
    narrative: str              # game narrative text
    features: PRFeatures = None
    alternatives: list = field(default_factory=list)
    reason: str = ""


# ── Basin Definitions ────────────────────────────────────────────

BASINS = {
    "quality_inspection": {
        "description": "Review artifact for flaws",
        "indicators": ["refactor", "fix", "bug", "patch", "hotfix", "cleanup"],
        "template": "medieval",
        "title_pattern": "Inspect the {artifact}",
        "narrative": "The blacksmith presents new work for inspection.",
    },
    "construction": {
        "description": "New feature or system being built",
        "indicators": ["feat", "feature", "add", "implement", "create", "new"],
        "template": "medieval",
        "title_pattern": "Review the New {artifact}",
        "narrative": "The architect presents blueprints for a new structure.",
    },
    "defense": {
        "description": "Security-related changes",
        "indicators": ["security", "auth", "permission", "vuln", "cve", "xss", "csrf", "inject"],
        "template": "scifi",
        "title_pattern": "Fortify the {artifact}",
        "narrative": "Sensor sweep detected changes to the defense grid.",
    },
    "investigation": {
        "description": "Debugging or root cause analysis",
        "indicators": ["debug", "investigate", "trace", "log", "diagnose", "root cause"],
        "template": "scifi",
        "title_pattern": "Analyze the Anomaly in {artifact}",
        "narrative": "An anomaly has been detected. Analyze sensor data.",
    },
    "logistics": {
        "description": "Dependencies, CI/CD, infrastructure",
        "indicators": ["deps", "dependency", "ci", "cd", "pipeline", "docker", "deploy", "config", "infra"],
        "template": "minimal",
        "title_pattern": "Supply Chain: {artifact}",
        "narrative": "Incoming shipment requires verification.",
    },
    "documentation": {
        "description": "Docs, README, comments",
        "indicators": ["doc", "readme", "comment", "typo", "changelog", "guide"],
        "template": "minimal",
        "title_pattern": "Archive Update: {artifact}",
        "narrative": "New records submitted to the archive.",
    },
}

TIER_THRESHOLDS = {
    1: {"max_files": 5, "max_lines": 200},      # full translation
    2: {"max_files": 15, "max_lines": 500},      # framed
    3: {"max_files": 999, "max_lines": 99999},   # passthrough
}


# ── Feature Extraction ──────────────────────────────────────────

def extract_features(pr: dict) -> PRFeatures:
    """Extract classifiable features from PR data."""
    files = pr.get("files", [])
    title = pr.get("title", "").lower()

    file_types = set()
    has_tests = False
    has_config = False
    has_docs = False
    has_migration = False
    has_security = False
    lines_added = 0
    lines_removed = 0

    for f in files:
        name = f.get("filename", "").lower()
        ext = name.rsplit(".", 1)[-1] if "." in name else ""
        file_types.add(ext)

        lines_added += f.get("additions", 0)
        lines_removed += f.get("deletions", 0)

        if "test" in name or "spec" in name:
            has_tests = True
        if name in ("config", "settings", ".env", "pyproject.toml",
                     "package.json", "docker", "makefile"):
            has_config = True
        if ext in ("md", "rst", "txt") or "doc" in name:
            has_docs = True
        if "migration" in name or "migrate" in name:
            has_migration = True
        if "auth" in name or "security" in name or "permission" in name:
            has_security = True

    total_lines = lines_added + lines_removed
    if total_lines > 500 or len(files) > 15:
        complexity = "high"
    elif total_lines > 100 or len(files) > 5:
        complexity = "medium"
    else:
        complexity = "low"

    keywords = []
    for basin, info in BASINS.items():
        for indicator in info["indicators"]:
            if indicator in title:
                keywords.append(indicator)

    return PRFeatures(
        files_changed=len(files),
        lines_added=lines_added,
        lines_removed=lines_removed,
        has_tests=has_tests,
        has_config=has_config,
        has_docs=has_docs,
        has_migration=has_migration,
        has_security_files=has_security,
        file_types=list(file_types),
        title_keywords=keywords,
        complexity=complexity)


# ── Classification ───────────────────────────────────────────────

def classify_pr(pr: dict) -> Classification:
    """Classify a PR into a cognitive basin with full explainability."""
    features = extract_features(pr)
    title = pr.get("title", "Unknown")

    # Score each basin
    scores: dict[str, float] = {}
    for basin_name, basin_info in BASINS.items():
        score = 0.0
        for indicator in basin_info["indicators"]:
            if indicator in title.lower():
                score += 2.0
            for ft in features.file_types:
                if indicator in ft:
                    score += 0.5
        if basin_name == "defense" and features.has_security_files:
            score += 3.0
        if basin_name == "documentation" and features.has_docs and not features.has_tests:
            score += 2.0
        if basin_name == "logistics" and features.has_config:
            score += 2.0
        if basin_name == "construction" and features.lines_added > features.lines_removed * 2:
            score += 1.0
        if basin_name == "quality_inspection" and features.has_tests:
            score += 1.0
        scores[basin_name] = score

    # Pick winner
    if all(s == 0 for s in scores.values()):
        best = "quality_inspection"  # safe default
        confidence = 0.4
    else:
        best = max(scores, key=scores.get)
        total = sum(scores.values())
        confidence = scores[best] / total if total > 0 else 0.5

    basin_info = BASINS[best]

    # Determine fidelity tier
    total_lines = features.lines_added + features.lines_removed
    if (features.files_changed <= TIER_THRESHOLDS[1]["max_files"] and
            total_lines <= TIER_THRESHOLDS[1]["max_lines"]):
        tier = 1
    elif (features.files_changed <= TIER_THRESHOLDS[2]["max_files"] and
            total_lines <= TIER_THRESHOLDS[2]["max_lines"]):
        tier = 2
    else:
        tier = 3

    # Build artifact name from PR title
    artifact = re.sub(r'^(feat|fix|chore|docs|refactor|test|ci)[:\s]*',
                       '', title, flags=re.IGNORECASE).strip() or "the code"

    # Build alternatives
    alternatives = []
    for name, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        if name != best and score > 0:
            alternatives.append({
                "basin": name,
                "confidence": round(score / max(1, sum(scores.values())), 2)
            })

    reason_parts = []
    if features.title_keywords:
        reason_parts.append(f"Title signals: {', '.join(features.title_keywords)}")
    reason_parts.append(f"Files: {features.files_changed}, "
                        f"Lines: +{features.lines_added}/-{features.lines_removed}")
    reason_parts.append(f"Complexity: {features.complexity}")
    reason_parts.append(f"Basin: {best} at {confidence:.0%}")

    return Classification(
        basin=best,
        template=basin_info["template"],
        fidelity_tier=tier,
        confidence=round(confidence, 2),
        title=basin_info["title_pattern"].format(artifact=artifact[:50]),
        narrative=basin_info["narrative"],
        features=features,
        alternatives=alternatives[:3],
        reason=". ".join(reason_parts))
