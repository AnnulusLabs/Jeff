"""jeff.workplay — The game IS the work.

Local web app serving themed PR review.
ONE task type: PR review. ONE source: GitHub. THREE templates.
ONE metric: time-to-correct-decision.

    python -m jeff.workplay
    # → http://localhost:8421

Or via CLI:
    jeff workplay

AnnulusLabs LLC · April 2026
"""

import os
import json
import hmac
import hashlib
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from jeff.workplay.classify import classify_pr
from jeff.workplay.themes import render_page, render_diff, THEMES
from jeff.workplay.telemetry import TelemetryStore, Decision

# ── Config ───────────────────────────────────────────────────────

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
PORT = int(os.environ.get("WORKPLAY_PORT", "8421"))
DEFAULT_THEME = os.environ.get("WORKPLAY_THEME", "medieval")

app = FastAPI(title="WorkPlay", version="1.0.0",
              description="The game IS the work.")
telemetry = TelemetryStore()

# In-memory PR cache (MVP — SQLite in production)
pr_cache: dict[str, dict] = {}
classification_cache: dict[str, dict] = {}

# Narrative fatigue tracker
narrative_counts: dict[str, int] = {}  # template → use count


# ── GitHub Client ────────────────────────────────────────────────

def _key(owner: str, repo: str, pr_number: int) -> str:
    return f"{owner.strip().lower()}/{repo.strip().lower()}#{pr_number}"


def _repo(repo_full_name: str) -> tuple[str, str]:
    return tuple(repo_full_name.split("/", 1)) if "/" in repo_full_name else ("", "")


def _cached(pr_number: int, repo_full_name: str = "") -> dict:
    if repo_full_name:
        return pr_cache.get(_key(*_repo(repo_full_name), pr_number), {})
    hits = [pr for key, pr in pr_cache.items() if key.endswith(f"#{pr_number}")]
    return hits[0] if len(hits) == 1 else {}


def gh_headers() -> dict:
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


async def fetch_pr(owner: str, repo: str, pr_number: int) -> dict:
    """Fetch PR data + files from GitHub API."""
    key = _key(owner, repo, pr_number)
    if key in pr_cache:
        return pr_cache[key]

    base = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    async with httpx.AsyncClient(timeout=30) as client:
        pr_resp = await client.get(base, headers=gh_headers())
        if pr_resp.status_code != 200:
            return {"error": f"GitHub API: {pr_resp.status_code}"}
        pr_data = pr_resp.json()

        files_resp = await client.get(f"{base}/files", headers=gh_headers())
        files = files_resp.json() if files_resp.status_code == 200 else []
        pr_data["files"] = files
        pr_data["_owner"] = owner
        pr_data["_repo"] = repo
        pr_data["_repo_full_name"] = f"{owner}/{repo}"

    pr_cache[key] = pr_data
    return pr_data


async def fetch_diff(owner: str, repo: str, pr_number: int) -> str:
    """Fetch raw diff from GitHub."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers={
            **gh_headers(),
            "Accept": "application/vnd.github.v3.diff"
        })
        return resp.text if resp.status_code == 200 else "Diff unavailable."


async def submit_review(owner: str, repo: str, pr_number: int,
                        decision: str, comment: str = "") -> dict:
    """Submit a review to GitHub."""
    if not GITHUB_TOKEN:
        return {"status": "skipped", "reason": "No GITHUB_TOKEN set"}

    event_map = {
        "approve": "APPROVE",
        "request_changes": "REQUEST_CHANGES",
        "reject": "REQUEST_CHANGES",  # GitHub has no "reject" — use request_changes
    }

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
    payload = {
        "event": event_map.get(decision, "COMMENT"),
        "body": comment or f"Reviewed via WorkPlay. Decision: {decision}.",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=gh_headers())
        return {"status": resp.status_code, "data": resp.json()
                if resp.status_code < 300 else resp.text}


# ── Narrative Fatigue ────────────────────────────────────────────

def get_narrative_mode(template: str) -> str:
    """Auto-rotate narrative based on usage. Earns its presence."""
    count = narrative_counts.get(template, 0)
    narrative_counts[template] = count + 1

    if count < 3:
        return "full"
    # After initial period: 20% full, 50% brief, 30% silent
    import random
    r = random.random()
    if r < 0.2:
        return "full"
    elif r < 0.7:
        return "brief"
    else:
        return "silent"


# ── Routes ───────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """Landing page — enter a PR to review."""
    return f"""<!DOCTYPE html>
<html><head><title>WorkPlay</title>
<style>
  body {{ background: #1a1410; color: #d4c5a0; font-family: 'Palatino', serif;
         display: flex; align-items: center; justify-content: center;
         min-height: 100vh; flex-direction: column; }}
  h1 {{ color: #c9a84c; font-size: 2rem; margin-bottom: 1rem; }}
  .subtitle {{ opacity: 0.6; margin-bottom: 2rem; }}
  form {{ display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; }}
  input {{ background: #2a2015; border: 1px solid #c9a84c; color: #d4c5a0;
           padding: 0.75rem 1rem; font-size: 1rem; border-radius: 4px;
           font-family: 'Consolas', monospace; width: 400px; }}
  select {{ background: #2a2015; border: 1px solid #c9a84c; color: #d4c5a0;
            padding: 0.75rem; border-radius: 4px; }}
  button {{ background: #c9a84c; color: #1a1410; border: none;
            padding: 0.75rem 1.5rem; cursor: pointer; font-size: 1rem;
            border-radius: 4px; font-weight: bold; }}
  .stats {{ margin-top: 3rem; opacity: 0.5; font-size: 0.85rem; font-family: monospace; }}
</style></head>
<body>
  <h1>WorkPlay</h1>
  <p class="subtitle">The game IS the work.</p>
  <form action="/review" method="get">
    <input name="pr_url" placeholder="owner/repo#123 or full GitHub PR URL"
           required autofocus>
    <select name="theme">
      <option value="medieval">Medieval</option>
      <option value="scifi">Sci-fi</option>
      <option value="minimal">Minimal</option>
      <option value="work">Standard</option>
    </select>
    <button type="submit">Review</button>
  </form>
  <div class="stats">{telemetry.summary()}</div>
</body></html>"""


@app.get("/review", response_class=HTMLResponse)
@app.get("/review/{pr_number}", response_class=HTMLResponse)
async def review(request: Request, pr_number: int = 0):
    """Review a PR in themed or work view."""
    theme = request.query_params.get("theme", DEFAULT_THEME)
    repo_full_name = request.query_params.get("repo_full_name", "")
    return_theme = request.query_params.get("return_theme", "")

    # Parse PR URL from form
    pr_url = request.query_params.get("pr_url", "")
    owner, repo = "", ""

    if pr_url:
        # Parse: owner/repo#123 or https://github.com/owner/repo/pull/123
        if "github.com" in pr_url:
            parts = pr_url.rstrip("/").split("/")
            try:
                idx = parts.index("pull")
                owner, repo = parts[idx-2], parts[idx-1]
                pr_number = int(parts[idx+1])
            except (ValueError, IndexError):
                return HTMLResponse(f"Could not parse PR URL: {pr_url}", 400)
        elif "#" in pr_url:
            repo_part, num = pr_url.rsplit("#", 1)
            if "/" in repo_part:
                owner, repo = repo_part.split("/", 1)
                pr_number = int(num)
        else:
            return HTMLResponse("Format: owner/repo#123 or GitHub PR URL", 400)
    elif pr_number > 0:
        # Use cached PR data
        owner, repo = _repo(repo_full_name)
        pr_data = _cached(pr_number, repo_full_name)
        if pr_data and (not owner or not repo):
            full_name = pr_data.get("base", {}).get("repo", {}).get("full_name", "/")
            owner, repo = _repo(full_name)

    if not owner or not repo or not pr_number:
        return HTMLResponse("Missing PR info. Use: owner/repo#123", 400)

    # Fetch PR
    pr_data = await fetch_pr(owner, repo, pr_number)
    if "error" in pr_data:
        return HTMLResponse(f"Error: {pr_data['error']}", 500)

    # Classify
    key = _key(owner, repo, pr_number)
    if key not in classification_cache:
        cls = classify_pr(pr_data)
        classification_cache[key] = {
            "basin": cls.basin,
            "template": cls.template,
            "fidelity_tier": cls.fidelity_tier,
            "confidence": cls.confidence,
            "title": cls.title,
            "narrative": cls.narrative,
            "alternatives": cls.alternatives,
            "reason": cls.reason,
        }

    classification = dict(classification_cache[key])

    # Auto-select theme from classification if not specified
    if theme not in THEMES:
        theme = classification.get("template", DEFAULT_THEME)

    # Narrative fatigue
    mode = get_narrative_mode(theme)
    if mode == "silent":
        classification["narrative"] = ""
    elif mode == "brief":
        classification["narrative"] = (
            f"{classification.get('title', 'Review')}. "
            f"{len(pr_data.get('files', []))} files.")

    # Store owner/repo for API calls
    pr_data["_owner"] = owner
    pr_data["_repo"] = repo
    pr_data["_repo_full_name"] = f"{owner}/{repo}"
    if theme != "work":
        return_theme = theme
    elif return_theme not in THEMES or return_theme == "work":
        return_theme = classification.get("template", DEFAULT_THEME)

    return HTMLResponse(
        render_page(
            pr_data,
            classification,
            theme,
            repo_full_name=pr_data["_repo_full_name"],
            return_theme=return_theme,
        )
    )


@app.get("/api/diff/{pr_number}")
async def api_diff(pr_number: int, request: Request):
    """Fetch and render themed diff."""
    pr_data = _cached(pr_number, request.query_params.get("repo_full_name", ""))
    owner = pr_data.get("_owner", "")
    repo = pr_data.get("_repo", "")
    theme = request.query_params.get("theme", DEFAULT_THEME)

    if not owner or not repo:
        return HTMLResponse("PR not loaded. Review it first.")

    diff_text = await fetch_diff(owner, repo, pr_number)
    return HTMLResponse(render_diff(diff_text, theme))


@app.get("/api/issues/{pr_number}")
async def api_issues(pr_number: int, request: Request):
    """Gate-identified issues (stub — wire to jeff/gate in production)."""
    pr_data = _cached(pr_number, request.query_params.get("repo_full_name", ""))
    issues = []

    for f in pr_data.get("files", []):
        name = f.get("filename", "")
        if f.get("additions", 0) > 100:
            issues.append(f"{name}: large change ({f['additions']}+ lines) — review carefully")
        if "test" not in name.lower() and f.get("additions", 0) > 50:
            issues.append(f"{name}: significant changes without corresponding tests")

    return JSONResponse({"issues": issues or ["No issues detected by gate."]})


@app.get("/api/tests/{pr_number}")
async def api_tests(pr_number: int, request: Request):
    """Run tests (stub — wire to jeff/nerve in production)."""
    _cached(pr_number, request.query_params.get("repo_full_name", ""))
    return JSONResponse({"result": "Test execution not wired for MVP. "
                                    "Wire to jeff run 'pytest' for production."})


@app.post("/api/decide")
async def api_decide(request: Request):
    """Capture a review decision. Log telemetry. Optionally push to GitHub."""
    data = await request.json()

    pr_number = data.get("pr_number", 0)
    decision_str = data.get("decision", "")
    pr_data = _cached(pr_number, data.get("repo_full_name", ""))

    # Record telemetry
    d = Decision(
        task_id=str(data.get("task_id", pr_number)),
        pr_number=pr_number,
        view_mode=data.get("view_mode", "unknown"),
        presented_at=datetime.now(timezone.utc).isoformat(),
        decided_at=datetime.now(timezone.utc).isoformat(),
        time_on_task_ms=data.get("time_on_task_ms", 0),
        decision=decision_str,
        comment=data.get("comment", ""),
        artifact_opens=data.get("artifact_opens", 0),
        analysis_runs=data.get("analysis_runs", 0),
        issue_highlights=data.get("issue_highlights", 0),
        fidelity_tier=data.get("fidelity_tier", 2),
        template_used=data.get("view_mode", ""),
        kerf_confidence=data.get("kerf_confidence", 0),
        basin=classification_cache.get(
            _key(pr_data.get("_owner", ""), pr_data.get("_repo", ""), pr_number),
            {},
        ).get("basin", ""),
    )
    telemetry.record(d)

    # Push to GitHub if token available
    owner = pr_data.get("_owner", "")
    repo = pr_data.get("_repo", "")
    gh_result = {}

    if owner and repo and GITHUB_TOKEN:
        gh_result = await submit_review(
            owner, repo, pr_number, decision_str,
            data.get("comment", ""))

    return JSONResponse({
        "status": "recorded",
        "decision": decision_str,
        "telemetry_count": telemetry.count(),
        "github": gh_result,
    })


@app.post("/webhook/github")
async def github_webhook(request: Request):
    """Receive GitHub webhook for new/updated PRs."""
    body = await request.body()

    # Verify signature if secret configured
    if GITHUB_WEBHOOK_SECRET:
        sig = request.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(
            GITHUB_WEBHOOK_SECRET.encode(), body,
            hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise HTTPException(403, "Invalid webhook signature")

    event = request.headers.get("X-GitHub-Event", "")
    data = json.loads(body)

    if event == "pull_request" and data.get("action") in ("opened", "synchronize", "reopened"):
        pr = data.get("pull_request", {})
        pr_number = pr.get("number", 0)
        if pr_number:
            owner = data.get("repository", {}).get("owner", {}).get("login", "")
            repo_name = data.get("repository", {}).get("name", "")
            pr_data = await fetch_pr(owner, repo_name, pr_number)
            cls = classify_pr(pr_data)
            classification_cache[_key(owner, repo_name, pr_number)] = {
                "basin": cls.basin, "template": cls.template,
                "fidelity_tier": cls.fidelity_tier, "confidence": cls.confidence,
                "title": cls.title, "narrative": cls.narrative,
                "alternatives": cls.alternatives, "reason": cls.reason,
            }
            return JSONResponse({"status": "classified", "pr": pr_number,
                                "basin": cls.basin})

    return JSONResponse({"status": "ignored", "event": event})


@app.get("/api/telemetry")
async def api_telemetry():
    """Pilot telemetry summary."""
    return JSONResponse(telemetry.stats())


@app.get("/api/telemetry/export")
async def api_telemetry_export():
    """Export telemetry to CSV."""
    path = telemetry.export_csv()
    return JSONResponse({"exported": path})


# ── Entry Point ──────────────────────────────────────────────────

def serve(host: str = "0.0.0.0", port: int = PORT):
    """Start WorkPlay server."""
    import uvicorn
    print(f"""
    ┌──────────────────────────────────────┐
    │  WorkPlay v1.0.0                     │
    │  The game IS the work.               │
    │                                      │
    │  http://localhost:{port}               │
    │                                      │
    │  Theme: {DEFAULT_THEME:<20s}        │
    │  GitHub: {'connected' if GITHUB_TOKEN else 'read-only (set GITHUB_TOKEN)'}  │
    └──────────────────────────────────────┘
    """)
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    serve()
