"""jeff.staff.scholar — Papers to code. Ideas to implementations.

Karpathy pattern: share the idea, agent builds it.
paper2code pattern: every line traces to the paper section.
DeepScientist pattern: one repo per quest, visible progress.

Jeff's scholar reads papers, extracts implementable claims,
builds working code with provenance, and flags what the paper
skips or assumes.

"The paper says X. Here's X as code. Here's what they didn't say."

AnnulusLabs LLC · April 2026
"""

import re
from dataclasses import dataclass, field


@dataclass
class PaperClaim:
    """An implementable claim extracted from a paper."""
    section: str           # "Section 3.2" or "Algorithm 1"
    claim: str             # what the paper claims
    implementable: bool    # can this be turned into code?
    dependencies: list = field(default_factory=list)  # what it depends on
    assumptions: list = field(default_factory=list)    # what it assumes
    gaps: list = field(default_factory=list)            # what it skips


@dataclass
class Implementation:
    """Code with provenance — every function traces to a paper section."""
    claim: PaperClaim
    code: str
    tests: str = ""
    provenance: str = ""   # "Implements Algorithm 1, Section 3.2"
    warnings: list = field(default_factory=list)  # "Paper assumes X but doesn't prove it"
    verified: bool = False


@dataclass
class ScholarReport:
    """Full analysis of a paper's implementability."""
    title: str
    claims: list[PaperClaim] = field(default_factory=list)
    implementations: list[Implementation] = field(default_factory=list)
    total_claims: int = 0
    implementable_claims: int = 0
    gaps_found: int = 0
    assumptions_flagged: int = 0


def extract_sections(text: str) -> list[tuple[str, str]]:
    """Extract titled sections from paper text."""
    # Match common paper section patterns
    patterns = [
        r"^(#{1,3})\s+(.+)$",                    # markdown headers
        r"^(\d+\.?\d*\.?\d*)\s+([A-Z].+)$",      # "3.2 Method"
        r"^(Abstract|Introduction|Method|Results|Discussion|Conclusion)",
    ]
    sections = []
    current_title = "Preamble"
    current_content = []

    for line in text.split("\n"):
        matched = False
        for pattern in patterns:
            m = re.match(pattern, line.strip())
            if m:
                if current_content:
                    sections.append((current_title, "\n".join(current_content)))
                current_title = line.strip()
                current_content = []
                matched = True
                break
        if not matched:
            current_content.append(line)

    if current_content:
        sections.append((current_title, "\n".join(current_content)))
    return sections


def find_claims(section_title: str, section_text: str) -> list[PaperClaim]:
    """Identify implementable claims in a section."""
    claims = []
    # Indicators of implementable content
    indicators = [
        r"algorithm\s+\d",
        r"we\s+(propose|introduce|define|implement)",
        r"the\s+(loss|objective|function|model)\s+is",
        r"equation\s+\(",
        r"(?:step\s+)?\d+[.:]\s+",  # numbered steps
        r"(input|output|return|compute|calculate)",
    ]

    sentences = re.split(r'[.!?]+', section_text)
    for sent in sentences:
        sent = sent.strip()
        if len(sent) < 20:
            continue
        for pattern in indicators:
            if re.search(pattern, sent, re.IGNORECASE):
                # Check for assumptions
                assumptions = []
                if re.search(r"(assum|given that|suppose|let .+ be)", sent, re.IGNORECASE):
                    assumptions.append(sent[:100])

                # Check for gaps
                gaps = []
                vague = re.findall(r"(straightforward|trivial|obvious|left to|omit)", sent, re.IGNORECASE)
                if vague:
                    gaps.append(f"Paper says '{vague[0]}' — implementation detail missing")

                claims.append(PaperClaim(
                    section=section_title,
                    claim=sent[:200],
                    implementable=True,
                    assumptions=assumptions,
                    gaps=gaps))
                break
    return claims


def analyze_paper(text: str, title: str = "Untitled") -> ScholarReport:
    """Full analysis: extract claims, flag gaps, identify implementable parts."""
    sections = extract_sections(text)
    all_claims = []
    for sec_title, sec_text in sections:
        claims = find_claims(sec_title, sec_text)
        all_claims.extend(claims)

    implementable = [c for c in all_claims if c.implementable]
    gaps = sum(len(c.gaps) for c in all_claims)
    assumptions = sum(len(c.assumptions) for c in all_claims)

    return ScholarReport(
        title=title,
        claims=all_claims,
        total_claims=len(all_claims),
        implementable_claims=len(implementable),
        gaps_found=gaps,
        assumptions_flagged=assumptions)


def format_report(report: ScholarReport) -> str:
    """Human-readable scholar report."""
    lines = [
        f"SCHOLAR REPORT: {report.title}",
        f"  Claims found: {report.total_claims}",
        f"  Implementable: {report.implementable_claims}",
        f"  Gaps flagged: {report.gaps_found}",
        f"  Assumptions flagged: {report.assumptions_flagged}",
        "",
    ]
    for claim in report.claims:
        status = "CAN BUILD" if claim.implementable else "CONCEPT"
        lines.append(f"  [{status}] {claim.section}")
        lines.append(f"    {claim.claim[:80]}")
        for gap in claim.gaps:
            lines.append(f"    GAP: {gap}")
        for assumption in claim.assumptions:
            lines.append(f"    ASSUMES: {assumption[:60]}")
    return "\n".join(lines)


def provenance_comment(section: str, claim: str) -> str:
    """Generate a provenance comment for code."""
    return (f"# PROVENANCE: {section}\n"
            f"# Implements: {claim[:80]}\n"
            f"# If this breaks, check the paper section above.\n")


# ── Birth Template ───────────────────────────────────────────────────

SCHOLAR_TEMPLATE = {
    "role": "scholar",
    "tools": ["read", "write", "web_search", "fetch_url"],
    "system_prompt": (
        "You are a research scholar. You read papers and extract "
        "implementable claims. Every line of code you produce traces "
        "back to a specific section of the paper. When the paper is "
        "vague, you flag it. When it assumes, you name the assumption. "
        "When it skips, you say what was skipped. The ghost never "
        "enters the code."),
    "rank": "senior",
}
