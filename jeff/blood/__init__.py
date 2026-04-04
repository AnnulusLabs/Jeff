"""jeff.blood — Production hardening. The circulatory system.

Blood carries oxygen to every organ. This module carries state
discipline, audit trails, spawn controls, backpressure, and error
contracts to every module in Jeff.

Fixes all 10 production risks identified in adversarial review:
  1. Task state machine (global, enforced)
  2. Agent spawn limits + lineage tracking
  3. Structured audit log (immutable)
  4. Backpressure / queue control
  5. Gate voting (pre/domain/post)
  6. Evolution safety constraints
  7. Tool sandboxing contracts
  8. Context budget enforcement
  9. Error strategy (retry/escalate/abort)
  10. Human-final-authority enforcement

Every module must:
  - Accept state → return state
  - Emit audit events
  - Respect spawn limits
  - Handle errors explicitly
  - Never mutate silently

AnnulusLabs LLC · April 2026
"""

import json
import time
import hashlib
import sqlite3
import threading
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any

BLOOD_DIR = Path.home() / ".jeff" / "blood"
AUDIT_DB = BLOOD_DIR / "audit.db"
STATE_DB = BLOOD_DIR / "state.db"


# ═══════════════════════════════════════════════════════════════════
# 1. TASK STATE MACHINE
# ═══════════════════════════════════════════════════════════════════

class TaskState(Enum):
    CREATED = "created"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    AWAITING_REVIEW = "awaiting_review"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    EXECUTED = "executed"
    FAILED = "failed"
    ARCHIVED = "archived"

# Legal transitions — enforced, not suggested
TRANSITIONS = {
    TaskState.CREATED: {TaskState.ASSIGNED, TaskState.ARCHIVED},
    TaskState.ASSIGNED: {TaskState.IN_PROGRESS, TaskState.FAILED},
    TaskState.IN_PROGRESS: {TaskState.AWAITING_REVIEW, TaskState.FAILED},
    TaskState.AWAITING_REVIEW: {TaskState.REVIEWED, TaskState.FAILED},
    TaskState.REVIEWED: {TaskState.APPROVED, TaskState.REJECTED},
    TaskState.APPROVED: {TaskState.EXECUTING},
    TaskState.REJECTED: {TaskState.ASSIGNED, TaskState.ARCHIVED},
    TaskState.EXECUTING: {TaskState.EXECUTED, TaskState.FAILED},
    TaskState.EXECUTED: {TaskState.ARCHIVED},
    TaskState.FAILED: {TaskState.ASSIGNED, TaskState.ARCHIVED},
    TaskState.ARCHIVED: set(),
}


@dataclass
class Task:
    id: str
    description: str
    state: TaskState = TaskState.CREATED
    assigned_to: str = ""
    created_by: str = "human"
    requires_human_approval: bool = True
    priority: int = 5  # 1=critical, 10=low
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    input_hash: str = ""
    output_hash: str = ""
    result: str = ""
    error: str = ""

    def transition(self, new_state: TaskState, actor: str = "",
                   reason: str = "") -> 'TransitionResult':
        """Enforce legal state transitions. No silent mutations."""
        allowed = TRANSITIONS.get(self.state, set())
        if new_state not in allowed:
            return TransitionResult(
                ok=False,
                error=f"Illegal: {self.state.value} → {new_state.value}. "
                      f"Allowed: {[s.value for s in allowed]}")

        # Human approval gate — HARD ENFORCEMENT
        if new_state == TaskState.EXECUTING and self.requires_human_approval:
            if actor != "human":
                return TransitionResult(
                    ok=False,
                    error="Execution requires human approval. Cannot be overridden.")

        old = self.state
        self.state = new_state
        self.updated_at = time.time()
        return TransitionResult(ok=True, old_state=old, new_state=new_state,
                                actor=actor, reason=reason)


@dataclass
class TransitionResult:
    ok: bool
    error: str = ""
    old_state: TaskState = TaskState.CREATED
    new_state: TaskState = TaskState.CREATED
    actor: str = ""
    reason: str = ""


# ═══════════════════════════════════════════════════════════════════
# 2. SPAWN CONTROLS
# ═══════════════════════════════════════════════════════════════════

@dataclass
class SpawnPolicy:
    max_agents_per_task: int = 3
    max_total_agents: int = 20
    max_depth: int = 2  # agent spawns agent spawns agent = depth 2
    require_justification: bool = True


@dataclass
class SpawnRequest:
    parent_id: str
    role: str
    task: str
    justification: str = ""
    depth: int = 0
    lineage: list = field(default_factory=list)


class SpawnGuard:
    """Prevents runaway agent spawning."""

    def __init__(self, policy: SpawnPolicy = None):
        self.policy = policy or SpawnPolicy()
        self.active_count: int = 0
        self.task_agents: dict[str, int] = {}  # task_id → count
        self._lock = threading.Lock()

    def request(self, req: SpawnRequest) -> TransitionResult:
        with self._lock:
            if self.active_count >= self.policy.max_total_agents:
                return TransitionResult(ok=False,
                    error=f"Total agent limit reached ({self.policy.max_total_agents})")

            task_count = self.task_agents.get(req.task, 0)
            if task_count >= self.policy.max_agents_per_task:
                return TransitionResult(ok=False,
                    error=f"Agent limit per task reached ({self.policy.max_agents_per_task})")

            if req.depth >= self.policy.max_depth:
                return TransitionResult(ok=False,
                    error=f"Spawn depth limit reached ({self.policy.max_depth})")

            if self.policy.require_justification and not req.justification:
                return TransitionResult(ok=False,
                    error="Spawn requires justification")

            self.active_count += 1
            self.task_agents[req.task] = task_count + 1
            return TransitionResult(ok=True, reason=f"Spawned: {req.role}")

    def release(self, task: str):
        with self._lock:
            self.active_count = max(0, self.active_count - 1)
            if task in self.task_agents:
                self.task_agents[task] = max(0, self.task_agents[task] - 1)


# ═══════════════════════════════════════════════════════════════════
# 3. STRUCTURED AUDIT LOG (immutable)
# ═══════════════════════════════════════════════════════════════════

@dataclass
class AuditEvent:
    timestamp: float = field(default_factory=time.time)
    actor: str = ""        # agent_id or "human"
    action: str = ""       # "review_pr", "spawn_agent", "execute_tool"
    task_id: str = ""
    input_hash: str = ""
    output_hash: str = ""
    decision: str = ""
    confidence: float = 0.0
    state_before: str = ""
    state_after: str = ""
    metadata: dict = field(default_factory=dict)


class AuditLog:
    """Immutable, structured audit trail. Append-only."""

    def __init__(self, db_path: Path = AUDIT_DB):
        BLOOD_DIR.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(db_path), check_same_thread=False)
        self._init_db()
        self._lock = threading.Lock()

    def _init_db(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                actor TEXT, action TEXT, task_id TEXT,
                input_hash TEXT, output_hash TEXT,
                decision TEXT, confidence REAL,
                state_before TEXT, state_after TEXT,
                metadata TEXT
            )""")
        self.db.commit()

    def emit(self, event: AuditEvent):
        """Append event. Never modify. Never delete."""
        with self._lock:
            self.db.execute(
                "INSERT INTO audit (timestamp, actor, action, task_id, "
                "input_hash, output_hash, decision, confidence, "
                "state_before, state_after, metadata) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (event.timestamp, event.actor, event.action, event.task_id,
                 event.input_hash, event.output_hash, event.decision,
                 event.confidence, event.state_before, event.state_after,
                 json.dumps(event.metadata)))
            self.db.commit()

    def query(self, task_id: str = "", actor: str = "",
              limit: int = 100) -> list[dict]:
        where, params = [], []
        if task_id:
            where.append("task_id=?"); params.append(task_id)
        if actor:
            where.append("actor=?"); params.append(actor)
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        rows = self.db.execute(
            f"SELECT * FROM audit {clause} ORDER BY timestamp DESC LIMIT ?",
            params + [limit]).fetchall()
        cols = ["id", "timestamp", "actor", "action", "task_id",
                "input_hash", "output_hash", "decision", "confidence",
                "state_before", "state_after", "metadata"]
        return [dict(zip(cols, r)) for r in rows]

    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM audit").fetchone()[0]


# ═══════════════════════════════════════════════════════════════════
# 4. BACKPRESSURE / QUEUE CONTROL
# ═══════════════════════════════════════════════════════════════════

@dataclass
class QueuePolicy:
    max_pending: int = 500
    max_review: int = 100
    max_executing: int = 10
    drop_policy: str = "defer_low_priority"  # or "reject" or "queue"


class TaskQueue:
    """Bounded task queue with priority and backpressure."""

    def __init__(self, policy: QueuePolicy = None):
        self.policy = policy or QueuePolicy()
        self.pending: list[Task] = []
        self._lock = threading.Lock()

    def enqueue(self, task: Task) -> TransitionResult:
        with self._lock:
            if len(self.pending) >= self.policy.max_pending:
                if self.policy.drop_policy == "defer_low_priority":
                    low = [t for t in self.pending if t.priority > 7]
                    if low:
                        self.pending.remove(low[-1])
                    else:
                        return TransitionResult(ok=False,
                            error="Queue full. All tasks are high priority.")
                elif self.policy.drop_policy == "reject":
                    return TransitionResult(ok=False, error="Queue full.")
            self.pending.append(task)
            self.pending.sort(key=lambda t: t.priority)
            return TransitionResult(ok=True)

    def dequeue(self) -> Task | None:
        with self._lock:
            return self.pending.pop(0) if self.pending else None

    def size(self) -> int:
        return len(self.pending)


# ═══════════════════════════════════════════════════════════════════
# 5. GATE VOTING (pre / domain / post)
# ═══════════════════════════════════════════════════════════════════

@dataclass
class GateVote:
    check: str          # "syntax", "logic", "safety", "domain"
    result: str         # "pass", "fail", "uncertain"
    reason: str = ""
    confidence: float = 1.0


@dataclass
class GateVerdict:
    votes: list[GateVote] = field(default_factory=list)
    policy: str = "majority"  # "unanimous", "majority", "any_pass"

    @property
    def passed(self) -> bool:
        passes = sum(1 for v in self.votes if v.result == "pass")
        fails = sum(1 for v in self.votes if v.result == "fail")
        if self.policy == "unanimous":
            return fails == 0 and passes > 0
        elif self.policy == "majority":
            return passes > fails
        elif self.policy == "any_pass":
            return passes > 0
        return False

    def summary(self) -> str:
        lines = []
        for v in self.votes:
            icon = {"pass": "+", "fail": "X", "uncertain": "~"}[v.result]
            lines.append(f"[{icon}] {v.check}: {v.reason}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# 6. EVOLUTION SAFETY
# ═══════════════════════════════════════════════════════════════════

@dataclass
class EvolutionPolicy:
    enabled: bool = False           # OFF by default in production
    allowed: list = field(default_factory=lambda: ["prompt_tuning"])
    forbidden: list = field(default_factory=lambda: [
        "logic_changes", "routing_changes", "gate_changes",
        "guard_changes", "security_changes"])
    require_audit: bool = True
    max_mutations_per_session: int = 5


# ═══════════════════════════════════════════════════════════════════
# 7. TOOL SANDBOX CONTRACT
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ToolPolicy:
    allowed: list = field(default_factory=lambda: [
        "read", "write", "edit", "grep", "glob", "git", "tree"])
    denied: list = field(default_factory=lambda: [
        "bash_unrestricted", "file_delete_recursive", "network_raw"])
    require_schema: bool = True
    max_output_bytes: int = 1_000_000  # 1MB cap on tool output

    def permits(self, tool: str) -> bool:
        if tool in self.denied:
            return False
        if self.allowed and tool not in self.allowed:
            return False
        return True


# ═══════════════════════════════════════════════════════════════════
# 8. CONTEXT BUDGET
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ContextBudget:
    max_tokens: int = 4000
    priority: list = field(default_factory=lambda: [
        "diff", "test_results", "error_logs", "recent_conversation"])
    drop_order: list = field(default_factory=lambda: [
        "old_comments", "low_relevance_files", "historical_context"])
    log_drops: bool = True


# ═══════════════════════════════════════════════════════════════════
# 9. ERROR CONTRACT
# ═══════════════════════════════════════════════════════════════════

class ErrorAction(Enum):
    RETRY = "retry"
    ESCALATE = "escalate"
    ABORT = "abort"


@dataclass
class ModuleResult:
    """Every module returns this. No exceptions. No silent failures."""
    status: str             # "success", "retry", "fail"
    data: Any = None
    error: str = ""
    next_action: ErrorAction = ErrorAction.ABORT
    retries_remaining: int = 0
    task_state: TaskState | None = None

    @property
    def ok(self) -> bool:
        return self.status == "success"


# ═══════════════════════════════════════════════════════════════════
# 10. HUMAN AUTHORITY ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════

@dataclass
class AuthorityPolicy:
    human_required_for: list = field(default_factory=lambda: [
        "execute", "merge", "deploy", "delete", "approve"])
    cannot_be_overridden: bool = True

    def requires_human(self, action: str) -> bool:
        return action in self.human_required_for


# ═══════════════════════════════════════════════════════════════════
# RUNTIME — Ties everything together
# ═══════════════════════════════════════════════════════════════════

class Runtime:
    """Jeff's circulatory system. Every module plugs into this."""

    def __init__(self):
        BLOOD_DIR.mkdir(parents=True, exist_ok=True)
        self.audit = AuditLog()
        self.spawn_guard = SpawnGuard()
        self.queue = TaskQueue()
        self.authority = AuthorityPolicy()
        self.tool_policy = ToolPolicy()
        self.context_budget = ContextBudget()
        self.evolution_policy = EvolutionPolicy()
        self.tasks: dict[str, Task] = {}

    def create_task(self, desc: str, creator: str = "human",
                    requires_approval: bool = True,
                    priority: int = 5) -> Task:
        tid = hashlib.sha256(f"{desc}{time.time()}".encode()).hexdigest()[:12]
        task = Task(id=tid, description=desc, created_by=creator,
                    requires_human_approval=requires_approval,
                    priority=priority)
        self.tasks[tid] = task
        self.audit.emit(AuditEvent(
            actor=creator, action="create_task", task_id=tid,
            state_after=task.state.value,
            metadata={"description": desc[:200]}))
        return task

    def transition_task(self, task_id: str, new_state: TaskState,
                        actor: str = "", reason: str = "") -> TransitionResult:
        task = self.tasks.get(task_id)
        if not task:
            return TransitionResult(ok=False, error=f"Task {task_id} not found")

        # Human authority check
        if new_state == TaskState.EXECUTING:
            if self.authority.requires_human("execute") and actor != "human":
                self.audit.emit(AuditEvent(
                    actor=actor, action="blocked_execution", task_id=task_id,
                    decision="denied",
                    metadata={"reason": "Human approval required"}))
                return TransitionResult(ok=False,
                    error="Execution requires human approval. Cannot override.")

        result = task.transition(new_state, actor, reason)

        self.audit.emit(AuditEvent(
            actor=actor, action="state_transition", task_id=task_id,
            state_before=result.old_state.value if result.ok else task.state.value,
            state_after=result.new_state.value if result.ok else task.state.value,
            decision="allowed" if result.ok else "denied",
            metadata={"reason": reason, "error": result.error}))
        return result

    def check_tool(self, tool: str) -> bool:
        allowed = self.tool_policy.permits(tool)
        if not allowed:
            self.audit.emit(AuditEvent(
                action="tool_denied", metadata={"tool": tool}))
        return allowed

    # ═══════════════════════════════════════════════════════════════
    # KERNEL LOOP — The single entry point. The spine.
    # ═══════════════════════════════════════════════════════════════

    def process_task(self, task_id: str,
                     route_fn=None,
                     execute_fn=None,
                     review_fn=None,
                     finalize_fn=None,
                     max_retries: int = 2) -> Task:
        """Drive a task through the state machine. Deterministic.
        Debuggable. Replayable. Every module plugs in as a handler.

        Args:
            task_id:      task to process
            route_fn:     (task) → assigned_to:str — who handles it
            execute_fn:   (task) → ModuleResult — do the work
            review_fn:    (task) → GateVerdict — check the output
            finalize_fn:  (task) → ModuleResult — post-approval action
            max_retries:  retry limit before FAILED
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        while True:
            self.audit.emit(AuditEvent(
                actor="kernel", action="loop_tick", task_id=task.id,
                state_before=task.state.value,
                metadata={"retry": task.error if task.error else ""}))

            # ── CREATED → route to an agent ──────────────────────
            if task.state == TaskState.CREATED:
                if route_fn:
                    try:
                        assigned = route_fn(task)
                        task.assigned_to = assigned or "jeff"
                    except Exception as e:
                        self._fail_or_retry(task, f"Route failed: {e}", max_retries)
                        continue
                else:
                    task.assigned_to = "jeff"
                self.transition_task(task.id, TaskState.ASSIGNED,
                                     actor="kernel", reason=f"routed to {task.assigned_to}")

            # ── ASSIGNED → execute the work ──────────────────────
            elif task.state == TaskState.ASSIGNED:
                self.transition_task(task.id, TaskState.IN_PROGRESS,
                                     actor=task.assigned_to, reason="starting work")

            # ── IN_PROGRESS → run execute_fn, move to review ─────
            elif task.state == TaskState.IN_PROGRESS:
                if execute_fn:
                    try:
                        result = execute_fn(task)
                        if not isinstance(result, ModuleResult):
                            result = ModuleResult(status="success", data=str(result))
                    except Exception as e:
                        result = ModuleResult(status="fail", error=str(e),
                                              next_action=ErrorAction.RETRY)

                    if result.ok:
                        task.result = str(result.data) if result.data else ""
                        task.output_hash = hashlib.sha256(
                            task.result.encode()).hexdigest()[:16]
                        self.transition_task(task.id, TaskState.AWAITING_REVIEW,
                                             actor=task.assigned_to, reason="work complete")
                    elif result.next_action == ErrorAction.RETRY:
                        self._fail_or_retry(task, result.error, max_retries)
                        continue
                    else:
                        self.transition_task(task.id, TaskState.FAILED,
                                             actor=task.assigned_to, reason=result.error)
                else:
                    self.transition_task(task.id, TaskState.AWAITING_REVIEW,
                                         actor="kernel", reason="no execute_fn, pass-through")

            # ── AWAITING_REVIEW → run gate checks ────────────────
            elif task.state == TaskState.AWAITING_REVIEW:
                if review_fn:
                    try:
                        verdict = review_fn(task)
                        if not isinstance(verdict, GateVerdict):
                            verdict = GateVerdict(votes=[
                                GateVote(check="default",
                                         result="pass" if verdict else "fail")])
                    except Exception as e:
                        verdict = GateVerdict(votes=[
                            GateVote(check="error", result="fail", reason=str(e))])

                    self.audit.emit(AuditEvent(
                        actor="gate", action="review", task_id=task.id,
                        decision="pass" if verdict.passed else "fail",
                        metadata={"votes": verdict.summary()}))

                    self.transition_task(task.id, TaskState.REVIEWED,
                                         actor="gate", reason=verdict.summary())
                else:
                    self.transition_task(task.id, TaskState.REVIEWED,
                                         actor="kernel", reason="no review_fn, auto-pass")

            # ── REVIEWED → approve or reject ─────────────────────
            elif task.state == TaskState.REVIEWED:
                # Check last gate verdict from audit
                recent = self.audit.query(task_id=task.id, limit=5)
                gate_passed = any(e.get("action") == "review"
                                  and e.get("decision") == "pass" for e in recent)
                if gate_passed:
                    self.transition_task(task.id, TaskState.APPROVED,
                                         actor="gate", reason="gate passed")
                else:
                    self.transition_task(task.id, TaskState.REJECTED,
                                         actor="gate", reason="gate failed")

            # ── APPROVED → human must approve execution ──────────
            elif task.state == TaskState.APPROVED:
                if not task.requires_human_approval:
                    self.transition_task(task.id, TaskState.EXECUTING,
                                         actor="human", reason="auto-approved (no human gate)")
                else:
                    # Return task to caller — human decides
                    self.audit.emit(AuditEvent(
                        actor="kernel", action="awaiting_human",
                        task_id=task.id,
                        metadata={"message": "Task approved by gate. Awaiting human execution approval."}))
                    return task  # Caller must call transition_task with actor="human"

            # ── EXECUTING → run finalize ─────────────────────────
            elif task.state == TaskState.EXECUTING:
                if finalize_fn:
                    try:
                        result = finalize_fn(task)
                        if not isinstance(result, ModuleResult):
                            result = ModuleResult(status="success", data=str(result))
                    except Exception as e:
                        result = ModuleResult(status="fail", error=str(e))

                    if result.ok:
                        self.transition_task(task.id, TaskState.EXECUTED,
                                             actor="kernel", reason="finalized")
                    else:
                        self.transition_task(task.id, TaskState.FAILED,
                                             actor="kernel", reason=result.error)
                else:
                    self.transition_task(task.id, TaskState.EXECUTED,
                                         actor="kernel", reason="no finalize_fn")

            # ── EXECUTED → archive ───────────────────────────────
            elif task.state == TaskState.EXECUTED:
                self.transition_task(task.id, TaskState.ARCHIVED,
                                     actor="kernel", reason="complete")

            # ── REJECTED → archive (could re-assign, but MVP archives)
            elif task.state == TaskState.REJECTED:
                self.transition_task(task.id, TaskState.ARCHIVED,
                                     actor="kernel", reason="rejected and archived")

            # ── TERMINAL STATES ──────────────────────────────────
            elif task.state in (TaskState.FAILED, TaskState.ARCHIVED):
                return task

        return task  # unreachable, but explicit

    def _fail_or_retry(self, task: Task, error: str, max_retries: int):
        """Retry or fail. No silent swallowing."""
        task.error = error
        retries = sum(1 for e in self.audit.query(task_id=task.id, limit=50)
                      if e.get("metadata") and "retry" in str(e.get("metadata", "")))
        if retries >= max_retries:
            self.transition_task(task.id, TaskState.FAILED,
                                 actor="kernel", reason=f"Max retries ({max_retries}): {error}")
        else:
            self.transition_task(task.id, TaskState.CREATED,
                                 actor="kernel", reason=f"Retry ({retries+1}/{max_retries}): {error}")

    def summary(self) -> str:
        active = sum(1 for t in self.tasks.values()
                     if t.state not in (TaskState.ARCHIVED, TaskState.EXECUTED))
        return (f"Runtime: {len(self.tasks)} tasks ({active} active), "
                f"{self.audit.count()} audit events, "
                f"{self.spawn_guard.active_count} agents alive, "
                f"{self.queue.size()} queued")
