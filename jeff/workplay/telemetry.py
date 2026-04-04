"""jeff.workplay.telemetry — Pilot measurement.

Logs every decision with the schema from WorkPlay v1.0.0 spec.
Primary metric: time-to-correct-decision.
Exports to CSV for analysis.

AnnulusLabs LLC · April 2026
"""

import csv
import json
import time
import sqlite3
from dataclasses import dataclass, field, asdict
from pathlib import Path

TELEMETRY_DIR = Path.home() / ".jeff" / "workplay"
TELEMETRY_DB = TELEMETRY_DIR / "telemetry.db"


@dataclass
class Decision:
    task_id: str
    pr_number: int
    reviewer: str = "local"
    view_mode: str = "medieval"     # private — never reported
    presented_at: str = ""
    decided_at: str = ""
    time_on_task_ms: int = 0
    decision: str = ""              # approve, request_changes, reject
    comment: str = ""
    artifact_opens: int = 0
    analysis_runs: int = 0
    issue_highlights: int = 0
    fidelity_tier: int = 2
    template_used: str = "medieval"
    kerf_confidence: float = 0.0
    basin: str = ""
    decision_reversed_within_7d: bool = False
    post_merge_ci_failures: int = 0
    post_merge_bugs: int = 0
    post_merge_hotfix: bool = False
    voluntary_session: bool = True
    returned_without_prompt: bool = False


class TelemetryStore:
    """SQLite-backed telemetry. Append-only. Exportable."""

    def __init__(self, db_path: Path = TELEMETRY_DB):
        TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(db_path))
        self._init()

    def _init(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT, pr_number INTEGER,
                reviewer TEXT, view_mode TEXT,
                presented_at TEXT, decided_at TEXT,
                time_on_task_ms INTEGER, decision TEXT,
                comment TEXT, artifact_opens INTEGER,
                analysis_runs INTEGER, issue_highlights INTEGER,
                fidelity_tier INTEGER, template_used TEXT,
                kerf_confidence REAL, basin TEXT,
                decision_reversed_within_7d BOOLEAN,
                post_merge_ci_failures INTEGER,
                post_merge_bugs INTEGER,
                post_merge_hotfix BOOLEAN,
                voluntary_session BOOLEAN,
                returned_without_prompt BOOLEAN
            )""")
        self.db.commit()

    def record(self, d: Decision):
        data = asdict(d)
        cols = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        self.db.execute(
            f"INSERT INTO decisions ({cols}) VALUES ({placeholders})",
            list(data.values()))
        self.db.commit()

    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]

    def export_csv(self, path: str = None) -> str:
        """Export all decisions to CSV for analysis."""
        path = path or str(TELEMETRY_DIR / "workplay_pilot.csv")
        rows = self.db.execute("SELECT * FROM decisions").fetchall()
        cols = [d[0] for d in self.db.execute(
            "SELECT * FROM decisions LIMIT 1").description]

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(cols)
            writer.writerows(rows)

        return path

    def stats(self) -> dict:
        """Pilot summary statistics."""
        total = self.count()
        if total == 0:
            return {"total": 0}

        rows = self.db.execute("""
            SELECT
                COUNT(*) as total,
                AVG(time_on_task_ms) as avg_time_ms,
                SUM(CASE WHEN decision='approve' THEN 1 ELSE 0 END) as approvals,
                SUM(CASE WHEN decision='reject' THEN 1 ELSE 0 END) as rejections,
                SUM(CASE WHEN decision='request_changes' THEN 1 ELSE 0 END) as changes,
                AVG(artifact_opens) as avg_artifact_opens,
                AVG(analysis_runs) as avg_analysis_runs,
                AVG(kerf_confidence) as avg_confidence,
                SUM(CASE WHEN decision_reversed_within_7d THEN 1 ELSE 0 END) as reversals,
                SUM(CASE WHEN voluntary_session THEN 1 ELSE 0 END) as voluntary
            FROM decisions
        """).fetchone()

        return {
            "total": rows[0],
            "avg_time_ms": round(rows[1] or 0),
            "avg_time_seconds": round((rows[1] or 0) / 1000, 1),
            "approvals": rows[2],
            "rejections": rows[3],
            "changes_requested": rows[4],
            "avg_artifact_opens": round(rows[5] or 0, 1),
            "avg_analysis_runs": round(rows[6] or 0, 1),
            "avg_kerf_confidence": round(rows[7] or 0, 2),
            "reversal_rate": round((rows[8] or 0) / max(1, rows[0]), 3),
            "voluntary_rate": round((rows[9] or 0) / max(1, rows[0]), 2),
        }

    def summary(self) -> str:
        s = self.stats()
        if s["total"] == 0:
            return "No decisions recorded yet."
        return (f"Pilot: {s['total']} decisions, "
                f"avg {s['avg_time_seconds']}s/review, "
                f"{s['approvals']} approved, {s['rejections']} rejected, "
                f"{s['changes_requested']} changes requested, "
                f"reversal rate: {s['reversal_rate']:.1%}")
