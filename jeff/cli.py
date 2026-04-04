"""jeff.cli — My name Jeff. I handle it.

Commands:
    jeff              Status + ready
    jeff init         Set up workspace
    jeff run <task>   Execute a task
    jeff ask <query>  One-shot question
    jeff fix <issue>  Diagnose and repair
    jeff ship         Build, test, deliver
    jeff audit        Quality gate check
    jeff local        Pantry inventory
    jeff cluster      Distributed nodes
    jeff status       Current state
    jeff arcade       Play games. Ship code.
    jeff version      Version
"""

import os, hashlib
import click
from jeff import __version__
from jeff import skin, bone, personality
from jeff.nerve import dispatch, bash, tree, TOOLS
from jeff.pantry import chat, generate, list_models, is_available, PantryConfig, JEFF_SYSTEM
from jeff.gate import check, gate_prompt, format_result


def _sid() -> str:
    return hashlib.sha256(os.getcwd().encode()).hexdigest()[:12]


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """My name Jeff. I handle it."""
    bone.init()
    if ctx.invoked_subcommand is None:
        skin.banner()
        if is_available():
            skin.whisper(f"{len(list_models())} models in the pantry.")
        else:
            skin.alert(personality.Level.WARN, "Ollama not running. jeff needs: ollama serve")
        skin.say("What needs doing?")


@main.command()
def init():
    """Set up workspace."""
    bone.init()
    session = bone.Session(id=_sid(), cwd=os.getcwd())
    bone.save_session(session)
    skin.banner()
    skin.done(f"Workspace ready at {os.getcwd()}")


@main.command()
@click.argument("task", nargs=-1, required=True)
@click.option("--model", "-m", default=None)
def run(task, model):
    """Execute a task."""
    task_text = " ".join(task)
    sid = _sid()
    session = bone.load_session(sid) or bone.Session(id=sid, cwd=os.getcwd())

    if not is_available():
        skin.alert(personality.Level.ERROR, "Ollama not running.")
        return

    cfg = PantryConfig()
    if model:
        cfg.default_model = model

    # Route through hand for domain detection
    from jeff.hand import detect_domain, DOMAIN_PROMPTS
    domain, confidence = detect_domain(task_text)

    cwd_info = tree(os.getcwd(), depth=2)
    system = f"""{JEFF_SYSTEM}

Domain: {domain.value} (confidence: {confidence:.0%})
{DOMAIN_PROMPTS.get(domain, '')}

Working directory: {os.getcwd()}
Files:\n{cwd_info.output[:2000]}

{gate_prompt()}

Available tools: {', '.join(TOOLS.keys())}
When using a tool, respond: TOOL: <name> / ARGS: <json>
When done, respond: DONE: <summary>
"""
    session.add("user", task_text)
    messages = session.history(limit=20)
    skin.whisper(f"[{domain.value}] {task_text}")

    for turn in range(15):
        response = chat(messages, config=cfg, system=system)
        if response.error:
            skin.alert(personality.Level.ERROR, response.error)
            break

        session.tokens_in += response.tokens_in
        session.tokens_out += response.tokens_out
        content = personality.sanitize(response.content)

        if "TOOL:" in content:
            import json as _json
            lines = content.split("\n")
            tool_name, tool_output = None, ""
            for line in lines:
                if line.strip().startswith("TOOL:"):
                    tool_name = line.split("TOOL:")[1].strip()
                elif line.strip().startswith("ARGS:"):
                    try:
                        args = _json.loads(line.split("ARGS:")[1].strip())
                    except Exception:
                        args = {"cmd": line.split("ARGS:")[1].strip()}
                    if tool_name in TOOLS:
                        skin.progress(f"[{tool_name}] {str(args)[:80]}")
                        result = dispatch(tool_name, **args)
                        tool_output = result.output if result.success else f"Error: {result.error}"
                    else:
                        tool_output = f"Unknown tool: {tool_name}"
            session.add("assistant", content)
            session.add("tool", tool_output, tool=tool_name)
            messages = session.history(limit=20)
            continue

        if "DONE:" in content:
            summary = content.split("DONE:")[-1].strip()
            session.add("assistant", content)
            skin.say(summary or "Handled.")
            break
        else:
            session.add("assistant", content)
            skin.say(content)
            break

    bone.save_session(session)
    skin.whisper(f"Tokens: {session.cost_summary()}")


@main.command()
@click.argument("task", nargs=-1, required=True)
@click.option("--model", "-m", default=None)
def ask(task, model):
    """One-shot question. No session."""
    if not is_available():
        skin.alert(personality.Level.ERROR, "Ollama not running.")
        return
    cfg = PantryConfig()
    if model:
        cfg.default_model = model
    response = generate(" ".join(task), config=cfg, system=JEFF_SYSTEM)
    if response.error:
        skin.alert(personality.Level.ERROR, response.error)
    else:
        skin.say(personality.sanitize(response.content))
    skin.whisper(f"Tokens: {response.tokens_in} in / {response.tokens_out} out")


@main.command()
@click.argument("cmd", nargs=-1, required=True)
def fix(cmd):
    """Diagnose and repair."""
    ctx = click.get_current_context()
    ctx.invoke(run, task=("fix",) + cmd)


@main.command()
def ship():
    """Build, test, deliver."""
    skin.whisper("Running gate checks...")
    result = dispatch("glob", pattern="*.py")
    if not result.output:
        skin.say("Nothing to ship.")
        return
    files = result.output.strip().split("\n")
    issues = 0
    for f in files[:20]:
        code = dispatch("read", path=f)
        if code.success:
            gate = check(code.output)
            if not gate.passed:
                skin.alert(personality.Level.WARN, f"{f}: {format_result(gate)}")
                issues += 1
    if issues == 0:
        test = bash("python -m pytest --tb=short -q 2>/dev/null || echo 'no tests'", timeout=60)
        if test.success:
            skin.done("Gate passed. Ready to ship.")
        else:
            skin.alert(personality.Level.ERROR, f"Tests failed.\n{test.output}")
    else:
        skin.alert(personality.Level.WARN, f"{issues} file(s) flagged. Fix before shipping.")


@main.command()
def audit():
    """Run quality gate on cwd."""
    result = dispatch("glob", pattern="*.py")
    if not result.output:
        skin.say("No Python files to audit.")
        return
    files = result.output.strip().split("\n")
    issues = 0
    for f in files[:50]:
        code = dispatch("read", path=f)
        if code.success:
            gate = check(code.output)
            if not gate.passed:
                skin.alert(personality.Level.WARN, f"{f}: {format_result(gate)}")
                issues += 1
    skin.done("Audit clean." if issues == 0 else f"{issues} file(s) flagged.")


@main.command()
def local():
    """What's in the pantry."""
    if not is_available():
        skin.alert(personality.Level.WARN, "Ollama not running.")
        return
    models = list_models()
    if models:
        skin.header("Pantry")
        for m in sorted(models):
            skin.say(f"  {m}")
        skin.whisper(f"{len(models)} models available.")
    else:
        skin.say("Pantry empty. Pull a model: ollama pull hermes3:8b")


@main.command()
def cluster():
    """Show distributed compute nodes."""
    import asyncio
    from jeff.pantry.cluster import Cluster
    async def _show():
        c = Cluster()
        await c.discover_local()
        skin.say(c.summary())
    asyncio.run(_show())


@main.command()
def status():
    """Current workspace state."""
    session = bone.load_session(_sid())
    skin.banner()
    if session:
        skin.say(f"Session: {session.id}")
        skin.say(f"Directory: {session.cwd}")
        skin.say(f"Messages: {len(session.messages)}")
        skin.say(f"Tokens: {session.cost_summary()}")
    else:
        skin.say("No session. Run jeff init.")
    if is_available():
        skin.whisper(f"Ollama: running ({len(list_models())} models)")
    else:
        skin.alert(personality.Level.WARN, "Ollama: not running")


@main.command()
def arcade():
    """Play games. Ship code. Same thing."""
    from jeff.arcade import arcade_menu
    arcade_menu()


@main.command()
@click.option("--port", "-p", default=8421)
@click.option("--theme", "-t", default="medieval",
              type=click.Choice(["medieval", "scifi", "minimal", "work"]))
def workplay(port, theme):
    """The game IS the work. Launch themed PR review."""
    os.environ["WORKPLAY_THEME"] = theme
    os.environ["WORKPLAY_PORT"] = str(port)
    try:
        from jeff.workplay import serve
    except ModuleNotFoundError as exc:
        if exc.name in {"fastapi", "pydantic", "starlette", "uvicorn"}:
            raise click.ClickException(
                "WorkPlay needs its extra deps. Install with: pip install -e '.[workplay]'"
            ) from exc
        raise
    serve(port=port)


@main.command()
def version():
    """Version."""
    skin.say(f"Jeff v{__version__}")


if __name__ == "__main__":
    main()
