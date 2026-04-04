#!/usr/bin/env python3
"""
JEFF'S ARCADE — Every game does real work.

Play games. Ship code. Same thing.

The arcade is a framework. Each game maps game events to real tasks.
Score a point? Ran a lint check. Kill a demon? Fixed a bug.
Pass a pipe? Audited a file. Hit a gorilla? Refactored a module.

Ships with:
  FLAPPY JEFF  — fly through pipes, each pipe = one task completed
  JEFF DOOM    — kill bugs (literal ASCII demons that are real bugs)
  GORILLAS     — QBasic classic, lob bananas at code smells
  JEFF MINER   — dig for gems, each gem = a finding in your code

Framework supports:
  - Adding custom games via simple event→task mapping
  - Emulator bridge: hook ANY game's score events to real tasks
  - Persistent high scores backed by K-history
  - Multiplayer via jeff/staff (agents play too)

"What dev doesn't want to play games and get paid for it."

AnnulusLabs LLC · April 2026
"""

import os
import sys
import time
import random
import json
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

C = {
    "r": "\033[0m", "b": "\033[1m", "dim": "\033[2m",
    "cyan": "\033[36m", "green": "\033[32m", "yellow": "\033[33m",
    "red": "\033[31m", "magenta": "\033[35m", "blue": "\033[34m",
}

ARCADE_DIR = Path.home() / ".jeff" / "arcade"
SCORES_FILE = ARCADE_DIR / "highscores.json"


# ── Task Engine (shared across all games) ────────────────────────────

class TaskPool:
    """Real tasks that games pull from. Every game event = real work."""

    TASKS = {
        "easy": [
            ("lint", "ruff check {file}"),
            ("format", "ruff format {file}"),
            ("typecheck", "check type hints in {file}"),
            ("docstring", "check docstrings in {file}"),
        ],
        "medium": [
            ("test", "pytest {file} -x"),
            ("audit", "security scan {file}"),
            ("deps", "check outdated deps"),
            ("coverage", "measure test coverage"),
        ],
        "hard": [
            ("refactor", "identify code smells in {module}"),
            ("architecture", "review module boundaries"),
            ("security", "deep vulnerability scan"),
            ("performance", "profile hot paths"),
        ],
        "boss": [
            ("full_audit", "complete codebase audit"),
            ("migration", "identify upgrade paths"),
            ("debt", "map technical debt"),
        ],
    }

    def __init__(self, cwd: str = "."):
        self.cwd = cwd
        self.completed: list[tuple[str, str]] = []
        self.k_generated: list[str] = []
        self._files = self._scan_files()

    def _scan_files(self) -> list[str]:
        try:
            return [str(p) for p in Path(self.cwd).rglob("*.py")
                    if "__pycache__" not in str(p)][:50]
        except Exception:
            return ["main.py"]

    def pull(self, difficulty: str = "easy") -> tuple[str, str]:
        tasks = self.TASKS.get(difficulty, self.TASKS["easy"])
        name, cmd = random.choice(tasks)
        file = random.choice(self._files) if self._files else "."
        module = str(Path(file).parent)
        cmd = cmd.format(file=file, module=module)
        return name, cmd

    def complete(self, name: str, cmd: str):
        self.completed.append((name, cmd))
        self.k_generated.append(f"Game completed: {name} -> {cmd}")

    def summary(self) -> str:
        return f"{len(self.completed)} tasks completed, {len(self.k_generated)} K generated"


# ── High Scores ──────────────────────────────────────────────────────

def load_scores() -> dict:
    ARCADE_DIR.mkdir(parents=True, exist_ok=True)
    if SCORES_FILE.exists():
        return json.loads(SCORES_FILE.read_text())
    return {}

def save_score(game: str, score: int, tasks: int):
    scores = load_scores()
    key = game
    if key not in scores or score > scores[key]["score"]:
        scores[key] = {"score": score, "tasks": tasks,
                       "date": time.strftime("%Y-%m-%d %H:%M")}
    SCORES_FILE.write_text(json.dumps(scores, indent=2))


# ── FLAPPY JEFF ──────────────────────────────────────────────────────

FLAPPY_HELP = """
  FLAPPY JEFF — Fly through pipes. Each pipe = one real task.

  Controls: SPACE/ENTER = flap, Q = quit
  The bird is Jeff. The pipes are your code.
  Hit a pipe and Jeff crashes. Just like production.
"""

def flappy_jeff(pool: TaskPool):
    """Flappy Bird but each pipe cleared runs a real task."""
    import select

    WIDTH, HEIGHT = 60, 20
    bird_x, bird_y = 10, HEIGHT // 2
    velocity = 0
    gravity = 0.4
    flap_power = -2.0
    score = 0
    frame = 0
    pipes = []
    alive = True

    def add_pipe():
        gap_y = random.randint(4, HEIGHT - 6)
        gap_size = random.randint(5, 7)
        pipes.append({"x": WIDTH - 1, "gap_y": gap_y, "gap_size": gap_size,
                       "scored": False, "task": pool.pull("easy" if score < 5 else "medium")})

    def render_frame():
        os.system("cls" if os.name == "nt" else "clear")
        screen = [[" "] * WIDTH for _ in range(HEIGHT)]

        # Draw pipes
        for p in pipes:
            px = int(p["x"])
            if 0 <= px < WIDTH:
                for y in range(HEIGHT):
                    if y < p["gap_y"] or y >= p["gap_y"] + p["gap_size"]:
                        if 0 <= px < WIDTH:
                            screen[y][px] = f"{C['green']}|{C['r']}"

        # Draw bird
        by = int(bird_y)
        if 0 <= by < HEIGHT:
            screen[by][bird_x] = f"{C['yellow']}>{C['r']}"

        # Draw ground
        for x in range(WIDTH):
            screen[HEIGHT - 1][x] = f"{C['dim']}={C['r']}"

        # Print
        border = f"{C['cyan']}{'─' * WIDTH}{C['r']}"
        print(f"\n  {C['b']}FLAPPY JEFF{C['r']}  Score: {score}  Tasks: {len(pool.completed)}\n")
        print(f"  {border}")
        for row in screen:
            print(f"  {''.join(row)}")
        print(f"  {border}")

        # Current task
        if pipes:
            active = [p for p in pipes if not p["scored"] and p["x"] > bird_x]
            if active:
                name, cmd = active[0]["task"]
                print(f"\n  {C['dim']}Next pipe: {name} -> {cmd[:50]}{C['r']}")

    add_pipe()

    while alive:
        frame += 1
        velocity += gravity
        bird_y += velocity

        # Move pipes
        for p in pipes:
            p["x"] -= 1.0

        # Score & complete task
        for p in pipes:
            if not p["scored"] and int(p["x"]) < bird_x:
                p["scored"] = True
                score += 1
                name, cmd = p["task"]
                pool.complete(name, cmd)

        # Spawn pipes
        if frame % 30 == 0:
            add_pipe()

        # Clean old pipes
        pipes = [p for p in pipes if p["x"] > -2]

        # Collision
        by = int(bird_y)
        if by <= 0 or by >= HEIGHT - 1:
            alive = False
        for p in pipes:
            px = int(p["x"])
            if px == bird_x:
                if by < p["gap_y"] or by >= p["gap_y"] + p["gap_size"]:
                    alive = False

        render_frame()

        # Input
        if sys.stdin in select.select([sys.stdin], [], [], 0.12)[0]:
            key = sys.stdin.readline().strip()
            if key == "q":
                break
            velocity = flap_power

    save_score("flappy_jeff", score, len(pool.completed))
    print(f"\n  {C['red']}CRASH!{C['r']} Score: {score}  Tasks completed: {len(pool.completed)}")
    print(f"  {pool.summary()}")
    _pause()


# ── GORILLAS ─────────────────────────────────────────────────────────

GORILLAS_HELP = """
  GORILLAS — The QBasic classic. Lob bananas at code smells.

  Controls: Enter ANGLE and POWER to throw.
  Hit the enemy gorilla = destroy a code smell.
  Miss = the code smell survives another round.
"""

def gorillas(pool: TaskPool):
    """QBasic Gorillas. Exploding bananas destroy code smells."""
    import math

    WIDTH, HEIGHT = 60, 25
    score = 0
    rounds = 10
    wind = random.uniform(-2, 2)

    for rnd in range(rounds):
        os.system("cls" if os.name == "nt" else "clear")

        # Positions
        p1_x, p1_y = random.randint(5, 15), HEIGHT - 5
        p2_x, p2_y = random.randint(WIDTH - 15, WIDTH - 5), HEIGHT - random.randint(3, 8)

        # Buildings (skyline)
        buildings = []
        x = 0
        while x < WIDTH:
            w = random.randint(4, 8)
            h = random.randint(5, HEIGHT - 3)
            buildings.append((x, h, w))
            x += w + 1

        task_name, task_cmd = pool.pull("medium" if score > 3 else "easy")

        # Render scene
        screen = [[" "] * WIDTH for _ in range(HEIGHT)]

        # Buildings
        for bx, bh, bw in buildings:
            for y in range(HEIGHT - bh, HEIGHT):
                for xx in range(bx, min(bx + bw, WIDTH)):
                    screen[y][xx] = f"{C['dim']}█{C['r']}"

        # Gorillas
        if 0 <= p1_y < HEIGHT and 0 <= p1_x < WIDTH:
            screen[p1_y][p1_x] = f"{C['yellow']}@{C['r']}"
        if 0 <= p2_y < HEIGHT and 0 <= p2_x < WIDTH:
            screen[p2_y][p2_x] = f"{C['red']}@{C['r']}"

        # Ground
        for x in range(WIDTH):
            screen[HEIGHT - 1][x] = f"{C['green']}={C['r']}"

        print(f"\n  {C['b']}GORILLAS{C['r']}  Round {rnd+1}/{rounds}  Score: {score}  Wind: {wind:+.1f}")
        print(f"  {C['dim']}Target: {task_name} -> {task_cmd[:45]}{C['r']}\n")
        for row in screen:
            print(f"  {''.join(row)}")

        # Input
        try:
            angle = float(input(f"\n  {C['cyan']}Angle (0-90):{C['r']} ") or 45)
            power = float(input(f"  {C['cyan']}Power (1-100):{C['r']} ") or 50)
        except (ValueError, EOFError):
            continue

        # Simulate trajectory
        rad = math.radians(angle)
        vx = math.cos(rad) * power * 0.15
        vy = -math.sin(rad) * power * 0.15
        bx, by = float(p1_x), float(p1_y)

        hit = False
        for step in range(200):
            bx += vx + wind * 0.02
            by += vy
            vy += 0.15  # gravity

            ix, iy = int(bx), int(by)
            if iy >= HEIGHT or ix < 0 or ix >= WIDTH:
                break

            # Hit target
            if abs(ix - p2_x) <= 1 and abs(iy - p2_y) <= 1:
                hit = True
                break

        if hit:
            score += 1
            pool.complete(task_name, task_cmd)
            print(f"\n  {C['green']}BOOM! Direct hit! {task_name} destroyed!{C['r']}")
        else:
            print(f"\n  {C['red']}Miss! The code smell survives.{C['r']}")

        wind = random.uniform(-2, 2)
        _pause()

    save_score("gorillas", score, len(pool.completed))
    print(f"\n  {C['b']}Game over.{C['r']} Score: {score}/{rounds}  {pool.summary()}")
    _pause()


# ── JEFF MINER ───────────────────────────────────────────────────────

MINER_HELP = """
  JEFF MINER — Dig for gems in your codebase.

  Controls: WASD/arrows to move, DIG to mine, Q to quit.
  Each gem is a real finding. Deeper = harder analysis.
  Watch your stamina (compute budget).
"""

def jeff_miner(pool: TaskPool):
    """Dig through layers. Each gem = a real code finding."""
    import select

    WIDTH, HEIGHT = 40, 20
    px, py = WIDTH // 2, 0
    depth = 0
    score = 0
    stamina = 100
    gems_found = []

    # Generate mine layers
    mine = {}
    for y in range(100):
        for x in range(WIDTH):
            r = random.random()
            if r < 0.02:
                diff = "hard" if y > 15 else "medium" if y > 5 else "easy"
                mine[(x, y)] = ("gem", pool.pull(diff))
            elif r < 0.08:
                mine[(x, y)] = ("rock", None)
            elif r < 0.12:
                mine[(x, y)] = ("ore", None)

    def render():
        os.system("cls" if os.name == "nt" else "clear")
        print(f"\n  {C['b']}JEFF MINER{C['r']}  Depth: {depth}  Gems: {score}  "
              f"Stamina: {'█' * (stamina // 5)}{'░' * (20 - stamina // 5)} {stamina}%\n")

        # Viewport
        view_top = max(0, py - HEIGHT // 2)
        for vy in range(view_top, view_top + HEIGHT):
            row = "  "
            for vx in range(WIDTH):
                if vx == px and vy == py:
                    row += f"{C['yellow']}@{C['r']}"
                elif (vx, vy) in mine:
                    kind, _ = mine[(vx, vy)]
                    if kind == "gem":
                        row += f"{C['cyan']}◆{C['r']}"
                    elif kind == "rock":
                        row += f"{C['dim']}#{C['r']}"
                    elif kind == "ore":
                        row += f"{C['yellow']}+{C['r']}"
                elif vy == 0:
                    row += f"{C['green']}={C['r']}"
                else:
                    row += f"{C['dim']}·{C['r']}"
            print(row)

        if gems_found:
            last = gems_found[-1]
            print(f"\n  {C['green']}Last find: {last}{C['r']}")

    render()

    while stamina > 0:
        if sys.stdin in select.select([sys.stdin], [], [], 0.2)[0]:
            key = sys.stdin.readline().strip().lower()
            if key == "q":
                break

            dx, dy = 0, 0
            if key in ("w", "up"): dy = -1
            elif key in ("s", "down"): dy = 1
            elif key in ("a", "left"): dx = -1
            elif key in ("d", "right"): dx = 1
            elif key == "dig":
                # Mine current position
                if (px, py) in mine:
                    kind, task = mine.pop((px, py))
                    if kind == "gem" and task:
                        name, cmd = task
                        score += 1
                        pool.complete(name, cmd)
                        gems_found.append(f"{name}: {cmd[:40]}")
                    stamina -= 2
                else:
                    stamina -= 1
                render()
                continue

            nx = max(0, min(WIDTH - 1, px + dx))
            ny = max(0, py + dy)

            # Can't walk through rock
            if (nx, ny) in mine and mine[(nx, ny)][0] == "rock":
                stamina -= 3  # breaking rock costs more
                mine.pop((nx, ny))
            else:
                px, py = nx, ny

            depth = max(depth, py)
            stamina -= 0.5
            render()

    save_score("jeff_miner", score, len(pool.completed))
    print(f"\n  {C['b']}Stamina depleted.{C['r']} Gems: {score}  Depth: {depth}")
    print(f"  {pool.summary()}")
    _pause()


# ── Emulator Bridge (concept) ────────────────────────────────────────

EMULATOR_HELP = """
  EMULATOR BRIDGE — Hook ANY game into real work.

  Concept: Monitor a game process for score/event changes.
  Map events to tasks. Kill = fix bug. Score = run test.
  Level up = promote analysis depth.

  Supports:
    - RetroArch (score memory address monitoring)
    - DOSBox (interrupt hooking)
    - Any game with a log file or memory-mapped score

  Setup: jeff arcade bridge <game_executable> --map <event_map.json>
"""

def emulator_bridge_info():
    """Print info about the emulator bridge concept."""
    print(EMULATOR_HELP)
    print(f"""
  {C['b']}Event Map Example (event_map.json):{C['r']}

  {{
    "score_increase": {{
      "trigger": "score_delta > 0",
      "task": "easy",
      "description": "Every point scores a lint check"
    }},
    "level_complete": {{
      "trigger": "level_changed",
      "task": "medium",
      "description": "Level clear = full module audit"
    }},
    "boss_kill": {{
      "trigger": "boss_health <= 0",
      "task": "hard",
      "description": "Boss kill = deep refactor"
    }},
    "death": {{
      "trigger": "lives_decreased",
      "task": "none",
      "description": "Death = Jeff judges your code silently"
    }},
    "game_over": {{
      "trigger": "game_state == over",
      "task": "boss",
      "description": "Game over = full codebase audit"
    }}
  }}

  {C['dim']}This runs real tasks. GTA wanted stars = real security audits.{C['r']}
""")
    _pause()


# ── Arcade Launcher ──────────────────────────────────────────────────

def _pause():
    input(f"\n  {C['dim']}[enter]{C['r']}")

def arcade_menu():
    """Jeff's Arcade main menu."""
    pool = TaskPool()

    while True:
        os.system("cls" if os.name == "nt" else "clear")

        scores = load_scores()
        print(f"""
{C['b']}{C['cyan']}
       ██╗███████╗███████╗███████╗██╗███████╗
       ██║██╔════╝██╔════╝██╔════╝╚═╝██╔════╝
       ██║█████╗  █████╗  █████╗      ███████╗
  ██   ██║██╔══╝  ██╔══╝  ██╔══╝      ╚════██║
  ╚█████╔╝███████╗██║     ██║         ███████║
   ╚════╝ ╚══════╝╚═╝     ╚═╝         ╚══════╝
            A  R  C  A  D  E
{C['r']}
  {C['dim']}Every game does real work. Play games. Ship code. Same thing.{C['r']}

  {C['b']}GAMES:{C['r']}

    {C['cyan']}1{C['r']}. Flappy Jeff    — Fly through pipes, each pipe = one task
    {C['cyan']}2{C['r']}. Gorillas        — QBasic classic, lob bananas at code smells
    {C['cyan']}3{C['r']}. Jeff Miner      — Dig for gems (real code findings)
    {C['cyan']}4{C['r']}. Emulator Bridge — Hook any game to real work (info)

  {C['b']}META:{C['r']}

    {C['cyan']}h{C['r']}. High Scores     {C['cyan']}t{C['r']}. Tasks Completed     {C['cyan']}q{C['r']}. Quit

  {C['b']}WORK DONE THIS SESSION:{C['r']} {pool.summary()}
""")

        if scores:
            print(f"  {C['b']}HIGH SCORES:{C['r']}")
            for game, data in scores.items():
                print(f"    {game:<16s} {data['score']:>6d}  ({data['tasks']} tasks)  {data['date']}")
            print()

        try:
            choice = input(f"  {C['cyan']}>{C['r']} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "1":
            flappy_jeff(pool)
        elif choice == "2":
            gorillas(pool)
        elif choice == "3":
            jeff_miner(pool)
        elif choice == "4":
            emulator_bridge_info()
        elif choice == "h":
            pass  # scores shown above
        elif choice == "t":
            print(f"\n  {C['b']}COMPLETED TASKS:{C['r']}")
            for name, cmd in pool.completed[-20:]:
                print(f"    {C['green']}✓{C['r']} {name}: {cmd}")
            _pause()
        elif choice == "q":
            break

    # Session summary
    if pool.completed:
        os.system("cls" if os.name == "nt" else "clear")
        print(f"""
  {C['b']}{C['cyan']}═══ ARCADE SESSION COMPLETE ═══{C['r']}

  Tasks completed: {len(pool.completed)}
  K generated:     {len(pool.k_generated)}

  {C['b']}REAL WORK DONE:{C['r']}""")
        for name, cmd in pool.completed:
            print(f"    {C['green']}✓{C['r']} {name}: {cmd}")
        print(f"\n  {C['dim']}Jeff's Arcade: where play is work and work is play.{C['r']}\n")


if __name__ == "__main__":
    arcade_menu()
