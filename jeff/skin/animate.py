"""jeff.skin.animate — Jeff's face. Terminal animation with voice sync.

Boot sequence: CRT warm-up → face draws line by line → mouth opens →
"My name Jeff." → face settles to prompt.

Mouth sync: 4 frames (closed, ajar, open, closed) timed to syllables.
Voice plays concurrent with animation via threading.

ANSI escape codes for cursor positioning. No curses dependency.
Works in any terminal that supports VT100 (all of them).

AnnulusLabs LLC · April 2026
"""

import os
import sys
import time
import random
import threading
from pathlib import Path

# ── ANSI Escapes ─────────────────────────────────────────────────────

ESC = "\033"
CLEAR = f"{ESC}[2J"
HOME = f"{ESC}[H"
HIDE_CURSOR = f"{ESC}[?25l"
SHOW_CURSOR = f"{ESC}[?25h"
GREEN = f"{ESC}[32m"
DIM_GREEN = f"{ESC}[2;32m"
BRIGHT_GREEN = f"{ESC}[1;32m"
RESET = f"{ESC}[0m"
AMBER = f"{ESC}[33m"


def _goto(row: int, col: int) -> str:
    return f"{ESC}[{row};{col}H"


def _color(text: str, color: str = GREEN) -> str:
    return f"{color}{text}{RESET}"


# ── Jeff's Face — 4 Mouth Frames ────────────────────────────────────

# Frame 0: mouth closed (resting / listening)
FACE_CLOSED = r"""
              ╔══════════════════════╗
              ║    ┌──────────────┐  ║
              ║   ╱                ╲ ║
              ║  │  ╭────╮╭────╮   │║
              ║  │  │ ·  ││  · │   │║
              ║  │  ╰────╯╰────╯   │║
              ║  │       ╱╲        │║
              ║  │      ╱  ╲       │║
              ║  │     ╱    ╲      │║
              ║  │    ╰──────╯     │║
              ║  │     ┌────┐      │║
              ║  │     │    │      │║
              ║  │     └────┘      │║
              ║  │  ╲            ╱ │║
              ║   ╲──────────────╱  ║
              ║      │      │       ║
              ║   ┌──┴──────┴──┐    ║
              ║   │  ┌──────┐  │    ║
              ║   │  │ JEFF │  │    ║
              ║   │  └──────┘  │    ║
              ╚══════════════════════╝
"""

# Frame 1: mouth ajar (starting to speak)
FACE_AJAR = r"""
              ╔══════════════════════╗
              ║    ┌──────────────┐  ║
              ║   ╱                ╲ ║
              ║  │  ╭────╮╭────╮   │║
              ║  │  │ ·  ││  · │   │║
              ║  │  ╰────╯╰────╯   │║
              ║  │       ╱╲        │║
              ║  │      ╱  ╲       │║
              ║  │     ╱    ╲      │║
              ║  │    ╰──────╯     │║
              ║  │     ┌────┐      │║
              ║  │     │ ·· │      │║
              ║  │     └────┘      │║
              ║  │  ╲            ╱ │║
              ║   ╲──────────────╱  ║
              ║      │      │       ║
              ║   ┌──┴──────┴──┐    ║
              ║   │  ┌──────┐  │    ║
              ║   │  │ JEFF │  │    ║
              ║   │  └──────┘  │    ║
              ╚══════════════════════╝
"""

# Frame 2: mouth open (speaking)
FACE_OPEN = r"""
              ╔══════════════════════╗
              ║    ┌──────────────┐  ║
              ║   ╱                ╲ ║
              ║  │  ╭────╮╭────╮   │║
              ║  │  │ ·  ││  · │   │║
              ║  │  ╰────╯╰────╯   │║
              ║  │       ╱╲        │║
              ║  │      ╱  ╲       │║
              ║  │     ╱    ╲      │║
              ║  │    ╰──────╯     │║
              ║  │    ┌──────┐     │║
              ║  │    │  @@  │     │║
              ║  │    │  @@  │     │║
              ║  │  ╲ └──────┘  ╱  │║
              ║   ╲──────────────╱  ║
              ║      │      │       ║
              ║   ┌──┴──────┴──┐    ║
              ║   │  ┌──────┐  │    ║
              ║   │  │ JEFF │  │    ║
              ║   │  └──────┘  │    ║
              ╚══════════════════════╝
"""

# Frame 3: mouth wide (emphasis syllable)
FACE_WIDE = r"""
              ╔══════════════════════╗
              ║    ┌──────────────┐  ║
              ║   ╱                ╲ ║
              ║  │  ╭────╮╭────╮   │║
              ║  │  │ ·  ││  · │   │║
              ║  │  ╰────╯╰────╯   │║
              ║  │       ╱╲        │║
              ║  │      ╱  ╲       │║
              ║  │     ╱    ╲      │║
              ║  │    ╰──────╯     │║
              ║  │   ┌────────┐    │║
              ║  │   │  @@@@  │    │║
              ║  │   │  @@@@  │    │║
              ║  │  ╲└────────┘ ╱  │║
              ║   ╲──────────────╱  ║
              ║      │      │       ║
              ║   ┌──┴──────┴──┐    ║
              ║   │  ┌──────┐  │    ║
              ║   │  │ JEFF │  │    ║
              ║   │  └──────┘  │    ║
              ╚══════════════════════╝
"""

FRAMES = [FACE_CLOSED, FACE_AJAR, FACE_OPEN, FACE_WIDE]

# ── Compact face for prompt ──────────────────────────────────────────

FACE_MINI = r"""
    ┌──────────┐
    │  ·    ·  │
    │    ──    │
    └────┬─────┘
    ┌────┴─────┐
    │  [JEFF]  │
    └──────────┘
"""

# Speech bubble
SPEECH = r"""
    ┌──────────────────────────────┐
    │  {text:<28s}  │
    └──────────────┬───────────────┘
                   │
"""

# ── CRT Boot Sequence ────────────────────────────────────────────────

def crt_boot(speed: float = 0.02):
    """Draw the face line by line like a CRT warming up."""
    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.write(CLEAR + HOME)
    sys.stdout.flush()

    lines = FACE_CLOSED.strip("\n").split("\n")

    # Warm-up flicker
    for _ in range(3):
        sys.stdout.write(HOME)
        row = random.randint(0, len(lines) - 1)
        noise = "".join(random.choice("░▒▓█ ") for _ in range(40))
        sys.stdout.write(_goto(row + 1, 1) + _color(noise, DIM_GREEN))
        sys.stdout.flush()
        time.sleep(0.05)

    sys.stdout.write(CLEAR + HOME)
    sys.stdout.flush()

    # Draw line by line
    for i, line in enumerate(lines):
        sys.stdout.write(_goto(i + 1, 1) + _color(line, GREEN))
        sys.stdout.flush()
        time.sleep(speed)

    # Stabilize — brief flicker then solid
    time.sleep(0.2)
    for _ in range(2):
        sys.stdout.write(HOME)
        for i, line in enumerate(lines):
            sys.stdout.write(_goto(i + 1, 1) + _color(line, DIM_GREEN))
        sys.stdout.flush()
        time.sleep(0.05)
        sys.stdout.write(HOME)
        for i, line in enumerate(lines):
            sys.stdout.write(_goto(i + 1, 1) + _color(line, BRIGHT_GREEN))
        sys.stdout.flush()
        time.sleep(0.05)

    # Settle to normal green
    sys.stdout.write(HOME)
    for i, line in enumerate(lines):
        sys.stdout.write(_goto(i + 1, 1) + _color(line, GREEN))
    sys.stdout.flush()


# ── Mouth Animation ──────────────────────────────────────────────────

def _draw_frame(frame: str, color: str = GREEN):
    """Draw a face frame at cursor home."""
    sys.stdout.write(HOME)
    for i, line in enumerate(frame.strip("\n").split("\n")):
        sys.stdout.write(_goto(i + 1, 1) + _color(line, color))
    sys.stdout.flush()


def mouth_sequence(text: str) -> list[int]:
    """Generate mouth frame indices from text.

    Simple phoneme approximation:
      vowels = wide open (3)
      consonants = ajar (1) or open (2)
      spaces = closed (0)
      punctuation = closed (0)
    """
    vowels = set("aeiouAEIOU")
    sequence = []
    for ch in text:
        if ch in vowels:
            sequence.append(3)      # wide
        elif ch == " ":
            sequence.append(0)      # closed
        elif ch in ".,;:!?-":
            sequence.append(0)      # pause
        elif ch in "mnbp":
            sequence.append(1)      # ajar (lips together)
        else:
            sequence.append(2)      # open
    return sequence


def speak_animated(text: str, frame_delay: float = 0.08,
                   color: str = GREEN, voice: bool = False):
    """Animate Jeff's face while speaking text.

    Optionally plays voice concurrently via skin.voice.
    """
    sys.stdout.write(HIDE_CURSOR)

    sequence = mouth_sequence(text)

    # Start voice in background thread if requested
    voice_thread = None
    if voice:
        try:
            from jeff.skin.voice import speak as voice_speak
            voice_thread = threading.Thread(
                target=voice_speak, args=(text,), daemon=True)
            voice_thread.start()
        except ImportError:
            pass

    # Draw speech bubble above face
    face_lines = FRAMES[0].strip("\n").split("\n")
    bubble = SPEECH.format(text=text)
    bubble_lines = bubble.strip("\n").split("\n")
    offset = len(bubble_lines)

    sys.stdout.write(CLEAR + HOME)
    for i, line in enumerate(bubble_lines):
        sys.stdout.write(_goto(i + 1, 1) + _color(line, color))

    # Animate mouth through sequence
    prev_frame = -1
    for idx in sequence:
        if idx != prev_frame:
            frame_lines = FRAMES[idx].strip("\n").split("\n")
            for i, line in enumerate(frame_lines):
                sys.stdout.write(
                    _goto(offset + i + 1, 1) + _color(line, color))
            sys.stdout.flush()
            prev_frame = idx
        time.sleep(frame_delay)

    # Return to closed
    _draw_frame(FRAMES[0], color)
    time.sleep(0.3)

    if voice_thread:
        voice_thread.join(timeout=5)

    sys.stdout.write(SHOW_CURSOR)
    sys.stdout.flush()


# ── Greeting Sequence ────────────────────────────────────────────────

def greet(voice: bool = False):
    """Full boot: CRT warm-up → face → speech → settle."""
    crt_boot()
    time.sleep(0.5)
    speak_animated("My name Jeff.", frame_delay=0.12, voice=voice)
    time.sleep(0.3)
    speak_animated("I handle it.", frame_delay=0.10, voice=voice)
    time.sleep(0.5)

    # Settle to mini face + prompt
    sys.stdout.write(CLEAR + HOME)
    for i, line in enumerate(FACE_MINI.strip("\n").split("\n")):
        sys.stdout.write(_goto(i + 1, 1) + _color(line, GREEN))
    sys.stdout.write(SHOW_CURSOR)
    sys.stdout.flush()


# ── Expression States ────────────────────────────────────────────────

def thinking(duration: float = 2.0):
    """Jeff thinks. Eyes shift."""
    sys.stdout.write(HIDE_CURSOR)
    lines = FACE_CLOSED.strip("\n").split("\n")
    end = time.time() + duration
    dot_states = ["·    ", " ·   ", "  ·  ", "   · ", "    ·"]
    idx = 0
    while time.time() < end:
        _draw_frame(FRAMES[0])
        # Subtle eye shift
        sys.stdout.write(_goto(5, 22) + _color(dot_states[idx % 5], GREEN))
        sys.stdout.flush()
        idx += 1
        time.sleep(0.3)
    _draw_frame(FRAMES[0])
    sys.stdout.write(SHOW_CURSOR)
    sys.stdout.flush()


def judge():
    """Jeff judges your code. Slight squint."""
    sys.stdout.write(HIDE_CURSOR)
    # Squint frame — narrow eyes
    squint = FACE_CLOSED.replace("│ ·  │", "│ -  │")
    sys.stdout.write(CLEAR + HOME)
    for i, line in enumerate(squint.strip("\n").split("\n")):
        sys.stdout.write(_goto(i + 1, 1) + _color(line, GREEN))
    sys.stdout.flush()
    time.sleep(1.5)
    _draw_frame(FRAMES[0])
    sys.stdout.write(SHOW_CURSOR)
    sys.stdout.flush()


def approve():
    """Subtle nod — frame shifts down 1 row briefly."""
    sys.stdout.write(HIDE_CURSOR)
    _draw_frame(FRAMES[0])
    time.sleep(0.2)
    # Shift down
    sys.stdout.write(CLEAR + HOME)
    sys.stdout.write("\n")  # one line down
    for i, line in enumerate(FRAMES[0].strip("\n").split("\n")):
        sys.stdout.write(_goto(i + 2, 1) + _color(line, GREEN))
    sys.stdout.flush()
    time.sleep(0.15)
    # Back up
    _draw_frame(FRAMES[0])
    time.sleep(0.1)
    sys.stdout.write(SHOW_CURSOR)
    sys.stdout.flush()


def reject():
    """Slight head shake — frame shifts left then right."""
    sys.stdout.write(HIDE_CURSOR)
    lines = FRAMES[0].strip("\n").split("\n")
    for offset in [-1, 1, -1, 0]:
        sys.stdout.write(CLEAR + HOME)
        for i, line in enumerate(lines):
            col = max(1, 1 + offset)
            sys.stdout.write(_goto(i + 1, col) + _color(line, GREEN))
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write(SHOW_CURSOR)
    sys.stdout.flush()


# ── Static Banner (for README / non-interactive) ────────────────────

BANNER = r"""
    ┌──────────────────────────────┐
    │  My name Jeff.               │
    │  I handle it.                │
    └──────────────┬───────────────┘
                   │
              ╔════╧════╗
              ║  ·   ·  ║
              ║    ▾    ║
              ║  └───┘  ║
              ╚════╤════╝
             ┌─────┴─────┐
             │ ┌───────┐ │
             │ │J·E·F·F│ │
             │ └───────┘ │
             └─────┬─────┘
                  ╱ ╲
                 ╱   ╲
"""


def print_banner():
    """Static banner for non-animated contexts."""
    print(_color(BANNER, GREEN))


# ── Entry Point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys as _sys
    if "--static" in _sys.argv:
        print_banner()
    elif "--greet" in _sys.argv:
        greet(voice="--voice" in _sys.argv)
    elif "--judge" in _sys.argv:
        judge()
    elif "--think" in _sys.argv:
        thinking()
    else:
        greet()
