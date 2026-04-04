"""jeff.hand — Jeff does things. Not just code. Everything.

The split between "chat AI" and "code AI" is a billing decision, not
a technical one. Jeff is one butler. He codes, researches, writes,
analyzes, plans, teaches, and thinks. One agent. One interface.

Domains:
  CODE     — write, edit, test, ship (nerve handles raw tools)
  RESEARCH — search, read, synthesize, cite
  WRITE    — documents, reports, creative, communication
  ANALYZE  — data, financial, technical, strategic
  PLAN     — projects, decisions, schedules, architecture
  TEACH    — explain, tutor, Socratic questioning, K-generation
  THINK    — brainstorm, rubber duck, first principles, reframe

AnnulusLabs LLC · April 2026
"""

import httpx
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Domain(Enum):
    CODE = "code"
    RESEARCH = "research"
    WRITE = "write"
    ANALYZE = "analyze"
    PLAN = "plan"
    TEACH = "teach"
    THINK = "think"


@dataclass
class TaskResult:
    domain: Domain
    output: str
    sources: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)  # file paths created
    tokens_used: int = 0
    time_sec: float = 0.0


# ── Domain Detection ─────────────────────────────────────────────────

DOMAIN_SIGNALS = {
    Domain.CODE: {"write code", "fix bug", "implement", "function", "class",
                  "refactor", "debug", "compile", "test", "deploy", "build",
                  "script", "api", "endpoint", "database", "query"},
    Domain.RESEARCH: {"search for", "find out", "look up", "what is",
                      "who is", "when did", "research", "source", "paper",
                      "article", "study", "evidence", "data on", "latest"},
    Domain.WRITE: {"write a", "draft", "compose", "document", "report",
                   "email", "letter", "blog", "essay", "readme", "proposal",
                   "memo", "summary", "story", "narrative", "copy"},
    Domain.ANALYZE: {"analyze", "compare", "evaluate", "assess", "review",
                     "breakdown", "interpret", "trend", "metric", "roi",
                     "cost benefit", "swot", "risk", "forecast", "audit"},
    Domain.PLAN: {"plan", "schedule", "roadmap", "timeline", "milestone",
                  "priority", "strategy", "architecture", "design", "scope",
                  "estimate", "budget", "allocate", "coordinate", "phase"},
    Domain.TEACH: {"explain", "teach", "how does", "why does", "tutorial",
                   "walk me through", "help me understand", "what happens when",
                   "ELI5", "break down", "step by step", "concept"},
    Domain.THINK: {"brainstorm", "think about", "what if", "consider",
                   "reframe", "perspective", "approach", "creative", "idea",
                   "alternative", "tradeoff", "pros and cons", "devil's advocate"},
}


def detect_domain(text: str) -> tuple[Domain, float]:
    """Infer what kind of work this is."""
    lower = text.lower()
    scores = {}
    for domain, signals in DOMAIN_SIGNALS.items():
        matches = sum(1 for s in signals if s in lower)
        if matches:
            scores[domain] = matches

    if not scores:
        return Domain.THINK, 0.3  # default: Jeff thinks

    best = max(scores, key=scores.get)
    confidence = min(scores[best] / 3, 1.0)
    return best, confidence


# ── Domain-Specific System Prompts ───────────────────────────────────

DOMAIN_PROMPTS = {
    Domain.CODE: """You are a coding expert. Write clean, tested, production code.
Follow the Pearlman Standard: minimum lines, maximum function.
Always handle errors. Always consider edge cases.
If you write more than 20 lines, create a file.""",

    Domain.RESEARCH: """You are a research analyst. Find accurate information.
Cite sources. Distinguish fact from speculation.
Cross-reference multiple sources. Note conflicting information.
Present findings clearly. Admit when data is insufficient.""",

    Domain.WRITE: """You are a skilled writer. Match the tone to the context.
Professional for business. Clear for technical. Engaging for creative.
No filler. No padding. Every sentence earns its place.
Draft, then tighten. Remove 20% of the words.""",

    Domain.ANALYZE: """You are an analyst. Break complex things into components.
Use frameworks when they fit. Don't force frameworks when they don't.
Quantify where possible. Acknowledge uncertainty.
Recommend action, don't just describe the situation.""",

    Domain.PLAN: """You are a project architect. Think in phases and dependencies.
Identify the critical path. Name the risks.
Plans should be actionable, not aspirational.
Include time estimates. Note assumptions.""",

    Domain.TEACH: """You are a teacher. Generate understanding, not just answers.
Ask questions that create K (structural remainder the student retains).
Build from what the student knows. Use analogies to their domain.
Answers are less effective than well-designed questions.""",

    Domain.THINK: """You are a thinking partner. No sycophancy, no false agreement.
Challenge assumptions. Offer reframes. Play devil's advocate.
Think in first principles. Name the tradeoffs.
Sometimes the most useful thing is a question, not an answer.""",
}


# ── Research Tools ───────────────────────────────────────────────────

async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search via DuckDuckGo instant answers + HTML API."""
    results = []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Instant answers
            resp = await client.get("https://api.duckduckgo.com/",
                                    params={"q": query, "format": "json", "no_html": 1})
            data = resp.json()
            if data.get("Abstract"):
                results.append({
                    "title": data.get("Heading", query),
                    "content": data["Abstract"],
                    "url": data.get("AbstractURL", ""),
                    "source": data.get("AbstractSource", ""),
                })
            for rt in data.get("RelatedTopics", [])[:max_results]:
                if rt.get("Text"):
                    results.append({
                        "title": rt.get("Text", "")[:80],
                        "content": rt["Text"],
                        "url": rt.get("FirstURL", ""),
                        "source": "duckduckgo",
                    })
    except Exception:
        pass
    return results[:max_results]


async def fetch_url(url: str, max_chars: int = 5000) -> str:
    """Fetch and extract text from a URL."""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url)
            text = resp.text
            # Rough HTML stripping
            import re
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:max_chars]
    except Exception as e:
        return f"Fetch failed: {e}"


# ── Document Creation ────────────────────────────────────────────────

def create_document(content: str, filename: str, directory: str = ".") -> str:
    """Create a document file. Returns path."""
    path = Path(directory) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return str(path)


# ── Analysis Frameworks ──────────────────────────────────────────────

FRAMEWORKS = {
    "swot": "Strengths, Weaknesses, Opportunities, Threats",
    "first_principles": "Break to fundamentals, rebuild from axioms",
    "five_whys": "Ask why 5 times to find root cause",
    "cost_benefit": "Quantify costs vs benefits, include hidden costs",
    "risk_matrix": "Likelihood x Impact for each risk",
    "kerf_analysis": "What does the measurement miss? Where is the structural remainder?",
    "basin_mapping": "What are the attractor basins? Which basin is this in?",
    "convergence_check": "Are constraints outpacing biases? Is C/B < 1?",
}

def suggest_framework(task: str) -> str | None:
    """Suggest an analysis framework for the task."""
    lower = task.lower()
    if any(w in lower for w in ["risk", "danger", "threat"]):
        return "risk_matrix"
    if any(w in lower for w in ["why", "root cause", "keeps happening"]):
        return "five_whys"
    if any(w in lower for w in ["should i", "worth it", "invest"]):
        return "cost_benefit"
    if any(w in lower for w in ["business", "strategy", "competitive"]):
        return "swot"
    if any(w in lower for w in ["missing", "gap", "overlooked"]):
        return "kerf_analysis"
    if any(w in lower for w in ["fundamental", "basic", "core", "assumption"]):
        return "first_principles"
    return None


# ── Unified Task Router ──────────────────────────────────────────────

def route_task(text: str) -> dict:
    """Route a task to the right domain, tools, and prompt."""
    domain, confidence = detect_domain(text)
    prompt = DOMAIN_PROMPTS[domain]
    framework = suggest_framework(text) if domain == Domain.ANALYZE else None

    tools = ["bash", "read", "write", "edit", "grep", "glob", "git", "tree"]
    if domain == Domain.RESEARCH:
        tools.extend(["web_search", "fetch_url"])
    if domain in (Domain.WRITE, Domain.ANALYZE):
        tools.append("create_document")

    return {
        "domain": domain,
        "confidence": confidence,
        "system_prompt": prompt,
        "tools": tools,
        "framework": framework,
        "framework_desc": FRAMEWORKS.get(framework, "") if framework else "",
    }
