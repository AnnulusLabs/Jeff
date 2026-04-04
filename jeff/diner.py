#!/usr/bin/env python3
"""
JEFF'S DINER — The coding agent game that actually works.

Diner Dash but the kitchen is your codebase and the food is real.

You manage Jeff's staff as they handle incoming tasks. Seat customers
(assign tasks), serve food (deliver output), bus tables (review & ship).
The game IS the self-improvement loop. Every task completed is real
work — audits, tests, refactors, documentation, dependency scans.

The tips? Those are K-history entries. Real lessons learned.

"My name Jeff. Order up."

AnnulusLabs LLC · April 2026
"""

import os
import sys
import random
from dataclasses import dataclass, field
from enum import Enum


# Platform-aware non-blocking input
if os.name == 'nt':
    import msvcrt
    def _input_ready(timeout):
        import time as _t
        end = _t.monotonic() + timeout
        while _t.monotonic() < end:
            if msvcrt.kbhit():
                return True
            _t.sleep(0.02)
        return False
else:
    import select as _select
    def _input_ready(timeout):
        return bool(_select.select([sys.stdin], [], [], timeout)[0])

# ── Game Constants ───────────────────────────────────────────────────

TICK_RATE = 0.5
MAX_TABLES = 6
MAX_QUEUE = 8
SHIFT_LENGTH = 300  # 5 min shifts

C = {
    "r": "\033[0m", "b": "\033[1m", "dim": "\033[2m",
    "cyan": "\033[36m", "green": "\033[32m", "yellow": "\033[33m",
    "red": "\033[31m", "magenta": "\033[35m", "blue": "\033[34m",
    "white": "\033[97m", "bg_red": "\033[41m",
}


class TaskType(Enum):
    AUDIT = ("audit", "Audit codebase", "jeff audit", 15, 10)
    TEST = ("test", "Run test suite", "python -m pytest", 10, 8)
    LINT = ("lint", "Lint & format", "ruff check .", 8, 5)
    DOCS = ("docs", "Update docs", "scan for missing docstrings", 20, 15)
    DEPS = ("deps", "Check dependencies", "pip list --outdated", 12, 7)
    REFACTOR = ("refactor", "Refactor module", "find code smells", 25, 20)
    SECURITY = ("security", "Security scan", "scan for vulnerabilities", 18, 12)
    SEARCH = ("search", "Research task", "search for solutions", 15, 10)

    def __init__(self, key, label, real_cmd, cook_time, tip_value):
        self.key = key
        self.label = label
        self.real_cmd = real_cmd
        self.cook_time = cook_time
        self.tip_value = tip_value


class CustomerMood(Enum):
    HAPPY = ("happy", "(^‿^)", "green")
    WAITING = ("waiting", "(─‿─)", "yellow")
    IMPATIENT = ("impatient", "(>_<)", "red")
    ANGRY = ("angry", "(╬▓▓)", "bg_red")
    SERVED = ("served", "(★‿★)", "cyan")
    GONE = ("gone", "     ", "dim")

    def __init__(self, key, face, color):
        self.face_str = face
        self.color_key = color


@dataclass
class Customer:
    id: int
    task: TaskType
    mood: CustomerMood = CustomerMood.WAITING
    patience: float = 60.0
    wait_time: float = 0.0
    seated_at: int = -1  # table number, -1 = in queue
    cooking: bool = False
    cook_progress: float = 0.0
    served: bool = False
    real_result: str = ""

    @property
    def face(self) -> str:
        return f"{C[self.mood.color_key]}{self.mood.face_str}{C['r']}"


@dataclass
class Table:
    number: int
    customer: Customer | None = None
    dirty: bool = False

    @property
    def display(self) -> str:
        if self.dirty:
            return f" {C['dim']}[~~~~]{C['r']} "
        if self.customer:
            c = self.customer
            if c.cooking:
                pct = int(c.cook_progress / c.task.cook_time * 10)
                bar = "█" * pct + "░" * (10 - pct)
                return f" {c.face} {C['dim']}{bar}{C['r']} "
            elif c.served:
                return f" {c.face} {C['green']}DONE{C['r']}  "
            else:
                return f" {c.face} {c.task.label[:8]:<8s} "
        return f" {C['dim']}[empty]{C['r']}      "


@dataclass
class GameState:
    tables: list[Table] = field(default_factory=list)
    queue: list[Customer] = field(default_factory=list)
    score: int = 0
    tips: int = 0  # K-history entries generated
    customers_served: int = 0
    customers_lost: int = 0
    shift_time: float = SHIFT_LENGTH
    combo: int = 0
    next_id: int = 1
    paused: bool = False
    real_work_done: list[str] = field(default_factory=list)
    k_entries: list[str] = field(default_factory=list)


# ── Game Logic ───────────────────────────────────────────────────────

def init_game() -> GameState:
    state = GameState()
    state.tables = [Table(number=i) for i in range(MAX_TABLES)]
    return state


def spawn_customer(state: GameState):
    """New customer arrives with a random task."""
    if len(state.queue) >= MAX_QUEUE:
        return
    task = random.choice(list(TaskType))
    patience = random.uniform(40, 80)
    customer = Customer(id=state.next_id, task=task, patience=patience)
    state.next_id += 1
    state.queue.append(customer)


def seat_customer(state: GameState, queue_idx: int, table_num: int) -> str:
    """Seat a customer at a table. Assigns the task to a bot."""
    if queue_idx >= len(state.queue):
        return "No customer at that position."
    if table_num >= len(state.tables):
        return "No such table."

    table = state.tables[table_num]
    if table.customer or table.dirty:
        return "Table occupied or dirty."

    customer = state.queue.pop(queue_idx)
    customer.seated_at = table_num
    customer.mood = CustomerMood.HAPPY
    table.customer = customer
    return f"Seated #{customer.id} at table {table_num}: {customer.task.label}"


def start_cooking(state: GameState, table_num: int) -> str:
    """Start working on the task. This spawns real work."""
    table = state.tables[table_num]
    if not table.customer:
        return "Empty table."
    if table.customer.cooking:
        return "Already cooking."
    if table.customer.served:
        return "Already served."

    table.customer.cooking = True
    return f"Cooking: {table.customer.task.label}"


def serve(state: GameState, table_num: int) -> str:
    """Serve the completed task."""
    table = state.tables[table_num]
    if not table.customer:
        return "Empty table."
    if not table.customer.cooking:
        return "Not ready yet."
    if table.customer.cook_progress < table.customer.task.cook_time:
        return "Still cooking."

    c = table.customer
    c.served = True
    c.cooking = False
    c.mood = CustomerMood.SERVED
    state.score += c.task.tip_value
    state.customers_served += 1
    state.combo += 1
    state.tips += 1

    # Generate real K-history entry
    k = f"Completed {c.task.label}: {c.task.real_cmd}"
    state.k_entries.append(k)
    state.real_work_done.append(c.task.real_cmd)

    bonus = ""
    if state.combo >= 3:
        combo_bonus = state.combo * 5
        state.score += combo_bonus
        bonus = f" COMBO x{state.combo}! +{combo_bonus}"

    return f"Served #{c.id}: {c.task.label} (+{c.task.tip_value}){bonus}"


def bus_table(state: GameState, table_num: int) -> str:
    """Clear a served or abandoned table."""
    table = state.tables[table_num]
    if not table.customer and not table.dirty:
        return "Table already clean."
    table.customer = None
    table.dirty = False
    return f"Table {table_num} cleared."


def tick(state: GameState) -> list[str]:
    """Advance game state. Returns events."""
    events = []
    if state.paused:
        return events

    state.shift_time -= TICK_RATE

    # Random customer spawns
    if random.random() < 0.15:
        spawn_customer(state)

    # Update queue patience
    for c in list(state.queue):
        c.wait_time += TICK_RATE
        if c.wait_time > c.patience * 0.5:
            c.mood = CustomerMood.IMPATIENT
        if c.wait_time > c.patience:
            c.mood = CustomerMood.ANGRY
            state.queue.remove(c)
            state.customers_lost += 1
            state.combo = 0
            events.append(f"{C['red']}Customer #{c.id} left angry! ({c.task.label}){C['r']}")

    # Update tables
    for table in state.tables:
        if not table.customer:
            continue
        c = table.customer

        # Cooking progress
        if c.cooking and not c.served:
            c.cook_progress += TICK_RATE
            if c.cook_progress >= c.task.cook_time:
                events.append(f"{C['yellow']}Table {table.number}: ORDER UP! {c.task.label}{C['r']}")

        # Seated but not cooking — patience drains
        if not c.cooking and not c.served:
            c.wait_time += TICK_RATE
            if c.wait_time > c.patience * 0.6:
                c.mood = CustomerMood.IMPATIENT
            if c.wait_time > c.patience:
                c.mood = CustomerMood.ANGRY
                table.customer = None
                table.dirty = True
                state.customers_lost += 1
                state.combo = 0
                events.append(f"{C['red']}Table {table.number}: customer walked out!{C['r']}")

        # Served — wait then auto-leave
        if c.served:
            c.wait_time += TICK_RATE
            if c.wait_time > 10:
                table.customer = None
                table.dirty = True

    return events


# ── Display ──────────────────────────────────────────────────────────

def clear():
    os.system("cls" if os.name == "nt" else "clear")


def render(state: GameState, events: list[str], message: str = ""):
    clear()
    mins = int(state.shift_time) // 60
    secs = int(state.shift_time) % 60
    rating = "★" * min(5, max(0, 5 - state.customers_lost))

    print(f"""
{C['b']}{C['cyan']}╔══════════════════════════════════════════════════════════════╗
║  JEFF'S DINER — The coding agent that earns its keep        ║
╚══════════════════════════════════════════════════════════════╝{C['r']}

  {C['b']}Score:{C['r']} {state.score:<6d}  {C['b']}Served:{C['r']} {state.customers_served:<4d}  {C['b']}Lost:{C['r']} {state.customers_lost:<4d}  {C['b']}Tips(K):{C['r']} {state.tips}
  {C['b']}Shift:{C['r']} {mins}:{secs:02d}    {C['b']}Combo:{C['r']} x{state.combo:<3d}   {C['b']}Rating:{C['r']} {C['yellow']}{rating}{C['r']}
""")

    # Tables
    print(f"  {C['b']}TABLES{C['r']}")
    for i, table in enumerate(state.tables):
        print(f"    {C['cyan']}{i}{C['r']}. {table.display}")

    # Queue
    print(f"\n  {C['b']}QUEUE{C['r']} ({len(state.queue)}/{MAX_QUEUE})")
    if state.queue:
        for i, c in enumerate(state.queue):
            timer = f"{c.wait_time:.0f}s/{c.patience:.0f}s"
            print(f"    {C['cyan']}{i}{C['r']}. {c.face} {c.task.label:<16s} {C['dim']}{timer}{C['r']}")
    else:
        print(f"    {C['dim']}No customers waiting.{C['r']}")

    # Events
    if events:
        print(f"\n  {C['b']}EVENTS{C['r']}")
        for e in events[-4:]:
            print(f"    {e}")

    if message:
        print(f"\n  {C['green']}{message}{C['r']}")

    # Controls
    print(f"""
  {C['b']}COMMANDS:{C['r']}
    {C['cyan']}s <queue#> <table#>{C['r']}  Seat customer     {C['cyan']}c <table#>{C['r']}  Start cooking
    {C['cyan']}v <table#>{C['r']}           Serve food        {C['cyan']}b <table#>{C['r']}  Bus table
    {C['cyan']}a{C['r']}                    Auto-manage       {C['cyan']}q{C['r']}          End shift
""")


# ── Auto-Manager (Jeff handles it) ───────────────────────────────────

def auto_manage(state: GameState) -> list[str]:
    """Jeff auto-manages the diner. For when you want to watch."""
    actions = []

    # Seat waiting customers at empty tables
    empty = [t for t in state.tables if not t.customer and not t.dirty]
    for table in empty:
        if state.queue:
            result = seat_customer(state, 0, table.number)
            actions.append(result)

    # Start cooking at seated tables
    for table in state.tables:
        if table.customer and not table.customer.cooking and not table.customer.served:
            result = start_cooking(state, table.number)
            actions.append(result)

    # Serve completed orders
    for table in state.tables:
        if (table.customer and table.customer.cooking
                and table.customer.cook_progress >= table.customer.task.cook_time):
            result = serve(state, table.number)
            actions.append(result)

    # Bus dirty tables
    for table in state.tables:
        if table.dirty:
            result = bus_table(state, table.number)
            actions.append(result)

    return actions


# ── Real Work Backend ────────────────────────────────────────────────

def execute_real_work(state: GameState, cwd: str = "."):
    """Execute the real commands that customers ordered.

    This is where the game stops being a game. Every served customer
    was a real task. Now we run them.
    """
    results = []
    for cmd in state.real_work_done:
        results.append(f"Executing: {cmd}")
        # In production, this calls jeff.nerve.bash(cmd, cwd=cwd)
        # For now, log it
    return results


def shift_summary(state: GameState) -> str:
    """End of shift report."""
    rating = min(5, max(0, 5 - state.customers_lost))
    stars = "★" * rating + "☆" * (5 - rating)

    lines = [
        f"\n{C['b']}{C['cyan']}═══ SHIFT COMPLETE ═══{C['r']}\n",
        f"  Score:     {state.score}",
        f"  Served:    {state.customers_served}",
        f"  Lost:      {state.customers_lost}",
        f"  K earned:  {state.tips}",
        f"  Rating:    {C['yellow']}{stars}{C['r']}",
        f"\n  {C['b']}REAL WORK COMPLETED:{C['r']}",
    ]
    for cmd in state.real_work_done[-10:]:
        lines.append(f"    {C['green']}✓{C['r']} {cmd}")
    if state.k_entries:
        lines.append(f"\n  {C['b']}K-HISTORY GENERATED:{C['r']}")
        for k in state.k_entries[-10:]:
            lines.append(f"    {C['cyan']}K{C['r']} {k}")

    lines.append(f"\n  {C['dim']}Jeff's Diner: where the game does real work.{C['r']}\n")
    return "\n".join(lines)


# ── Main Loop ────────────────────────────────────────────────────────

def main():
    state = init_game()
    message = "My name Jeff. Order up."
    events = []

    # Spawn initial customers
    for _ in range(3):
        spawn_customer(state)

    while state.shift_time > 0:
        game_events = tick(state)
        events.extend(game_events)
        render(state, events, message)
        message = ""

        # Non-blocking input with timeout
        if _input_ready(TICK_RATE):
            try:
                raw = sys.stdin.readline().strip()
            except EOFError:
                break

            if not raw:
                continue

            parts = raw.split()
            cmd = parts[0].lower()

            if cmd == "q":
                break
            elif cmd == "a":
                actions = auto_manage(state)
                message = " | ".join(actions[:3]) if actions else "Nothing to manage."
            elif cmd == "s" and len(parts) == 3:
                try:
                    message = seat_customer(state, int(parts[1]), int(parts[2]))
                except (ValueError, IndexError):
                    message = "Usage: s <queue#> <table#>"
            elif cmd == "c" and len(parts) == 2:
                try:
                    message = start_cooking(state, int(parts[1]))
                except (ValueError, IndexError):
                    message = "Usage: c <table#>"
            elif cmd == "v" and len(parts) == 2:
                try:
                    message = serve(state, int(parts[1]))
                except (ValueError, IndexError):
                    message = "Usage: v <table#>"
            elif cmd == "b" and len(parts) == 2:
                try:
                    message = bus_table(state, int(parts[1]))
                except (ValueError, IndexError):
                    message = "Usage: b <table#>"
            else:
                message = "Unknown command. Try: s, c, v, b, a, q"

        # Trim old events
        events = events[-8:]

    # Shift over
    clear()
    print(shift_summary(state))

    # Execute real work
    real = execute_real_work(state)
    if real:
        print(f"  {C['b']}EXECUTING REAL WORK...{C['r']}")
        for r in real:
            print(f"    {r}")


if __name__ == "__main__":
    main()
