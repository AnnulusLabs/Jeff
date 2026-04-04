"""jeff.hand.forge — When Jeff can't, Jeff builds.

Most agents fail when they lack a capability.
Jeff doesn't fizzle. Jeff forges.

When a task requires a tool Jeff doesn't have:
  1. Identify what's missing
  2. Search for existing tools (PyPI, GitHub, local)
  3. If found → install and wire
  4. If not found → WRITE the tool
  5. Test it
  6. Add to nerve/ toolkit
  7. Resume the original task

The dead end becomes a forge. The blocker becomes a feature.

"I needed a hammer. Didn't have one. Made one. Here's your shelf."

Gripe #28 extension: Don't just remember dead ends — build past them.

AnnulusLabs LLC · April 2026
"""

import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

FORGE_DIR = Path.home() / ".jeff" / "forge"
TOOLS_DIR = FORGE_DIR / "tools"


class ForgeStrategy(Enum):
    FIND_PYPI = "find_pypi"          # search PyPI for existing package
    FIND_SYSTEM = "find_system"      # check if system binary exists
    FIND_LOCAL = "find_local"        # search local filesystem
    BUILD = "build"                  # write the tool from scratch
    COMPOSE = "compose"              # combine existing tools


@dataclass
class Need:
    """What Jeff needs but doesn't have."""
    capability: str         # "pdf_parsing", "image_resize", "csv_pivot"
    context: str           # why it's needed
    task_id: str = ""      # original task that triggered the need
    attempted: list = field(default_factory=list)  # what was tried


@dataclass
class ForgedTool:
    """A tool Jeff built or found to fill a gap."""
    name: str
    source: str            # "pypi:pdfplumber", "built:csv_pivoter", "system:ffmpeg"
    strategy: ForgeStrategy
    code: str = ""         # if built, the actual code
    install_cmd: str = ""  # if found, how to install
    test_result: str = ""
    tested: bool = False
    works: bool = False
    forged_at: float = field(default_factory=time.time)
    filepath: str = ""     # where the tool lives on disk


@dataclass
class ForgeResult:
    success: bool
    tool: ForgedTool = None
    error: str = ""
    strategy_used: ForgeStrategy = ForgeStrategy.BUILD
    attempts: list = field(default_factory=list)


# ── Discovery ────────────────────────────────────────────────────────

def search_pypi(capability: str) -> list[dict]:
    """Search PyPI for packages that might provide the capability."""
    # Map common capabilities to known packages
    KNOWN_TOOLS = {
        "pdf": ["pdfplumber", "PyPDF2", "pymupdf"],
        "csv": ["pandas", "polars"],
        "image": ["Pillow", "opencv-python"],
        "excel": ["openpyxl", "xlsxwriter"],
        "yaml": ["pyyaml", "ruamel.yaml"],
        "toml": ["tomli", "toml"],
        "html": ["beautifulsoup4", "lxml"],
        "markdown": ["markdown", "mistune"],
        "sql": ["sqlite3"],  # built-in
        "http": ["httpx", "requests"],
        "json": ["orjson", "ujson"],
        "xml": ["lxml", "xmltodict"],
        "zip": ["zipfile"],  # built-in
        "tar": ["tarfile"],  # built-in
        "regex": ["re"],     # built-in
        "date": ["python-dateutil", "arrow"],
        "crypto": ["cryptography", "hashlib"],
        "test": ["pytest", "unittest"],
        "graph": ["networkx", "igraph"],
        "plot": ["matplotlib", "plotly"],
        "audio": ["pydub", "soundfile"],
        "video": ["moviepy", "ffmpeg-python"],
        "ocr": ["pytesseract", "easyocr"],
        "scrape": ["beautifulsoup4", "scrapy", "httpx"],
        "git": ["gitpython"],
        "docker": ["docker"],
        "ssh": ["paramiko", "fabric"],
    }

    results = []
    cap_lower = capability.lower()
    for key, packages in KNOWN_TOOLS.items():
        if key in cap_lower:
            for pkg in packages:
                results.append({"name": pkg, "match": key})

    return results


def check_system_tool(name: str) -> bool:
    """Check if a system binary exists."""
    import shutil
    return shutil.which(name) is not None


def check_python_import(module: str) -> bool:
    """Check if a Python module is importable."""
    try:
        __import__(module.replace("-", "_"))
        return True
    except ImportError:
        return False


# ── Installation ─────────────────────────────────────────────────────

def install_package(package: str, timeout: int = 60) -> bool:
    """Install a PyPI package. Returns success."""
    try:
        result = subprocess.run(
            ["pip", "install", package, "--break-system-packages", "-q"],
            capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0
    except Exception:
        return False


# ── Tool Building ────────────────────────────────────────────────────

def build_tool_stub(name: str, capability: str, context: str) -> str:
    """Generate a tool stub that Jeff can fill in.

    Returns Python code for a minimal tool module.
    Jeff's mind/evolve or an LLM call fills in the implementation.
    """
    return f'''"""jeff.forge.{name} — Auto-forged tool.

Capability: {capability}
Context: {context}
Forged: {time.strftime("%Y-%m-%d %H:%M")}

This tool was built by Jeff at runtime because it was needed
and didn't exist. It may need refinement.
"""


def run(input_data, **kwargs):
    """Execute the tool.

    Args:
        input_data: primary input
        **kwargs: additional parameters

    Returns:
        result dict with 'output' and 'success' keys
    """
    # TODO: Jeff fills this in via LLM or evolve
    raise NotImplementedError(
        f"Stub for {{capability}}. Needs implementation.")


def test():
    """Self-test. Returns True if the tool works."""
    try:
        result = run("test_input")
        return result.get("success", False)
    except NotImplementedError:
        return False
    except Exception:
        return False


TOOL_META = {{
    "name": "{name}",
    "capability": "{capability}",
    "forged": True,
    "tested": False,
}}
'''


def save_forged_tool(tool: ForgedTool):
    """Save a forged tool to disk."""
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    if tool.code:
        filepath = TOOLS_DIR / f"{tool.name}.py"
        filepath.write_text(tool.code)
        tool.filepath = str(filepath)

    # Save metadata
    meta = {
        "name": tool.name,
        "source": tool.source,
        "strategy": tool.strategy.value,
        "tested": tool.tested,
        "works": tool.works,
        "forged_at": tool.forged_at,
        "filepath": tool.filepath,
        "install_cmd": tool.install_cmd,
    }
    meta_path = TOOLS_DIR / f"{tool.name}.json"
    meta_path.write_text(json.dumps(meta, indent=2))


def load_forged_tools() -> list[ForgedTool]:
    """Load all previously forged tools."""
    tools = []
    if not TOOLS_DIR.exists():
        return tools
    for meta_path in TOOLS_DIR.glob("*.json"):
        try:
            meta = json.loads(meta_path.read_text())
            tools.append(ForgedTool(
                name=meta["name"],
                source=meta.get("source", ""),
                strategy=ForgeStrategy(meta.get("strategy", "build")),
                tested=meta.get("tested", False),
                works=meta.get("works", False),
                forged_at=meta.get("forged_at", 0),
                filepath=meta.get("filepath", ""),
                install_cmd=meta.get("install_cmd", ""),
            ))
        except Exception:
            pass
    return tools


# ── The Forge ────────────────────────────────────────────────────────

def forge(need: Need, llm_fn=None) -> ForgeResult:
    """The main forge loop. Find or build what's needed.

    Args:
        need: what capability is missing
        llm_fn: optional function(prompt) → code string
                 for LLM-powered tool building

    Returns:
        ForgeResult with the tool (found or built)
    """
    attempts = []
    cap = need.capability.lower()

    # 1. Check if we already forged this
    existing = load_forged_tools()
    for tool in existing:
        if tool.name == cap or cap in tool.name:
            if tool.works:
                return ForgeResult(success=True, tool=tool,
                                   strategy_used=ForgeStrategy.FIND_LOCAL,
                                   attempts=["Found in forge cache"])

    # 2. Check if it's already importable
    if check_python_import(cap.replace(" ", "_")):
        tool = ForgedTool(
            name=cap, source=f"python:{cap}",
            strategy=ForgeStrategy.FIND_LOCAL,
            tested=True, works=True)
        return ForgeResult(success=True, tool=tool,
                           strategy_used=ForgeStrategy.FIND_LOCAL,
                           attempts=["Already importable"])

    # 3. Check system tools
    for cmd in cap.split():
        if check_system_tool(cmd):
            tool = ForgedTool(
                name=cmd, source=f"system:{cmd}",
                strategy=ForgeStrategy.FIND_SYSTEM,
                tested=True, works=True)
            return ForgeResult(success=True, tool=tool,
                               strategy_used=ForgeStrategy.FIND_SYSTEM,
                               attempts=["Found system binary"])

    # 4. Search PyPI
    pypi_results = search_pypi(cap)
    for pkg_info in pypi_results:
        pkg = pkg_info["name"]
        attempts.append(f"Trying PyPI: {pkg}")

        if check_python_import(pkg.replace("-", "_")):
            tool = ForgedTool(
                name=pkg, source=f"pypi:{pkg}",
                strategy=ForgeStrategy.FIND_PYPI,
                tested=True, works=True)
            save_forged_tool(tool)
            return ForgeResult(success=True, tool=tool,
                               strategy_used=ForgeStrategy.FIND_PYPI,
                               attempts=attempts)

        if install_package(pkg):
            tool = ForgedTool(
                name=pkg, source=f"pypi:{pkg}",
                strategy=ForgeStrategy.FIND_PYPI,
                install_cmd=f"pip install {pkg}",
                tested=True, works=True)
            save_forged_tool(tool)
            return ForgeResult(success=True, tool=tool,
                               strategy_used=ForgeStrategy.FIND_PYPI,
                               attempts=attempts)
        attempts.append(f"  {pkg} install failed")

    # 5. Build it
    attempts.append("No existing tool found. Building...")
    name = cap.replace(" ", "_").replace("-", "_")

    if llm_fn:
        # Ask the LLM to write the tool
        prompt = (f"Write a Python module that provides: {need.capability}\n"
                  f"Context: {need.context}\n"
                  f"Requirements:\n"
                  f"- Single file, no external dependencies beyond stdlib\n"
                  f"- Must have a run(input_data, **kwargs) function\n"
                  f"- Must have a test() function that returns bool\n"
                  f"- Must have TOOL_META dict\n"
                  f"- Handle errors gracefully\n"
                  f"Return ONLY the Python code.")
        try:
            code = llm_fn(prompt)
            tool = ForgedTool(
                name=name, source=f"built:{name}",
                strategy=ForgeStrategy.BUILD, code=code)
            save_forged_tool(tool)
            # Try to test it
            try:
                exec(compile(code, f"<forge:{name}>", "exec"))
                tool.tested = True
                tool.works = True
                attempts.append(f"Built and tested: {name}")
            except Exception as e:
                tool.tested = True
                tool.works = False
                tool.test_result = str(e)
                attempts.append(f"Built but test failed: {e}")

            save_forged_tool(tool)
            return ForgeResult(success=tool.works, tool=tool,
                               strategy_used=ForgeStrategy.BUILD,
                               attempts=attempts)
        except Exception as e:
            attempts.append(f"LLM build failed: {e}")

    # 6. Generate stub for manual completion
    code = build_tool_stub(name, need.capability, need.context)
    tool = ForgedTool(
        name=name, source=f"stub:{name}",
        strategy=ForgeStrategy.BUILD, code=code,
        tested=False, works=False)
    save_forged_tool(tool)
    attempts.append(f"Generated stub at {tool.filepath}. Needs implementation.")

    return ForgeResult(success=False, tool=tool,
                       strategy_used=ForgeStrategy.BUILD,
                       attempts=attempts,
                       error="Generated stub. LLM or human must implement.")


# ── Inventory ────────────────────────────────────────────────────────

def inventory() -> str:
    """What's in the forge?"""
    tools = load_forged_tools()
    if not tools:
        return "Forge empty. Jeff hasn't needed to build anything yet."
    lines = [f"FORGE: {len(tools)} tools"]
    for t in tools:
        status = "OK" if t.works else "STUB" if not t.tested else "BROKEN"
        lines.append(f"  [{status:<6s}] {t.name:<25s} via {t.strategy.value}")
    return "\n".join(lines)
