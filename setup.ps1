# Jeff Setup — Steve's Rig
# Run once: powershell -ExecutionPolicy Bypass -File setup.ps1
# After: just type 'jeff' anywhere

Write-Host ""
Write-Host "    ┌──────────┐"
Write-Host "    │  ·    ·  │   Setting up Jeff..."
Write-Host "    │    ──    │   RTX 3090 · 24GB · Solar"
Write-Host "    └────┬─────┘"
Write-Host "    ┌────┴─────┐"
Write-Host "    │  [JEFF]  │"
Write-Host "    └──────────┘"
Write-Host ""

# ── Check Ollama ─────────────────────────────────────────────────
Write-Host "[1/5] Checking Ollama..."
try {
    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 5
    $modelCount = $response.models.Count
    Write-Host "  Ollama running. $modelCount models in pantry."
} catch {
    Write-Host "  Ollama not running. Start it: ollama serve"
    Write-Host "  Then re-run this script."
    exit 1
}

# ── Install Jeff ─────────────────────────────────────────────────
Write-Host "[2/5] Installing Jeff..."
$jeffDir = "A:\AI\jeff-release"
if (Test-Path $jeffDir) {
    Push-Location $jeffDir
    pip install -e . 2>$null
    if ($LASTEXITCODE -ne 0) {
        pip install -e .
    }
    Pop-Location
    Write-Host "  Jeff installed from $jeffDir"
} else {
    Write-Host "  Jeff not found at $jeffDir"
    Write-Host "  Extract jeff-1.0.0.tar.gz there first."
    exit 1
}

# ── Pull Recommended Models ──────────────────────────────────────
Write-Host "[3/5] Checking models..."

$models = @(
    "hermes3:8b",
    "qwen2.5-coder:7b",
    "deepseek-r1:7b"
)

foreach ($model in $models) {
    $existing = ollama list 2>$null | Select-String $model
    if ($existing) {
        Write-Host "  $model — already pulled"
    } else {
        Write-Host "  $model — pulling (this may take a while)..."
        ollama pull $model
    }
}

# ── Create Jeff Home ─────────────────────────────────────────────
Write-Host "[4/5] Creating Jeff home..."
$jeffHome = "$env:USERPROFILE\.jeff"
$dirs = @("blood", "forge\tools", "lore", "arcade", "voice\models")
foreach ($dir in $dirs) {
    $path = Join-Path $jeffHome $dir
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}
Write-Host "  Home at $jeffHome"

# ── Index Local Lore ─────────────────────────────────────────────
Write-Host "[5/5] Indexing local knowledge..."
python -c "
from jeff.sense.lore import index_all
for root in ['A:\\AI\\KERF', 'A:\\AI\\jeff-release', 'A:\\AI\\kerf-terminal']:
    try:
        r = index_all(root)
        print(f'  {root}: {r[\"total\"]} entries')
    except Exception as e:
        print(f'  {root}: skipped ({e})')
" 2>$null

# ── Done ─────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  Jeff is ready." -ForegroundColor Green
Write-Host ""
Write-Host "  Commands:"
Write-Host "    jeff              — status"
Write-Host "    jeff run <task>   — do the thing"
Write-Host "    jeff ask <query>  — one-shot"
Write-Host "    jeff audit        — quality gate"
Write-Host "    jeff ship         — build + test + deliver"
Write-Host "    jeff arcade       — play games, ship code"
Write-Host "    jeff local        — what's in the pantry"
Write-Host ""
Write-Host "  My name Jeff. I handle it."
Write-Host ""
