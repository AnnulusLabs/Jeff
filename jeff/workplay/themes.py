"""jeff.workplay.themes — Themed review interfaces.

Three game themes + standard work view. Toggle switches CSS class.
Diff viewer styled to match theme — cognitive continuity.

The game FRAMES the artifact. It never REPLACES it.
"View Blueprint" opens the ACTUAL diff.

AnnulusLabs LLC · April 2026
"""

import json

THEMES = {
    "medieval": {
        "name": "Kingdom Review",
        "bg": "#1a1410",
        "fg": "#d4c5a0",
        "accent": "#c9a84c",
        "accent2": "#8b2500",
        "panel_bg": "#2a2015",
        "diff_bg": "#1e1a12",
        "diff_add": "#8b7d3c",
        "diff_del": "#8b2500",
        "font": "'Palatino Linotype', 'Book Antiqua', serif",
        "mono": "'Courier New', monospace",
        "npc": "Blacksmith",
        "approve_label": "Commission",
        "reject_label": "Reject Blueprint",
        "changes_label": "Send to Forge",
        "view_artifact": "View Blueprint",
        "run_tests": "Test Under Load",
        "show_issues": "Inspect Joints",
    },
    "scifi": {
        "name": "Command Deck",
        "bg": "#0a0e14",
        "fg": "#00ff88",
        "accent": "#00ccff",
        "accent2": "#ff6600",
        "panel_bg": "#0d1117",
        "diff_bg": "#0a0e11",
        "diff_add": "#00ccaa",
        "diff_del": "#ff6644",
        "font": "'Consolas', 'SF Mono', monospace",
        "mono": "'Consolas', monospace",
        "npc": "Ship AI",
        "approve_label": "Authorize",
        "reject_label": "Abort Sequence",
        "changes_label": "Flag for Reanalysis",
        "view_artifact": "Display Schematic",
        "run_tests": "Run Diagnostics",
        "show_issues": "Scan for Anomalies",
    },
    "minimal": {
        "name": "Review",
        "bg": "#f8f6f0",
        "fg": "#2d2d2d",
        "accent": "#4a7c59",
        "accent2": "#8b4513",
        "panel_bg": "#fffef8",
        "diff_bg": "#faf8f2",
        "diff_add": "#4a7c59",
        "diff_del": "#a0522d",
        "font": "'Inter', 'Segoe UI', sans-serif",
        "mono": "'JetBrains Mono', 'Fira Code', monospace",
        "npc": "Reviewer",
        "approve_label": "Approve",
        "reject_label": "Reject",
        "changes_label": "Request Changes",
        "view_artifact": "View Diff",
        "run_tests": "Run Tests",
        "show_issues": "Show Issues",
    },
    "work": {
        "name": "Standard Review",
        "bg": "#ffffff",
        "fg": "#24292e",
        "accent": "#0366d6",
        "accent2": "#cb2431",
        "panel_bg": "#f6f8fa",
        "diff_bg": "#fafbfc",
        "diff_add": "#28a745",
        "diff_del": "#cb2431",
        "font": "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "mono": "'SFMono-Regular', 'Consolas', monospace",
        "npc": "",
        "approve_label": "Approve",
        "reject_label": "Reject",
        "changes_label": "Request Changes",
        "view_artifact": "View Diff",
        "run_tests": "Run Tests",
        "show_issues": "Show Issues",
    },
}


def render_page(pr: dict, classification: dict, theme_name: str = "medieval",
                diff_html: str = "", repo_full_name: str = "",
                return_theme: str = "medieval") -> str:
    """Render the full WorkPlay review page."""
    theme = THEMES.get(theme_name, THEMES["work"])
    is_work = theme_name == "work"

    task_title = classification.get("title", pr.get("title", "Review"))
    narrative = classification.get("narrative", "")
    npc = theme.get("npc", "")
    basin = classification.get("basin", "unknown")
    confidence = classification.get("confidence", 0)
    tier = classification.get("fidelity_tier", 2)
    pr_title = pr.get("title", "Untitled PR")
    pr_number = pr.get("number", "?")
    pr_author = pr.get("user", {}).get("login", "unknown")
    files_changed = len(pr.get("files", []))
    additions = sum(f.get("additions", 0) for f in pr.get("files", []))
    deletions = sum(f.get("deletions", 0) for f in pr.get("files", []))
    repo_full_name = repo_full_name or pr.get("_repo_full_name", "")
    return_theme = return_theme if return_theme in THEMES and return_theme != "work" else "medieval"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WorkPlay — {task_title}</title>
<style>
  :root {{
    --bg: {theme['bg']};
    --fg: {theme['fg']};
    --accent: {theme['accent']};
    --accent2: {theme['accent2']};
    --panel: {theme['panel_bg']};
    --diff-bg: {theme['diff_bg']};
    --diff-add: {theme['diff_add']};
    --diff-del: {theme['diff_del']};
    --font: {theme['font']};
    --mono: {theme['mono']};
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: var(--bg); color: var(--fg);
    font-family: var(--font); line-height: 1.6;
    min-height: 100vh; padding: 2rem;
  }}
  .header {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 1rem 0; border-bottom: 1px solid var(--accent);
    margin-bottom: 2rem;
  }}
  .header h1 {{ font-size: 1.4rem; color: var(--accent); }}
  .toggle {{
    background: var(--panel); border: 1px solid var(--accent);
    color: var(--accent); padding: 0.5rem 1rem; cursor: pointer;
    font-family: var(--mono); font-size: 0.85rem; border-radius: 4px;
  }}
  .toggle:hover {{ background: var(--accent); color: var(--bg); }}
  .kerf-explain {{
    background: var(--panel); padding: 0.5rem 1rem;
    font-size: 0.75rem; color: var(--fg); opacity: 0.7;
    border-left: 3px solid var(--accent); margin-bottom: 1.5rem;
    font-family: var(--mono); cursor: pointer;
  }}
  .kerf-explain:hover {{ opacity: 1; }}
  .mission {{
    background: var(--panel); padding: 2rem;
    border: 1px solid var(--accent); border-radius: 8px;
    margin-bottom: 2rem;
  }}
  .mission h2 {{ color: var(--accent); margin-bottom: 0.5rem; }}
  .mission .narrative {{
    font-style: italic; opacity: 0.8; margin-bottom: 1.5rem;
  }}
  .mission .meta {{
    font-family: var(--mono); font-size: 0.8rem; opacity: 0.6;
  }}
  .actions {{
    display: flex; gap: 1rem; margin: 1.5rem 0; flex-wrap: wrap;
  }}
  .action-btn {{
    background: var(--panel); border: 1px solid var(--accent);
    color: var(--accent); padding: 0.75rem 1.5rem; cursor: pointer;
    font-family: var(--font); font-size: 0.9rem; border-radius: 4px;
    transition: all 0.15s;
  }}
  .action-btn:hover {{
    background: var(--accent); color: var(--bg); transform: translateY(-1px);
  }}
  .decisions {{
    display: flex; gap: 1rem; margin-top: 2rem;
    padding-top: 1.5rem; border-top: 1px solid var(--accent);
  }}
  .decide {{
    padding: 0.75rem 2rem; border: 2px solid; cursor: pointer;
    font-family: var(--font); font-size: 1rem; border-radius: 4px;
    font-weight: bold; transition: all 0.15s;
  }}
  .decide.approve {{ border-color: var(--diff-add); color: var(--diff-add); }}
  .decide.approve:hover {{ background: var(--diff-add); color: var(--bg); }}
  .decide.changes {{ border-color: var(--accent); color: var(--accent); }}
  .decide.changes:hover {{ background: var(--accent); color: var(--bg); }}
  .decide.reject {{ border-color: var(--diff-del); color: var(--diff-del); }}
  .decide.reject:hover {{ background: var(--diff-del); color: var(--bg); }}
  .diff-container {{
    background: var(--diff-bg); border: 1px solid var(--accent);
    border-radius: 4px; padding: 1rem; margin: 1rem 0;
    font-family: var(--mono); font-size: 0.85rem;
    max-height: 60vh; overflow-y: auto; display: none;
    white-space: pre-wrap; line-height: 1.4;
  }}
  .diff-container.visible {{ display: block; }}
  .diff-add {{ color: var(--diff-add); }}
  .diff-del {{ color: var(--diff-del); }}
  .diff-hunk {{ color: var(--accent); opacity: 0.6; }}
  .comment-box {{
    width: 100%; min-height: 100px; margin-top: 1rem;
    background: var(--panel); border: 1px solid var(--accent);
    color: var(--fg); font-family: var(--mono); font-size: 0.85rem;
    padding: 0.75rem; border-radius: 4px; display: none; resize: vertical;
  }}
  .comment-box.visible {{ display: block; }}
  .audit {{
    margin-top: 2rem; padding: 1rem; background: var(--panel);
    border: 1px solid var(--accent); border-radius: 4px;
    font-family: var(--mono); font-size: 0.75rem; opacity: 0.5;
  }}
  .files-list {{
    margin: 1rem 0; font-family: var(--mono); font-size: 0.8rem;
  }}
  .files-list .file {{
    padding: 0.25rem 0; border-bottom: 1px solid rgba(128,128,128,0.1);
  }}
  .file .additions {{ color: var(--diff-add); }}
  .file .deletions {{ color: var(--diff-del); }}
</style>
</head>
<body>
  <div class="header">
    <h1>{'🏰 ' if theme_name=='medieval' else '🚀 ' if theme_name=='scifi' else ''}{theme['name']}</h1>
    <div>
      <button class="toggle" onclick="toggleView()" id="toggleBtn">
        {'Switch to Work View' if not is_work else 'Switch to Themed View'}
      </button>
      <button class="toggle" onclick="toggleKerf()" style="margin-left:0.5rem">
        Why this mapping?
      </button>
    </div>
  </div>

  <div class="kerf-explain" id="kerfExplain" style="display:none">
    Basin: {basin} ({confidence:.0%} confidence) · Tier {tier} ·
    {classification.get('reason', 'No classification data')}
    {' · Alternatives: ' + ', '.join(a['basin'] + f" ({a['confidence']:.0%})" for a in classification.get('alternatives', [])) if classification.get('alternatives') else ''}
  </div>

  <div class="mission">
    <h2>{task_title if not is_work else f'PR #{pr_number}: {pr_title}'}</h2>
    {'<p class="narrative">' + (f'{npc}: ' if npc else '') + narrative + '</p>' if not is_work and narrative and tier < 3 else ''}
    <div class="meta">
      {'Author: ' + pr_author + ' · ' if is_work else ''}
      {files_changed} file{'s' if files_changed != 1 else ''} ·
      <span style="color:var(--diff-add)">+{additions}</span> /
      <span style="color:var(--diff-del)">-{deletions}</span>
    </div>

    <div class="files-list" id="filesList">
      {''.join(f'<div class="file">{f.get("filename","")} <span class="additions">+{f.get("additions",0)}</span> <span class="deletions">-{f.get("deletions",0)}</span></div>' for f in pr.get("files", [])[:20])}
    </div>

    <div class="actions">
      <button class="action-btn" onclick="toggleDiff()">
        {theme['view_artifact']}
      </button>
      <button class="action-btn" onclick="showIssues()">
        {theme['show_issues']}
      </button>
      <button class="action-btn" onclick="runTests()">
        {theme['run_tests']}
      </button>
    </div>

    <div class="diff-container" id="diffView">
{diff_html or '<span class="diff-hunk">No diff loaded. Click view to fetch.</span>'}
    </div>

    <div class="decisions">
      <button class="decide approve" onclick="decide('approve')">
        {theme['approve_label']}
      </button>
      <button class="decide changes" onclick="decide('request_changes')">
        {theme['changes_label']}
      </button>
      <button class="decide reject" onclick="decide('reject')">
        {theme['reject_label']}
      </button>
    </div>

    <textarea class="comment-box" id="commentBox"
              placeholder="{'The blacksmith asks: what needs refinement?' if theme_name=='medieval' else 'Specify required changes...' if theme_name=='scifi' else 'Comments...'}"></textarea>
  </div>

  <div class="audit" id="auditLog">
    Task presented: <span id="presentedAt"></span> ·
    View: <span id="viewMode">{theme_name}</span> ·
    Decision: <span id="decisionField">pending</span> ·
    Time on task: <span id="timeOnTask">0s</span>
  </div>

<script>
  const startTime = Date.now();
  const taskId = '{pr.get("id", pr_number)}';
  const repoFullName = {json.dumps(repo_full_name)};
  const returnTheme = {json.dumps(return_theme)};
  let currentTheme = '{theme_name}';
  let artifactOpens = 0;
  let analysisRuns = 0;
  let issueHighlights = 0;

  document.getElementById('presentedAt').textContent = new Date().toISOString();

  // Update timer
  setInterval(() => {{
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    document.getElementById('timeOnTask').textContent = elapsed + 's';
  }}, 1000);

  function toggleView() {{
    const isWork = currentTheme === 'work';
    const params = new URLSearchParams({{
      theme: isWork ? returnTheme : 'work',
      repo_full_name: repoFullName,
      return_theme: isWork ? returnTheme : currentTheme,
    }});
    window.location.href = '/review/{pr_number}?' + params.toString();
  }}

  function toggleKerf() {{
    const el = document.getElementById('kerfExplain');
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
  }}

  function toggleDiff() {{
    const el = document.getElementById('diffView');
    el.classList.toggle('visible');
    if (el.classList.contains('visible')) {{
      artifactOpens++;
      if (!el.dataset.loaded) {{
        fetch('/api/diff/{pr_number}?' + new URLSearchParams({{
          theme: currentTheme,
          repo_full_name: repoFullName,
        }}).toString())
          .then(r => r.text())
          .then(html => {{ el.innerHTML = html; el.dataset.loaded = '1'; }});
      }}
    }}
  }}

  function showIssues() {{
    issueHighlights++;
    fetch('/api/issues/{pr_number}?' + new URLSearchParams({{
      repo_full_name: repoFullName,
    }}).toString())
      .then(r => r.json())
      .then(data => {{
        alert(data.issues ? data.issues.join('\\n') : 'No issues detected.');
      }});
  }}

  function runTests() {{
    analysisRuns++;
    fetch('/api/tests/{pr_number}?' + new URLSearchParams({{
      repo_full_name: repoFullName,
    }}).toString())
      .then(r => r.json())
      .then(data => {{
        alert(data.result || 'Tests complete.');
      }});
  }}

  function decide(decision) {{
    if (decision === 'request_changes') {{
      document.getElementById('commentBox').classList.add('visible');
      document.getElementById('commentBox').focus();
      // Change button to submit
      const btn = document.querySelector('.decide.changes');
      if (btn.dataset.ready) {{
        submitDecision(decision);
      }} else {{
        btn.textContent = 'Submit Changes';
        btn.dataset.ready = '1';
      }}
      return;
    }}
    submitDecision(decision);
  }}

  function submitDecision(decision) {{
    const elapsed = Date.now() - startTime;
    const comment = document.getElementById('commentBox').value;
    const payload = {{
      task_id: taskId,
      pr_number: {pr_number},
      repo_full_name: repoFullName,
      decision: decision,
      comment: comment,
      time_on_task_ms: elapsed,
      view_mode: currentTheme,
      artifact_opens: artifactOpens,
      analysis_runs: analysisRuns,
      issue_highlights: issueHighlights,
      fidelity_tier: {tier},
      kerf_confidence: {confidence},
    }};

    document.getElementById('decisionField').textContent = decision;

    fetch('/api/decide', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(payload),
    }})
    .then(r => r.json())
    .then(data => {{
      document.querySelector('.mission').style.opacity = '0.5';
      document.querySelector('.decisions').innerHTML =
        '<div style="color:var(--accent);font-size:1.2rem">' +
        (decision === 'approve' ? '✓ {theme["approve_label"]}d' :
         decision === 'reject' ? '✗ {theme["reject_label"]}ed' :
         '↩ {theme["changes_label"]}') + '</div>';
    }});
  }}
</script>
</body>
</html>"""


def render_diff(diff_text: str, theme_name: str = "medieval") -> str:
    """Render a diff with themed colors."""
    theme = THEMES.get(theme_name, THEMES["work"])
    lines = []
    for line in diff_text.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            lines.append(f'<span class="diff-add">{_escape(line)}</span>')
        elif line.startswith("-") and not line.startswith("---"):
            lines.append(f'<span class="diff-del">{_escape(line)}</span>')
        elif line.startswith("@@"):
            lines.append(f'<span class="diff-hunk">{_escape(line)}</span>')
        else:
            lines.append(_escape(line))
    return "\n".join(lines)


def _escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))
