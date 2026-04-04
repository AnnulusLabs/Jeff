"""jeff.staff — Multi-agent orchestration. Hire with purpose.

You don't spin up a blank agent and then explain the job.
You birth it with a role, a task, tools, and context.
WEIGHTS (experience) accumulate. The JOB was there from birth.

Household staff metaphor:
  Intern   — new, supervised, limited tools
  Junior   — capable, some autonomy
  Staff    — full capability, trusted
  Senior   — mentors others, complex tasks
  Head     — oversees operations

Birth template:
  role     — what job this agent does
  task     — specific current assignment
  tools    — which nerve tools it can use
  context  — preloaded L2 knowledge for its domain
  model    — which pantry model to use
  gate     — quality threshold before output accepted
  budget   — token/time limit
  reports_to — which agent or human reviews its work

AnnulusLabs LLC · April 2026
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class Rank(Enum):
    INTERN = "intern"
    JUNIOR = "junior"
    STAFF = "staff"
    SENIOR = "senior"
    HEAD = "head"


class Status(Enum):
    IDLE = "idle"
    WORKING = "working"
    BLOCKED = "blocked"
    DONE = "done"
    FAILED = "failed"


@dataclass
class BirthCert:
    """What an agent is born with. The job, not the experience."""
    role: str                          # "researcher", "coder", "writer", "analyst"
    task: str                          # specific current assignment
    model: str = "hermes3:8b"          # pantry model
    tools: list[str] = field(default_factory=lambda: ["bash", "read", "write", "edit"])
    context: str = ""                  # preloaded domain knowledge
    system_prompt: str = ""            # role-specific personality
    rank: Rank = Rank.STAFF
    budget_tokens: int = 50000         # token ceiling
    budget_seconds: int = 300          # time ceiling
    reports_to: str = "human"          # who reviews output
    gate_threshold: float = 0.7        # quality gate minimum


# ── Pre-built Birth Templates ────────────────────────────────────────

TEMPLATES = {
    "coder": BirthCert(
        role="coder",
        task="",
        tools=["bash", "read", "write", "edit", "grep", "glob", "git", "tree"],
        system_prompt=("You write clean, tested code. Pearlman Standard: "
                       "minimum lines, maximum function. Handle errors. "
                       "No sycophancy. If it's wrong, say so."),
        rank=Rank.STAFF,
    ),
    "researcher": BirthCert(
        role="researcher",
        task="",
        tools=["bash", "read", "write", "web_search", "fetch_url"],
        system_prompt=("You find accurate information. Cite sources. "
                       "Distinguish fact from speculation. Cross-reference. "
                       "Admit when data is insufficient."),
        rank=Rank.STAFF,
    ),
    "writer": BirthCert(
        role="writer",
        task="",
        tools=["read", "write"],
        system_prompt=("You write clearly. Match tone to context. "
                       "No filler. Every sentence earns its place. "
                       "Draft, then cut 20%."),
        rank=Rank.STAFF,
    ),
    "reviewer": BirthCert(
        role="reviewer",
        task="",
        tools=["read", "grep", "glob"],
        system_prompt=("You review work honestly. Find what's wrong. "
                       "Don't soften it. Suggest fixes, not just problems. "
                       "If it's good, say so briefly and move on."),
        rank=Rank.SENIOR,
    ),
    "planner": BirthCert(
        role="planner",
        task="",
        tools=["read", "write"],
        system_prompt=("You think in phases and dependencies. "
                       "Identify the critical path. Name risks. "
                       "Plans are actionable, not aspirational."),
        rank=Rank.SENIOR,
    ),
    "scout": BirthCert(
        role="scout",
        task="",
        tools=["bash", "web_search", "fetch_url", "read"],
        system_prompt=("You explore and report back. Find what others miss. "
                       "Look in unusual places. The kerf between sources "
                       "is where the signal hides."),
        rank=Rank.JUNIOR,
    ),
}


@dataclass
class Agent:
    """A living staff member. Born with purpose, accumulates experience."""
    id: str = ""
    birth: BirthCert = field(default_factory=BirthCert)
    status: Status = Status.IDLE
    output: str = ""
    errors: list[str] = field(default_factory=list)
    tokens_used: int = 0
    time_started: float = 0.0
    time_finished: float = 0.0
    k_generated: list[str] = field(default_factory=list)  # lessons learned

    def __post_init__(self):
        if not self.id:
            self.id = f"{self.birth.role}_{uuid.uuid4().hex[:8]}"

    @property
    def elapsed(self) -> float:
        if self.time_finished:
            return self.time_finished - self.time_started
        if self.time_started:
            return time.time() - self.time_started
        return 0

    @property
    def over_budget(self) -> bool:
        return (self.tokens_used > self.birth.budget_tokens or
                self.elapsed > self.birth.budget_seconds)


def birth(template: str, task: str, **overrides) -> Agent:
    """Birth an agent from a template with a specific task.

    Usage:
        agent = birth("coder", "fix the auth bug in login.py")
        agent = birth("researcher", "find recent papers on MoE abliteration")
        agent = birth("reviewer", "review the jeff/guard module", model="deepseek-r1:14b")
    """
    if template in TEMPLATES:
        cert = BirthCert(
            role=TEMPLATES[template].role,
            task=task,
            model=overrides.get("model", TEMPLATES[template].model),
            tools=overrides.get("tools", TEMPLATES[template].tools.copy()),
            context=overrides.get("context", TEMPLATES[template].context),
            system_prompt=TEMPLATES[template].system_prompt,
            rank=overrides.get("rank", TEMPLATES[template].rank),
            budget_tokens=overrides.get("budget_tokens", TEMPLATES[template].budget_tokens),
            budget_seconds=overrides.get("budget_seconds", TEMPLATES[template].budget_seconds),
            reports_to=overrides.get("reports_to", TEMPLATES[template].reports_to),
            gate_threshold=overrides.get("gate_threshold", TEMPLATES[template].gate_threshold),
        )
    else:
        cert = BirthCert(role=template, task=task, **overrides)

    return Agent(birth=cert)


# ── Staff Roster ─────────────────────────────────────────────────────

class Staff:
    """Manages the household. Hires, assigns, coordinates."""

    def __init__(self):
        self.roster: dict[str, Agent] = {}
        self.completed: list[Agent] = []

    def hire(self, template: str, task: str, **overrides) -> Agent:
        """Birth and register an agent."""
        agent = birth(template, task, **overrides)
        self.roster[agent.id] = agent
        return agent

    def fire(self, agent_id: str):
        """Remove from active roster, preserve history."""
        agent = self.roster.pop(agent_id, None)
        if agent:
            self.completed.append(agent)

    def find(self, role: str = None, status: Status = None) -> list[Agent]:
        """Find agents by role or status."""
        results = list(self.roster.values())
        if role:
            results = [a for a in results if a.birth.role == role]
        if status:
            results = [a for a in results if a.status == status]
        return results

    def idle(self) -> list[Agent]:
        return self.find(status=Status.IDLE)

    def working(self) -> list[Agent]:
        return self.find(status=Status.WORKING)

    async def assign(self, agent_id: str, work_fn: Callable) -> Agent:
        """Assign work to an agent. work_fn receives the agent."""
        agent = self.roster.get(agent_id)
        if not agent:
            raise ValueError(f"No agent {agent_id}")

        agent.status = Status.WORKING
        agent.time_started = time.time()
        try:
            agent.output = await _call(work_fn, agent)
            agent.status = Status.DONE
        except Exception as e:
            agent.errors.append(str(e))
            agent.status = Status.FAILED
            agent.k_generated.append(f"Failed: {e}")
        agent.time_finished = time.time()
        return agent

    async def team_task(self, task: str, roles: list[str],
                        work_fn: Callable) -> list[Agent]:
        """Hire a team, run them in parallel on the same task."""
        agents = [self.hire(role, task) for role in roles]
        tasks = [self.assign(a.id, work_fn) for a in agents]
        return await asyncio.gather(*tasks)

    async def pipeline(self, task: str, steps: list[tuple[str, Callable]]):
        """Sequential pipeline: each step's output feeds the next."""
        current_input = task
        results = []
        for role, work_fn in steps:
            agent = self.hire(role, current_input)
            agent = await self.assign(agent.id, work_fn)
            results.append(agent)
            if agent.status == Status.FAILED:
                break
            current_input = agent.output
        return results

    def summary(self) -> str:
        active = len(self.roster)
        by_status = {}
        for a in self.roster.values():
            by_status.setdefault(a.status.value, []).append(a)

        lines = [f"STAFF: {active} active, {len(self.completed)} completed"]
        for status, agents in by_status.items():
            for a in agents:
                budget = f"{a.tokens_used}/{a.birth.budget_tokens}t"
                lines.append(f"  [{status:<8s}] {a.id:<30s} {budget}")
        return "\n".join(lines)


async def _call(fn, *args):
    if asyncio.iscoroutinefunction(fn):
        return await fn(*args)
    return fn(*args)
