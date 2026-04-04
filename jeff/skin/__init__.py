"""jeff.skin — Terminal UI. Clean output. No noise."""

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from jeff.personality import Level, PHRASES, sanitize

console = Console()

STYLE = {
    Level.INFO: "dim",
    Level.WARN: "yellow",
    Level.ERROR: "red",
    Level.FATAL: "bold red",
}


def say(msg: str):
    """Jeff speaks. Sanitized, no sycophancy."""
    console.print(sanitize(msg))


def whisper(msg: str):
    """Low-priority output."""
    console.print(f"[dim]{msg}[/dim]")


def alert(level: Level, msg: str):
    style = STYLE[level]
    prefix = PHRASES[level]
    console.print(f"[{style}]{prefix}[/{style}] {msg}")


def code(text: str, language: str = "python"):
    console.print(Syntax(text, language, theme="monokai", line_numbers=False))


def header(title: str):
    console.print(f"\n[bold]{title}[/bold]")


def result(title: str, body: str):
    console.print(Panel(body, title=title, border_style="dim"))


def progress(msg: str):
    console.print(f"[dim]  {msg}[/dim]")


def done(msg: str = "Handled."):
    console.print(f"[green]{msg}[/green]")


def banner():
    console.print("[bold]My name Jeff.[/bold]")
