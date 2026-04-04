"""jeff.hand.pulse — Agentic drift monitor.

Watches the goal-to-action ratio. If an agent exceeds N sub-steps
without measurable progress toward the primary basin, Jeff pauses.

"I'm in a rabbit hole. Should I keep digging or reset?"

Gripe #21: Complex agent loops get lost in sub-tasks.

AnnulusLabs LLC · April 2026
"""

import time
from dataclasses import dataclass, field


@dataclass
class GoalState:
    """Tracks progress toward a goal."""
    goal: str
    steps_taken: int = 0
    steps_since_progress: int = 0
    last_progress: float = field(default_factory=time.time)
    checkpoints: list = field(default_factory=list)
    stalled: bool = False
    max_drift: int = 5


@dataclass
class ProgressSignal:
    """Evidence of forward motion."""
    description: str
    metric: str = ""       # "files_changed", "tests_passed", "lines_written"
    value: float = 0.0
    timestamp: float = field(default_factory=time.time)


class PulseMonitor:
    """Monitors agent progress. Catches drift before it wastes compute."""

    def __init__(self, max_drift: int = 5, max_time_minutes: float = 10.0):
        self.max_drift = max_drift
        self.max_time = max_time_minutes * 60
        self.goals: dict[str, GoalState] = {}

    def start(self, task_id: str, goal: str) -> GoalState:
        state = GoalState(goal=goal, max_drift=self.max_drift)
        self.goals[task_id] = state
        return state

    def step(self, task_id: str, description: str = "") -> GoalState:
        """Record a step. Increments drift counter."""
        state = self.goals.get(task_id)
        if not state:
            return GoalState(goal="unknown")
        state.steps_taken += 1
        state.steps_since_progress += 1
        state.stalled = state.steps_since_progress >= state.max_drift
        return state

    def progress(self, task_id: str, signal: ProgressSignal) -> GoalState:
        """Record measurable progress. Resets drift counter."""
        state = self.goals.get(task_id)
        if not state:
            return GoalState(goal="unknown")
        state.checkpoints.append(signal)
        state.steps_since_progress = 0
        state.last_progress = signal.timestamp
        state.stalled = False
        return state

    def check(self, task_id: str) -> dict:
        """Check if agent is drifting. Returns diagnosis."""
        state = self.goals.get(task_id)
        if not state:
            return {"status": "unknown", "task_id": task_id}

        elapsed = time.time() - state.last_progress
        time_stalled = elapsed > self.max_time

        if state.stalled or time_stalled:
            return {
                "status": "stalled",
                "task_id": task_id,
                "goal": state.goal,
                "steps_taken": state.steps_taken,
                "steps_since_progress": state.steps_since_progress,
                "seconds_since_progress": round(elapsed),
                "checkpoints": len(state.checkpoints),
                "message": (f"Rabbit hole detected. {state.steps_since_progress} steps "
                           f"without progress toward: {state.goal}. "
                           f"Keep digging or reset?")
            }

        return {
            "status": "on_track",
            "task_id": task_id,
            "goal": state.goal,
            "steps_taken": state.steps_taken,
            "drift_ratio": state.steps_since_progress / max(1, state.max_drift),
            "checkpoints": len(state.checkpoints),
        }

    def reset(self, task_id: str, new_goal: str = "") -> GoalState:
        """Reset after a stall. Optionally redirect."""
        state = self.goals.get(task_id)
        if not state:
            return GoalState(goal=new_goal or "unknown")
        state.steps_since_progress = 0
        state.stalled = False
        state.last_progress = time.time()
        if new_goal:
            state.goal = new_goal
            state.checkpoints.append(
                ProgressSignal(description=f"Redirected to: {new_goal}"))
        return state

    def summary(self) -> str:
        lines = [f"PULSE: {len(self.goals)} goals tracked"]
        for tid, state in self.goals.items():
            status = "STALLED" if state.stalled else "ok"
            lines.append(f"  [{status:<7s}] {tid}: {state.goal[:50]} "
                        f"({state.steps_taken} steps, "
                        f"{state.steps_since_progress} since progress)")
        return "\n".join(lines)
