"""Deterministic Trade Center scenarios for controlled tests only."""
from datetime import datetime, timedelta, timezone

from services.trade_intelligence import build_trade_intelligence


def _player(name, position, player_id, age=60):
    timestamp = (datetime.now(timezone.utc) - timedelta(seconds=age)).isoformat()
    return {
        "player": name,
        "position": position,
        "source_player_id": player_id,
        "local_player_id": f"local-{player_id}",
        "normalized_name": name.lower().replace(" ", ""),
        "identity_match_method": "DIRECT_SLEEPER_ID",
        "identity_state": "RESOLVED",
        "projection": 200,
        "projection_retrieved_at": timestamp,
        "projection_source": "Controlled projection",
        "weekly_score": 12,
        "weekly_baseline": 12,
        "matchup_rank": 12,
        "matchup_updated_at": timestamp,
        "matchup_source": "Controlled matchup",
        "opponent": "KC",
        "injury_status": "Healthy",
        "injury_multiplier": 1,
        "injury_updated_at": timestamp,
        "injury_source": "Controlled health",
        "roster_updated_at": timestamp,
        "roster_source": "Controlled roster",
        "is_bye": False,
        "evidence_gaps": [],
    }


def build_trade_scenario(name):
    if name not in {"ready", "ready_empty", "degraded", "blocked", "unsupported_partner_fit", "identity_ambiguity"}:
        name = "blocked"
        unknown = True
    else:
        unknown = False
    owner = [_player("Owner RB", "RB", "owner-rb"), _player("Owner WR", "WR", "owner-wr")]
    partner = [_player("Partner TE", "TE", "partner-te"), _player("Partner WR", "WR", "partner-wr")]
    owner[0]["projection"] = 120
    owner[0]["weekly_score"] = 7
    partner[0]["projection"] = 260
    partner[0]["weekly_score"] = 16
    if name == "degraded":
        partner[0]["matchup_updated_at"] = (datetime.now(timezone.utc) - timedelta(seconds=70000)).isoformat()
    if name == "blocked":
        partner[0]["projection_retrieved_at"] = None
    if name == "identity_ambiguity":
        partner[0]["identity_state"] = "AMBIGUOUS"
        partner[0]["identity_match_method"] = "UNRESOLVED"
    result = build_trade_intelligence(owner, partner, {"slot": 2, "name": "Scenario Partner"})
    if name == "ready_empty":
        result.update(allowed=True, publication_state="READY", one_for_one=[], two_for_one=[])
    if name == "degraded":
        result["integrity"]["confidence"] = {"label": "MEDIUM", "score": 75}
        result["integrity"]["confidence_score"] = 75
    if name == "unsupported_partner_fit" and result["one_for_one"]:
        result["one_for_one"][0]["explanation"]["partner_fit_state"] = "NOT_SUPPORTED"
    if name == "identity_ambiguity":
        result["blockers"] = sorted(set([*result["blockers"], "TRADE_IDENTITY_AMBIGUOUS"]))
        result.update(allowed=False, publication_state="BLOCKED", one_for_one=[], two_for_one=[])
    if unknown:
        result["blockers"] = sorted(set([*result["blockers"], "TRADE_SCENARIO_UNKNOWN"]))
        result.update(allowed=False, publication_state="BLOCKED", one_for_one=[], two_for_one=[])
    result["identity_lineage"] = [
        {key: player.get(key) for key in ("source_player_id", "local_player_id", "player", "normalized_name", "identity_match_method", "identity_state", "projection_source", "projection_retrieved_at")}
        for player in [*owner, *partner]
    ]
    return result