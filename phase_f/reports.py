from __future__ import annotations
import json
from pathlib import Path

def write_reports(output_dir, summary):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "draft_report.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    lines = [
        "# Phase F2 Draft Report",
        "",
        f"- Status: {summary['status']}",
        f"- Accepted picks: {summary['accepted_picks']}",
        f"- Recommendations: {summary['recommendations']}",
        f"- Strategy: {summary['strategy']}",
        f"- Synthetic adapter: {summary['synthetic']}",
        "",
        "## Safety",
        "",
        "- Sandbox mode only",
        "- No live Sleeper polling",
        "- No database migration included",
    ]
    (out / "draft_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
