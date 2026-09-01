#!/usr/bin/env python3
"""Fantasy Intelligence project health checker.

Run from the project root:
    source venv/bin/activate
    python verify_fantasy_intelligence.py
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_FILE = ROOT / "app.py"
TEMPLATE_FILE = ROOT / "templates" / "draftboard.html"
SERVICE_FILE = ROOT / "services" / "sleeper_service.py"

CHECKS: list[dict] = []


def record(name: str, passed: bool, detail: str = "") -> None:
    CHECKS.append({"name": name, "passed": bool(passed), "detail": detail})
    symbol = "PASS" if passed else "FAIL"
    print(f"[{symbol}] {name}" + (f": {detail}" if detail else ""))


def read_text(path: Path) -> str:
    if not path.exists():
        record(f"File exists: {path.relative_to(ROOT)}", False, "Missing")
        return ""
    record(f"File exists: {path.relative_to(ROOT)}", True, f"{path.stat().st_size} bytes")
    return path.read_text(encoding="utf-8")


def check_syntax(path: Path) -> None:
    try:
        py_compile.compile(str(path), doraise=True)
        record(f"Python syntax: {path.relative_to(ROOT)}", True)
    except Exception as exc:
        record(f"Python syntax: {path.relative_to(ROOT)}", False, str(exc))


def check_source(app_source: str, template_source: str, service_source: str) -> None:
    required_app_tokens = {
        "Flask application": "app = Flask(__name__)",
        "Draft Board route": 'def draftboard():',
        "Strategy route": 'def set_draft_strategy():',
        "Sleeper pick sync": 'def sync_sleeper_draft_picks():',
        "Sleeper player map": 'def sync_sleeper_player_map():',
        "Tier engine": 'def get_player_tier(',
        "Opponent forecast": 'def build_opponent_forecast(',
        "League tendencies": 'def build_league_tendencies(',
        "Monte Carlo": 'def run_monte_carlo_availability(',
        "Value gap": 'def build_value_gap_analysis(',
        "Round planner": 'def build_round_plan(',
        "Draft-now analyzer": 'def build_draft_now_wait_analysis(',
        "Recommendation candidates": 'recommendation_candidates = []',
        "Roster targets": 'ROSTER_TARGETS = {',
        "Strategy profiles": 'STRATEGY_PROFILES = {',
    }
    for label, token in required_app_tokens.items():
        record(label, token in app_source, token if token not in app_source else "")

    required_template_tokens = {
        "Draft Agent panel": "Draft Agent",
        "Top 5 panel": "Top 5 Recommendations",
        "Tier panel": "Tier Intelligence",
        "Opponent pressure panel": "Opponent Pressure Index",
        "Draft-now panel": "Draft Now vs. Wait",
        "League tendencies panel": "League Tendencies",
        "Availability simulation panel": "Availability Simulation",
        "Value gap panel": "Value Gap Analysis",
        "Round planner panel": "Round-by-Round Draft Plan",
        "Strategy selector": "Draft Strategy Profile",
    }
    for label, token in required_template_tokens.items():
        record(label, token in template_source, token if token not in template_source else "")

    required_service_tokens = {
        "Sleeper league API": "def get_league(",
        "Sleeper users API": "def get_users(",
        "Sleeper rosters API": "def get_rosters(",
        "Sleeper draft API": "def get_draft(",
        "Sleeper draft picks API": "def get_draft_picks(",
        "Sleeper players API": "def get_all_players(",
    }
    for label, token in required_service_tokens.items():
        record(label, token in service_source, token if token not in service_source else "")

    # Check dependency order inside draftboard().
    start = app_source.find("def draftboard():")
    end = app_source.find("\n@app.route(", start + 1) if start != -1 else -1
    body = app_source[start:end if end != -1 else len(app_source)] if start != -1 else ""

    dependencies = [
        ("league_tendencies = build_league_tendencies()", "player_league_bonus"),
        ("pick_forecast = build_opponent_forecast(", "run_monte_carlo_availability("),
        ("monte_carlo = run_monte_carlo_availability(", "build_value_gap_analysis("),
        ("recommendation_candidates = []", "top_recommendations = recommendation_candidates[:5]"),
    ]
    for assignment, use in dependencies:
        a = body.find(assignment)
        u = body.find(use)
        passed = a != -1 and u != -1 and a < u
        record(
            f"Initialization order: {assignment.split('=')[0].strip()}",
            passed,
            f"assignment line precedes use" if passed else f"assignment={a}, use={u}",
        )

    league_assignments = body.count("league_tendencies = build_league_tendencies()")
    record(
        "Exactly one League Tendencies initialization",
        league_assignments == 1,
        f"found {league_assignments}",
    )

    # Detect common pasted-HTML corruption in Python.
    corruption = [token for token in ("<br>", "&lt;", "&gt;") if token in app_source]
    record(
        "No HTML corruption in app.py",
        not corruption,
        ", ".join(corruption) if corruption else "",
    )


def check_import_and_routes() -> None:
    try:
        spec = importlib.util.spec_from_file_location("fantasy_intelligence_app", APP_FILE)
        if spec is None or spec.loader is None:
            raise RuntimeError("Unable to create import spec")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        record("Import app.py without starting Flask", True)

        routes = {rule.rule for rule in module.app.url_map.iter_rules()}
        required_routes = {
            "/",
            "/draftboard",
            "/draftboard/strategy",
            "/sleeper/draft-picks/sync",
            "/sleeper/players/sync",
            "/test-draft-picks",
        }
        for route in sorted(required_routes):
            record(f"Flask route: {route}", route in routes)
    except Exception as exc:
        record("Import app.py without starting Flask", False, repr(exc))


def check_database() -> None:
    try:
        import psycopg2
    except Exception as exc:
        record("psycopg2 available", False, repr(exc))
        return

    record("psycopg2 available", True)
    try:
        conn = psycopg2.connect(
            host=os.environ.get("FI_DB_HOST", "localhost"),
            port=int(os.environ.get("FI_DB_PORT", "5433")),
            database=os.environ.get("FI_DB_NAME", "fantasy_intelligence"),
            user=os.environ.get("FI_DB_USER", "fantasy"),
            password=os.environ.get("FI_DB_PASSWORD", "fantasy"),
            connect_timeout=5,
        )
        cur = conn.cursor()
        record("PostgreSQL connection", True)

        required_tables = {
            "players",
            "draft_board",
            "my_roster",
            "league_teams",
            "league_rosters",
            "sleeper_teams",
            "sleeper_drafts",
            "sleeper_draft_picks",
        }
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            """
        )
        tables = {row[0] for row in cur.fetchall()}
        for table in sorted(required_tables):
            record(f"Database table: {table}", table in tables)

        if "players" in tables:
            cur.execute("SELECT COUNT(*) FROM players")
            count = cur.fetchone()[0]
            record("Player pool loaded", count >= 500, f"{count} players")

            cur.execute(
                """
                SELECT COUNT(*)
                FROM players
                WHERE ranking IS NULL
                   OR player_name IS NULL
                   OR position IS NULL
                """
            )
            incomplete = cur.fetchone()[0]
            record("No incomplete core player rows", incomplete == 0, f"{incomplete} incomplete")

        cur.close()
        conn.close()
    except Exception as exc:
        record("PostgreSQL connection", False, repr(exc))


def main() -> int:
    print("Fantasy Intelligence Health Check")
    print("=" * 36)

    app_source = read_text(APP_FILE)
    template_source = read_text(TEMPLATE_FILE)
    service_source = read_text(SERVICE_FILE)

    if app_source:
        check_syntax(APP_FILE)
        try:
            ast.parse(app_source)
            record("AST parse: app.py", True)
        except Exception as exc:
            record("AST parse: app.py", False, str(exc))
    if service_source:
        check_syntax(SERVICE_FILE)

    check_source(app_source, template_source, service_source)
    if app_source:
        check_import_and_routes()
    check_database()

    failed = [check for check in CHECKS if not check["passed"]]
    report = {
        "passed": len(CHECKS) - len(failed),
        "failed": len(failed),
        "total": len(CHECKS),
        "failures": failed,
    }
    report_file = ROOT / "fantasy_intelligence_health_report.json"
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n" + "=" * 36)
    print(f"Passed: {report['passed']} / {report['total']}")
    print(f"Failed: {report['failed']}")
    print(f"Report: {report_file.name}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
