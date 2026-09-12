from __future__ import annotations

REQUIRED_POSITIONS = ("QB", "RB", "WR", "TE", "FLEX", "K", "DEF")


def _matchup_row(player):
    player = dict(player or {})
    is_bye = bool(player.get("is_bye"))
    gaps = list(player.get("evidence_gaps") or [])
    if not is_bye and not player.get("opponent"):
        gaps.append("OPPONENT_DATA_MISSING")
    if not is_bye and player.get("matchup_rank") is None:
        gaps.append("MATCHUP_RANK_MISSING")
    if not is_bye and player.get("matchup_modifier") is None:
        gaps.append("MATCHUP_MODIFIER_MISSING")
    gaps = sorted(set(gaps))
    state = "NOT_APPLICABLE" if is_bye else "UNAVAILABLE" if gaps else "AVAILABLE"
    return {
        "player": player.get("player"),
        "position": str(player.get("position") or "").upper().replace("DST", "DEF"),
        "state": state,
        "opponent": player.get("opponent"),
        "matchup_rank": player.get("matchup_rank"),
        "blockers": gaps,
    }


def build_team_accuracy_contract(roster, starters, league_settings, team_needs, team_health):
    settings = dict(league_settings or {})
    needs = dict(team_needs or {})
    health = dict(team_health or {})
    settings_available = settings.get("state") == "AVAILABLE"
    scoring_verified = settings_available and settings.get("full_ppr") is True
    missing_need_keys = [key for key in REQUIRED_POSITIONS if key not in needs]
    blocked_need_keys = [key for key in REQUIRED_POSITIONS if key in needs and (needs.get(key) or {}).get("state") != "AVAILABLE"]
    rows = [_matchup_row(player) for player in (starters or []) if not player.get("vacant")]
    matchup_blockers = sorted({blocker for row in rows for blocker in row["blockers"]})
    blockers = []
    if not settings_available:
        blockers.append(settings.get("blocker") or "LEAGUE_SETTINGS_UNAVAILABLE")
    if settings_available and not scoring_verified:
        blockers.append("FULL_PPR_SCORING_NOT_VERIFIED")
    if missing_need_keys:
        blockers.append("TEAM_NEED_KEYS_MISSING")
    if blocked_need_keys:
        blockers.append("TEAM_NEEDS_BLOCKED")
    blockers.extend(matchup_blockers)
    if health.get("state") != "AVAILABLE":
        blockers.append(health.get("blocker") or "TEAM_HEALTH_UNAVAILABLE")
    blockers = sorted(set(blockers))
    trusted = bool(rows) and not blockers
    if not rows:
        blockers.append("MATCHUP_DATA_MISSING")
    return {
        "state": "AVAILABLE" if trusted else "DEGRADED",
        "trusted": trusted,
        "source": settings.get("source") or "Unavailable",
        "league_settings": {
            "state": settings.get("state") or "UNAVAILABLE",
            "starter_slots": settings.get("starter_slots") or {},
            "flex_eligible_positions": settings.get("flex_eligible_positions") or [],
            "blocker": settings.get("blocker"),
        },
        "scoring": {
            "state": "AVAILABLE" if scoring_verified else "BLOCKED",
            "format": "Full PPR" if scoring_verified else "Unavailable",
            "blocker": None if scoring_verified else "FULL_PPR_SCORING_NOT_VERIFIED",
        },
        "team_needs": {
            "state": "AVAILABLE" if not missing_need_keys and not blocked_need_keys else "BLOCKED",
            "positions": {key: needs.get(key) for key in REQUIRED_POSITIONS},
            "missing_keys": missing_need_keys,
            "blocked_keys": blocked_need_keys,
        },
        "health": {
            "state": health.get("state") or "UNAVAILABLE",
            "source": health.get("source") or "Unavailable",
            "freshness_state": health.get("freshness_state") or "UNAVAILABLE",
            "blocker": health.get("blocker"),
        },
        "matchups": {"state": "AVAILABLE" if rows and not matchup_blockers else "UNAVAILABLE", "rows": rows, "blockers": matchup_blockers or ([] if rows else ["MATCHUP_DATA_MISSING"])},
        "blockers": sorted(set(blockers)),
        "recommendation_impact": (
            "League settings, Full-PPR scoring, team needs, health, and starter matchup evidence support this review."
            if trusted else
            "One or more evidence domains are unavailable. Treat affected lineup values as unavailable and review the listed blockers before relying on the recommendation."
        ),
    }
