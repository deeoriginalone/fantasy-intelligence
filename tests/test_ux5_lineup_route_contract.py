from pathlib import Path
from html.parser import HTMLParser

from jinja2 import Environment

from services.weekly_lineup_intelligence import build_lineup_intelligence
from owner_operations import build_lineup_reconciliation, build_recommended_bench


def player(name, position, score=10.0):
    return {
        "player": name,
        "position": position,
        "weekly_score": score,
        "weekly_baseline": score,
        "projection": score * 17,
        "rank": 100,
        "injury_status": "Healthy",
        "injury_multiplier": 1.0,
        "is_bye": False,
        "opponent": "X",
        "matchup_rank": 16,
        "matchup_modifier": 0.0,
    }


def test_lineup_route_redirects_to_unified_team_page():
    source = Path("owner_operations.py").read_text(encoding="utf-8")
    start = source.index('@bp.route("/lineup")')
    end = source.index('@bp.route("/waivers")', start)
    segment = source[start:end]

    assert 'redirect(url_for("owner_ops.team_page") + "#lineup", code=302)' in segment


def test_team_route_delegates_to_explainable_payload():
    source = Path("owner_operations.py").read_text(encoding="utf-8")
    start = source.index('@bp.route("/team")')
    end = source.index('@bp.route("/lineup")', start)
    segment = source[start:end]

    assert "context, roster, meta = current_roster(cur)" in segment
    assert "lineup_intelligence = build_lineup_intelligence(roster, current_starters=current_sleeper_starters)" in segment
    assert "lineup_intelligence=lineup_intelligence" in segment


class TeamPageContractParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.ids = []
        self.top_level_ids = []
        self.id_counts = {}
        self.id_tags = {}
        self.id_text = {}
        self.all_text = ""
        self.decision_items = 0
        self.verdict_blocks = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        element_id = attributes.get("id")
        classes = attributes.get("class", "").split()
        self.stack.append((tag, element_id, classes, attributes))
        if element_id:
            self.ids.append(element_id)
            self.id_counts[element_id] = self.id_counts.get(element_id, 0) + 1
            self.id_tags[element_id] = (tag, attributes)
            self.id_text.setdefault(element_id, "")
            if len(self.stack) > 1 and self.stack[-2][0] == "main" and "team-page" in self.stack[-2][2]:
                self.top_level_ids.append(element_id)
        if "decision-item" in classes and "biggest-decisions" in [item[1] for item in self.stack]:
            self.decision_items += 1
        if "verdict" in classes:
            self.verdict_blocks += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.all_text += data
        for _, element_id, _, _ in self.stack:
            if element_id:
                self.id_text[element_id] += data


def test_team_template_renders_required_primary_page_contract():
    from app import app
    from flask import render_template

    slots = ["QB", "RB1", "RB2", "WR1", "WR2", "TE", "FLEX", "K", "DEF"]
    starters = [
        {"slot": slot, "player": f"Player {slot}", "position": slot.rstrip("0123456789"), "weekly_score": 10.0, "opponent": "NYJ", "injury_status": "Healthy", "decision": "START", "vacant": False}
        for slot in slots
    ]
    changes = [{"slot": "QB", "current": "Alternative QB", "current_id": "old-qb", "recommended": "Player QB", "recommended_id": "new-qb", "authority": "START", "reason": "Supported recommendation reason.", "recommended_player": {**starters[0], "injury_status": "Healthy"}}]
    reconciliation = {
        "state": "AVAILABLE", "blocker": None,
        "current": [{"slot": slot, "player": f"Current {slot}", "player_id": f"current-{slot}", "position": slot.rstrip("0123456789"), "injury_status": "Healthy"} for slot in slots],
        "changes": changes,
    }
    context = {
        "title": "My Team", "context": {"mode": "LIVE"}, "meta": {"week": 4, "team_name": "Test Team"},
        "roster": [
            {"player": "Questionable Player", "injury_status": "Questionable"},
            {"player": "Out Player", "injury_status": "Out"},
            {"player": "Healthy Player", "injury_status": "Healthy"},
            {"player": "Unknown Player", "injury_status": "Unknown"},
        ],
        "league_settings": {"scoring_format": "PPR"}, "lineup_reconciliation": reconciliation,
        "lineup_comparison_unavailable": "Lineup comparison unavailable.", "lineup_intelligence": {"starters": starters, "bench": [], "verdict": {}},
        "decisions_by_slot": {"QB": {"decision": "START", "weekly_score_delta": 2.0, "alternative": "Alternative QB"}},
        "team_accuracy": {}, "team_health": {}, "team_needs": {}, "lineup_snapshot": {"counts": {"ready": 0, "monitor": 0, "blocked": 0}}, "weekly_risks": [],
        "roster_outlook": {}, "changes": {}, "opportunity_changes": {}, "opportunity_view": {}, "preliminary_matchup_context": {},
        "team_trust": {"confidence": {"label": "HIGH", "score": 80}}, "team_priority_action": {}, "bench_decisions": [], "bench_plan": {}, "team": {"lineage": []},
    }
    with app.test_request_context("/team"):
        html = render_template("team.html", **context)

    parser = TeamPageContractParser()
    parser.feed(html)
    required_ids = [
        "my-team-header", "your-lineup", "health-availability", "biggest-decisions",
        "why-these-decisions", "what-could-change", "supporting-roster-details", "data-model-diagnostics",
    ]
    assert all(parser.id_counts.get(element_id) == 1 for element_id in required_ids)
    positions = [parser.ids.index(element_id) for element_id in required_ids]
    assert positions == sorted(positions)
    assert parser.top_level_ids == required_ids
    assert "open" not in parser.id_tags["data-model-diagnostics"][1]
    lineup_text = parser.id_text["your-lineup"]
    assert all(slot in lineup_text for slot in slots)
    assert not any(term in lineup_text.lower() for term in ("source", "lineage", "2026-", "generated", "blocker_", "age in seconds"))
    assert "Current Sleeper Lineup" in parser.id_text["supporting-roster-details"]
    assert "Team Needs" in parser.id_text["supporting-roster-details"]
    assert "Bench Priority" in parser.id_text["supporting-roster-details"]
    for element_id in required_ids:
        if element_id != "supporting-roster-details":
            assert "Current Sleeper Lineup" not in parser.id_text[element_id]
            assert "Team Needs" not in parser.id_text[element_id]
            assert "Bench Priority" not in parser.id_text[element_id]
    assert "Current Sleeper Lineup" not in lineup_text
    assert parser.decision_items == 1
    assert "1 decision needs attention" in lineup_text
    health_text = parser.id_text["health-availability"]
    assert health_text.index("Out Player") < health_text.index("Questionable Player")
    assert health_text.index("Questionable Player") < health_text.index("Healthy Player")
    assert health_text.index("Healthy Player") < health_text.index("Unknown Player")
    assert "UNKNOWN" in health_text and "ACTIVE" in health_text
    assert parser.verdict_blocks == 0
    assert "Lineup needs attention" not in html
    assert "Additional evidence diagnostics" in parser.id_text["data-model-diagnostics"]
    for element_id in required_ids[:-1]:
        assert "Additional evidence diagnostics" not in parser.id_text[element_id]


def test_lineup_route_returns_302_and_preserves_fragment():
    import os

    os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")
    os.environ.setdefault("DB_HOST", "localhost")
    os.environ.setdefault("DB_PORT", "5433")
    os.environ.setdefault("DB_NAME", "fantasy_intelligence")
    os.environ.setdefault("DB_USER", "fantasy")
    os.environ.setdefault("DB_PASSWORD", "fantasy")
    os.environ.setdefault("ADMIN_TOKEN", "test-admin-token")
    os.environ.setdefault("SLEEPER_LEAGUE_ID", "league-123")
    os.environ.setdefault("SLEEPER_DRAFT_ID", "draft-123")
    from app import app

    response = app.test_client().get("/lineup", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/team#lineup")


def test_lineup_payload_uses_explicit_decisions_and_bench_order():
    roster = [
        player("QB1", "QB", 20),
        player("RB1", "RB", 18),
        player("RB2", "RB", 17),
        player("WR1", "WR", 16),
        player("WR2", "WR", 15),
        player("TE1", "TE", 12),
        player("FLEX1", "WR", 11),
        player("K1", "K", 9),
        player("DEF1", "DEF", 8),
        player("BENCH1", "WR", 7),
    ]
    payload = build_lineup_intelligence(roster)

    assert all("decision" in item for item in payload["start_sit_decisions"])
    assert not any(item.get("action") == "HOLD" for item in payload["start_sit_decisions"])
    assert {item["decision"] for item in payload["start_sit_decisions"]} <= {"START", "FLEX", "MONITOR"}
    assert [item["bench_order"] for item in payload["bench"]] == [1]
    assert payload["metric_definitions"]["baseline"]
    assert payload["metric_definitions"]["weekly_score"]


def test_lineup_reconciliation_keeps_sleeper_truth_separate_from_recommendation():
    current = [{"player": "Justin Herbert", "source_player_id": "Justin Herbert", "position": "QB", "weekly_score": 18.25, "sleeper_current_starter": True, "sleeper_lineup_slot": "QB", "injury_status": "Healthy"}]
    recommended = [{"player": "Joe Burrow", "source_player_id": "Joe Burrow", "position": "QB", "slot": "QB", "weekly_score": 20.0, "vacant": False}]
    result = build_lineup_reconciliation(current, recommended)
    assert result["state"] == "AVAILABLE"
    assert result["current"][0]["player"] == "Justin Herbert"
    assert result["changes"][0]["slot"] == "QB"
    assert result["changes"][0]["current"] == "Justin Herbert"
    assert result["changes"][0]["recommended"] == "Joe Burrow"
    assert result["changes"][0]["current_id"] == "Justin Herbert"
    assert result["changes"][0]["recommended_id"] == "Joe Burrow"
    assert "weekly_score_edge" not in result["changes"][0]


def render_start_sit_section(change):
    templates = Path(__file__).resolve().parents[1] / "templates"
    source = (templates / "team.html").read_text(encoding="utf-8")
    start = source.index('<section class="lineup-section" aria-labelledby="start-sit-decisions-title">')
    end = source.index("</section>", start) + len("</section>")
    return Environment().from_string(source[start:end]).render(
        lineup_reconciliation={
            "state": "AVAILABLE",
            "blocker": None,
            "current": [],
            "changes": [change],
        },
    )


def render_health_section(roster):
    templates = Path(__file__).resolve().parents[1] / "templates"
    source = (templates / "team.html").read_text(encoding="utf-8")
    start = source.index('<section class="lineup-section" aria-labelledby="health-availability-title">')
    end = source.index("</section>", start) + len("</section>")
    return Environment().from_string(source[start:end]).render(roster=roster)


def test_team_start_sit_template_renders_available_confidence_and_watch():
    html = render_start_sit_section({
        "slot": "QB",
        "authority": "START",
        "recommended": "Joe Burrow",
        "current": "Justin Herbert",
        "reason": "Supported reason supplied.",
        "recommended_player": {"player": "Joe Burrow", "reason": "Supported reason supplied."},
        "confidence": {"label": "HIGH", "score": 80},
        "watch_item": "HEALTH_EVIDENCE_STALE",
        "provider_projection": {
            "recommended": {
                "state": "PRELIMINARY", "projected_ppg": 18.25,
                "metric_name": "Provider Full-PPR Projection", "unit": "fantasy_points_per_game",
                "scoring_format": "ppr", "season": 2026, "week": 4,
                "data_through_week": 3, "source_record_time": "2026-10-05T06:20:00+00:00",
                "age_seconds": 3480, "freshness_state": "UNAVAILABLE",
                "evidence_level": "PRELIMINARY", "recommendation_impact": "INFORMATIONAL_ONLY",
                "attribution": "JerryGM projections attribution",
            },
            "current": {
                "state": "PRELIMINARY", "projected_ppg": 12.0,
                "metric_name": "Provider Full-PPR Projection", "unit": "fantasy_points_per_game",
                "scoring_format": "ppr", "season": 2026, "week": 4,
                "data_through_week": 3, "source_record_time": "2026-10-05T06:20:00+00:00",
                "age_seconds": 3480, "freshness_state": "UNAVAILABLE",
                "evidence_level": "PRELIMINARY", "recommendation_impact": "INFORMATIONAL_ONLY",
                "attribution": "JerryGM projections attribution",
            },
            "comparison": {"state": "UNAVAILABLE", "blocker": "JERRYGM_FRESHNESS_THRESHOLD_UNVERIFIED"},
        },
    })

    assert "START Joe Burrow" in html
    assert "SIT Justin Herbert" in html
    assert "Why:</strong> Supported reason supplied." in html
    assert "Confidence:</strong> HIGH" in html
    assert "Watch:</strong> Health information needs a pre-kickoff check." in html
    assert "Projection (informational only):</strong> 18.25 vs 12.00" in html
    assert "What could change this decision:" in html
    assert "generated 2026-10-05T06:20:00+00:00" in html
    assert "freshness UNAVAILABLE" in html
    assert "INFORMATIONAL_ONLY" in html
    assert "JerryGM projections attribution" in html
    assert "HEALTH_EVIDENCE_STALE" not in html
    assert "JERRYGM_FRESHNESS_THRESHOLD_UNVERIFIED" not in html
    assert "6.25" not in html


def test_team_start_sit_template_renders_unavailable_evidence_without_zero():
    html = render_start_sit_section({
        "slot": "QB",
        "authority": "START",
        "recommended": "Joe Burrow",
        "current": "Justin Herbert",
        "reason": "Supported reason supplied.",
        "recommended_player": {"player": "Joe Burrow", "reason": "Supported reason supplied."},
        "confidence": None,
        "watch_item": None,
    })

    assert "START Joe Burrow" in html
    assert "SIT Justin Herbert" in html
    assert "Why:</strong> Supported reason supplied." in html
    assert "Confidence:</strong> UNAVAILABLE" in html
    assert "Watch:</strong> No specific watch item was supplied." in html
    assert "Projection:</strong> UNAVAILABLE" in html
    assert "0.00" not in html


def test_team_health_section_surfaces_status_and_missing_evidence():
    html = render_health_section([
        {"player": "Out Player", "injury_status": "Out"},
        {"player": "Questionable Player", "injury_status": "Questionable"},
        {"player": "Healthy Player", "injury_status": "Healthy"},
        {"player": "Unknown Player", "injury_status": "Unknown"},
    ])

    assert "Out Player" in html and "OUT" in html and "Remove from consideration" in html
    assert "Questionable Player" in html and "QUESTIONABLE" in html and "Monitor before kickoff" in html
    assert "Healthy Player" in html and "HEALTHY" in html and "Available" in html
    assert "Unknown Player" in html and "UNAVAILABLE" in html and "Availability information unavailable" in html


def test_lineup_reconciliation_numbers_duplicate_sleeper_running_back_slots():
    current = [
        {"player": "Rico Dowdle", "source_player_id": "rico", "position": "RB", "sleeper_current_starter": True, "sleeper_lineup_slot": "RB", "sleeper_lineup_index": 2},
        {"player": "RB One", "source_player_id": "rb-one", "position": "RB", "sleeper_current_starter": True, "sleeper_lineup_slot": "RB", "sleeper_lineup_index": 1},
    ]
    recommended = [
        {"player": "RB One", "source_player_id": "rb-one", "position": "RB", "slot": "RB1", "vacant": False},
        {"player": "Kenny Gainwell", "source_player_id": "kenny", "position": "RB", "slot": "RB2", "vacant": False},
    ]
    result = build_lineup_reconciliation(current, recommended)
    assert result["changes"][0]["slot"] == "RB2"
    assert result["changes"][0]["current"] == "Rico Dowdle"
    assert result["changes"][0]["recommended"] == "Kenny Gainwell"
    assert result["changes"][0]["current_id"] == "rico"
    assert result["changes"][0]["recommended_id"] == "kenny"


def test_lineup_reconciliation_fails_closed_without_sleeper_starters():
    result = build_lineup_reconciliation([{"player": "Joe Burrow"}], [{"player": "Joe Burrow", "slot": "QB", "vacant": False}])
    assert result["state"] == "UNAVAILABLE"


def test_reconciliation_uses_stable_ids_and_changed_slots_only():
    roster = [
        {"player": "Current QB", "source_player_id": "qb-old", "sleeper_current_starter": True, "sleeper_lineup_slot": "QB", "injury_status": "Healthy"},
        {"player": "Incoming QB", "source_player_id": "qb-new", "sleeper_current_starter": False, "sleeper_lineup_slot": None, "injury_status": "Healthy"},
        {"player": "Unchanged RB", "source_player_id": "rb-1", "sleeper_current_starter": True, "sleeper_lineup_slot": "RB", "sleeper_lineup_index": 1, "injury_status": "Healthy"},
    ]
    result = build_lineup_reconciliation(roster, [
        {"player": "Incoming QB", "source_player_id": "qb-new", "position": "QB", "slot": "QB", "vacant": False},
        {"player": "Unchanged RB", "source_player_id": "rb-1", "position": "RB", "slot": "RB1", "vacant": False},
    ])
    assert [(item["current_id"], item["recommended_id"], item["slot"]) for item in result["changes"]] == [("qb-old", "qb-new", "QB")]
    assert [item["player"] for item in result["changed_recommended"]] == ["Incoming QB"]


def test_recommended_bench_is_roster_minus_recommended_starter_ids():
    roster = [
        {"player": "Starter", "source_player_id": "p1", "position": "WR", "weekly_score": 10, "weekly_baseline": 10, "injury_status": "Healthy", "injury_multiplier": 1, "is_bye": False},
        {"player": "Healthy Bench", "source_player_id": "p2", "position": "WR", "weekly_score": 8, "weekly_baseline": 8, "injury_status": "Healthy", "injury_multiplier": 1, "is_bye": False},
        {"player": "Out Bench", "source_player_id": "p3", "position": "RB", "weekly_score": 7, "weekly_baseline": 7, "injury_status": "Out", "injury_multiplier": 0, "is_bye": False},
    ]
    bench = build_recommended_bench(roster, [{"player": "Starter", "source_player_id": "p1", "vacant": False}])
    assert [item["source_player_id"] for item in bench] == ["p2", "p3"]
    assert all(item["source_player_id"] != "p1" for item in bench)
    assert bench[0]["decision"] == "SIT"
    assert bench[1]["decision"] == "MONITOR"
