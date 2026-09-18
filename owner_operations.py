from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from weekly_intelligence import enrich_players, current_week, upcoming_byes
from services.weekly_lineup_intelligence import build_lineup_intelligence, optimize_lineup
from services.trade_intelligence import build_trade_intelligence
from services.opportunity_evidence import build_opportunity_view
from services.trade_target_center import build_trade_target_center
from services.decision_ranking import build_action, build_decision_ranking
from services.matchup_intelligence import build_matchup_intelligence
from services.preliminary_matchup_context import build_preliminary_matchup_context
from services.ux_evidence import derived_waiver_availability, evaluate_waiver_availability, resolve_waiver_candidate_identity, shared_league_facts, waiver_evidence_contract, waiver_ownership_freshness, waiver_roster_coverage, weekly_evidence_contract
from services.team_needs import build_team_needs_summary, league_settings_contract, team_needs_contract
from services.team_health import team_health_contract, apply_player_health_to_recommendations, health_freshness_from_report_date
from services.ux2_team_accuracy import build_team_accuracy_contract
from services.team_priority import build_team_priority_action
from services.team_hardening import build_bench_decisions, build_bench_plan, build_lineup_snapshot, build_roster_outlook, build_team_trust_summary, build_weekly_risks
from services.player_opportunity_reader import read_player_what_changed
from services.gsis_identity_crosswalk import attach_opportunity_player_ids
from services.nflverse_player_metadata import acquire_nflverse_player_metadata

POSITIONS = ("QB", "RB", "WR", "TE", "K", "DEF")
STARTER_SLOTS = ("QB", "RB1", "RB2", "WR1", "WR2", "TE", "FLEX", "K", "DEF")


def build_team_opportunity_changes(connection, roster, *, season, week, nflverse_records=None, nflverse_lineage=None):
    """Build informational What Changed evidence for explicitly linked players."""
    result = {"state": "UNAVAILABLE", "players": [], "blockers": [], "decision_effect": "INFORMATIONAL_ONLY"}
    if not isinstance(season, int) or isinstance(season, bool) or season <= 0:
        result["blockers"] = ["OPPORTUNITY_SEASON_INVALID"]
        return result
    if not isinstance(week, int) or isinstance(week, bool) or week <= 0:
        result["blockers"] = ["OPPORTUNITY_WEEK_INVALID"]
        return result
    mapped_roster = attach_opportunity_player_ids(
        roster or [],
        nflverse_records or [],
        nflverse_lineage=nflverse_lineage,
    ) if nflverse_records is not None else [dict(player) for player in (roster or [])]
    for player in mapped_roster:
        name = player.get("player") or "Unnamed player"
        opportunity_player_id = player.get("opportunity_player_id")
        if not isinstance(opportunity_player_id, str) or not opportunity_player_id.strip():
            result["players"].append({
                "player": name,
                "state": "UNAVAILABLE",
                "opportunity_identity_state": player.get("opportunity_identity_state", "UNRESOLVED"),
                "blockers": ["OPPORTUNITY_PLAYER_IDENTITY_UNAVAILABLE"],
                "decision_effect": "INFORMATIONAL_ONLY",
            })
            continue
        comparison = read_player_what_changed(
            connection,
            player_id=opportunity_player_id,
            season=season,
            week=week,
        )
        result["players"].append({"player": name, "opportunity_player_id": opportunity_player_id, **comparison})
    if not result["players"]:
        result["blockers"] = ["OPPORTUNITY_ROSTER_EMPTY"]
    elif all(item["state"] == "AVAILABLE" for item in result["players"]):
        result["state"] = "AVAILABLE"
    elif any(item["state"] == "BLOCKED" for item in result["players"]):
        result["state"] = "BLOCKED"
        result["blockers"] = list(dict.fromkeys(
            blocker for item in result["players"] for blocker in item.get("blockers", [])
        ))
    else:
        result["state"] = "UNAVAILABLE"
        result["blockers"] = list(dict.fromkeys(
            blocker for item in result["players"] for blocker in item.get("blockers", [])
        ))
    return result


def waiver_projection_contribution(candidate):
    """Return optional projection evidence without treating warnings as authority."""
    candidate = dict(candidate or {})
    identity = candidate.get("identity_resolution") or {}
    available = (
        candidate.get("projection") is not None
        and bool(candidate.get("projection_retrieved_at"))
        and identity.get("resolution_state") in {None, "RESOLVED"}
    )
    evidence = candidate.get("projection_evidence") or {}
    return {
        "value": candidate.get("projection") if available else None,
        "state": "AVAILABLE" if available else "UNAVAILABLE",
        "warnings": list(evidence.get("blockers") or []),
    }


def create_owner_operations_blueprint(
    get_db_connection,
    get_league,
    get_users,
    get_rosters,
    get_all_players,
    normalize_player_name,
):
    bp = Blueprint("owner_ops", __name__)

    def data_context(cur):
        cur.execute(
            """
            SELECT state_value
            FROM application_state
            WHERE state_key = 'active_sandbox'
            """
        )
        row = cur.fetchone()
        state = row[0] if row else None
        if state and state.get("mode") == "MOCK" and state.get("draft_id"):
            return {"mode": "MOCK", "draft_id": int(state["draft_id"])}
        return {"mode": "LIVE", "draft_id": None}

    def row_to_player(row, projection_retrieved_at=None, local_player_id=None):
        return {
            "player": row[0],
            "position": (row[1] or "NA").upper().replace("DST", "DEF"),
            "nfl_team": row[2] or "FA",
            "rank": row[3],
            "projection": float(row[4] or 0),
            "tier": row[5],
            "adp": float(row[6]) if row[6] is not None else None,
            "bye_week": row[7],
            "injury_status": row[8] or "Healthy / Not listed",
            "pick_no": row[9] if len(row) > 9 else None,
            "round": row[10] if len(row) > 10 else None,
            "projection_retrieved_at": projection_retrieved_at,
            "local_player_id": local_player_id,
        }

    def mock_roster(cur, draft_id, draft_slot=None):
        if draft_slot is None:
            cur.execute("SELECT draft_position FROM mock_drafts WHERE id = %s", (draft_id,))
            found = cur.fetchone()
            draft_slot = found[0] if found else 5
        cur.execute(
            """
            SELECT
                mp.player_name,
                UPPER(mp.position),
                mp.nfl_team,
                mp.overall_rank,
                p.projected_points,
                p.tier,
                p.adp,
                p.bye_week,
                p.injury_status,
                mp.pick_no,
                mp.round_num,
                p.projection_retrieved_at
            FROM mock_picks mp
            LEFT JOIN players p ON p.player_name = mp.player_name
            WHERE mp.draft_id = %s
              AND mp.draft_slot = %s
            ORDER BY mp.pick_no
            """,
            (draft_id, draft_slot),
        )
        return [row_to_player(row, row[11] if len(row) > 11 else None) for row in cur.fetchall()]

    def live_roster(cur):
        league = get_league(current_app.config.get("SLEEPER_LEAGUE_ID", "")) or {}
        users = get_users(current_app.config.get("SLEEPER_LEAGUE_ID", "")) or []
        rosters = get_rosters(current_app.config.get("SLEEPER_LEAGUE_ID", "")) or []
        all_players = get_all_players() or {}
        sleeper_retrieved_at = datetime.now(timezone.utc).isoformat()
        owner_ids = {
            str(user.get("user_id"))
            for user in users
            if user.get("is_owner") is True
        }
        owner_roster = next(
            (r for r in rosters if str(r.get("owner_id") or "") in owner_ids),
            None,
        )
        if not owner_roster:
            return [], league
        player_ids = [str(pid) for pid in (owner_roster.get("players") or [])]
        local_names = []
        for pid in player_ids:
            raw = all_players.get(pid) or {}
            name = raw.get("full_name") or " ".join(
                part for part in (raw.get("first_name"), raw.get("last_name")) if part
            )
            if name:
                local_names.append((pid, name, raw.get("position"), raw.get("team"), raw.get("injury_status") or raw.get("status")))
        result = []
        for sleeper_player_id, name, position, team, raw_status in local_names:
            cur.execute(
                """
                SELECT player_name, UPPER(position), nfl_team, ranking,
                       projected_points, tier, adp, bye_week, injury_status,
                       projection_retrieved_at, id
                FROM players
                WHERE REGEXP_REPLACE(LOWER(player_name), '[^a-z0-9]', '', 'g') = %s
                LIMIT 1
                """,
                (normalize_player_name(name),),
            )
            row = cur.fetchone()
            if not row:
                normalized_name = normalize_player_name(name)
                cur.execute(
                    """
                    SELECT player_name, UPPER(position), nfl_team, ranking,
                           projected_points, tier, adp, bye_week, injury_status,
                           projection_retrieved_at, id
                    FROM players
                    WHERE REGEXP_REPLACE(LOWER(player_name), '[^a-z0-9]', '', 'g') LIKE %s
                    ORDER BY LENGTH(player_name)
                    LIMIT 1
                    """,
                    (f"{normalized_name}%",),
                )
                row = cur.fetchone()
            if row:
                player=row_to_player(row, row[9] if len(row) > 9 else None, row[10] if len(row) > 10 else None)
                player["source_player_id"] = sleeper_player_id
                player["sleeper_gsis_id"] = raw.get("gsis_id")
                player["sleeper_metadata_retrieved_at"] = sleeper_retrieved_at
                player["normalized_name"] = normalize_player_name(name)
                player["identity_match_method"] = "UNIQUE_NORMALIZED_NAME"
                player["identity_state"] = "RESOLVED"
                if raw_status:
                    player["injury_status"] = raw_status
                    player["injury_source"] = "Sleeper API"
                    player["health_fetched_at"] = sleeper_retrieved_at
                    player["injury_updated_at"] = sleeper_retrieved_at
                    player["health_status_available"] = True
                else:
                    player["injury_status"] = "Unknown"
                    player["injury_source"] = "Sleeper API"
                    player["health_status_available"] = False
                player["ownership"] = "ROSTERED"
                player["ownership_source"] = "Sleeper API"
                player["roster_updated_at"] = sleeper_retrieved_at
                player["roster_source"] = "Sleeper API"
                result.append(player)
            else:
                player = {
                    "player": name,
                    "position": (position or "NA").upper().replace("DST", "DEF"),
                    "nfl_team": team or "FA",
                    "rank": None,
                    "projection": 0.0,
                    "tier": None,
                    "adp": None,
                    "bye_week": None,
                    "injury_status": raw.get("injury_status") or raw.get("status") or "Unknown",
                    "injury_source": "Sleeper API",
                    "pick_no": None,
                    "round": None,
                }
                player["injury_source"] = "Sleeper API"
                player["source_player_id"] = sleeper_player_id
                player["sleeper_gsis_id"] = raw.get("gsis_id")
                player["sleeper_metadata_retrieved_at"] = sleeper_retrieved_at
                player["normalized_name"] = normalize_player_name(name)
                player["identity_match_method"] = "LOCAL_PLAYER_UNAVAILABLE"
                player["identity_state"] = "UNRESOLVED"
                player["health_status_available"] = player["injury_status"] != "Unknown"
                player["ownership"] = "ROSTERED"
                player["ownership_source"] = "Sleeper API"
                player["roster_updated_at"] = sleeper_retrieved_at
                player["roster_source"] = "Sleeper API"
                if player["health_status_available"]:
                    player["health_fetched_at"] = sleeper_retrieved_at
                    player["injury_updated_at"] = sleeper_retrieved_at
                result.append(player)
        return result, league

    def current_roster(cur):
        context = data_context(cur)
        season = 2026
        if context["mode"] == "MOCK":
            cur.execute(
                "SELECT draft_name, strategy, draft_position FROM mock_drafts WHERE id = %s",
                (context["draft_id"],),
            )
            row = cur.fetchone()
            roster = mock_roster(cur, context["draft_id"], row[2] if row else 5)
            week = current_week(cur)
            roster = enrich_players(cur, roster, week)
            return context, roster, {
                "team_name": "My Mock Team",
                "league_name": "Season Sandbox",
                "strategy": row[1] if row else "WR_HEAVY",
                "draft_name": row[0] if row else f"Mock #{context['draft_id']}",
                "season": season,
                "week": week,
                "shared_facts": shared_league_facts({}, source="Season Sandbox", blocker="LIVE_LEAGUE_FACTS_NOT_APPLICABLE"),
            }
        roster, league = live_roster(cur)
        week = current_week(cur)
        roster = enrich_players(cur, roster, week, allow_local_weekly_data=True, allow_local_health_fallback=False, require_automated_weekly_evidence=True)
        return context, roster, {
            "team_name": "DiE-HaRd-9eRs-FaN",
            "league_name": league.get("name") or "Fantasy Intelligence Champions League",
            "strategy": "LIVE",
            "draft_name": None,
            "season": season,
            "week": week,
            "shared_facts": shared_league_facts(league),
        }

    def roster_analysis(roster, vacancies):
        counts = {pos: sum(1 for p in roster if p["position"] == pos) for pos in POSITIONS}
        targets = {"QB": 2, "RB": 4, "WR": 4, "TE": 2, "K": 1, "DEF": 1}
        needs = []
        grades = {}
        for pos in POSITIONS:
            count = counts[pos]
            target = targets[pos]
            ratio = count / target if target else 1
            grades[pos] = "A" if ratio >= 1 else "B" if ratio >= .75 else "C" if ratio >= .5 else "F"
            if count < target:
                needs.append(f"Add {pos} depth: {count} rostered, target {target}.")
        for slot in vacancies:
            message = f"Fill vacant {slot} starter slot before Week 1."
            if message not in needs:
                needs.insert(0, message)
        injured = [p for p in roster if str(p["injury_status"]).lower() not in {"healthy / not listed", "healthy", "none", ""}]
        if injured:
            needs.append(f"Monitor {len(injured)} player(s) with an injury designation.")
        score = sum(min(counts[p] / targets[p], 1) for p in POSITIONS) / len(POSITIONS) * 100
        overall = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 45 else "F"
        return counts, grades, needs, overall, round(score)

    def waiver_pool_with_evidence(cur, context, roster, limit=40):
        roster_names = {p["player"] for p in roster}
        if context["mode"] == "MOCK":
            cur.execute(
                """
                SELECT p.player_name, UPPER(p.position), p.nfl_team, p.ranking,
                       p.projected_points, p.tier, p.adp, p.bye_week, p.injury_status
                FROM players p
                WHERE UPPER(p.position) IN ('QB','RB','WR','TE','K','DEF')
                  AND NOT EXISTS (
                      SELECT 1 FROM mock_picks mp
                      WHERE mp.draft_id = %s AND mp.player_name = p.player_name
                  )
                ORDER BY p.ranking NULLS LAST
                LIMIT %s
                """,
                (context["draft_id"], limit),
            )
        else:
            cur.execute(
                """
                SELECT player_name, UPPER(position), nfl_team, ranking,
                       projected_points, tier, adp, bye_week, injury_status
                FROM players
                WHERE UPPER(position) IN ('QB','RB','WR','TE','K','DEF')
                ORDER BY ranking NULLS LAST
                LIMIT %s
                """,
                (max(120, limit * 3),),
            )
        rows = [row_to_player(tuple(row) + (None, None)) for row in cur.fetchall()]
        if context["mode"] != "LIVE":
            candidates = [{**row, "player_id": normalize_player_name(row["player"])} for row in rows if row["player"] not in roster_names][:limit]
            return evaluate_waiver_availability(
                candidates,
                waiver_evidence_contract(domain="waiver ownership", source="Season Sandbox", freshness_state="BLOCKED", completeness_state="UNKNOWN", blocker="WAIVER_LIVE_OWNERSHIP_REQUIRED"),
                waiver_evidence_contract(domain="waiver eligibility", source="Season Sandbox", freshness_state="BLOCKED", completeness_state="UNKNOWN", blocker="WAIVER_LIVE_ELIGIBILITY_REQUIRED"),
            )
        return _live_waiver_evidence(rows, current_app.config.get("SLEEPER_LEAGUE_ID", ""), get_league, get_rosters, get_all_players, normalize_player_name, limit)

    def _live_waiver_evidence(rows, league_id, league_fetcher, roster_fetcher, catalog_fetcher, name_normalizer, limit=40):
        retrieved_at = datetime.now(timezone.utc).isoformat()
        try:
            league = league_fetcher(league_id)
            all_rosters = roster_fetcher(league_id)
            catalog = catalog_fetcher()
        except Exception:
            league = None
            catalog = None
            all_rosters = None
        expected_count = (league or {}).get("total_rosters") if isinstance(league, dict) else None
        coverage = waiver_roster_coverage(all_rosters, expected_count)
        catalog_ok = isinstance(catalog, dict) and bool(catalog)
        rosters_ok = isinstance(all_rosters, list) and all(
            isinstance(item, dict) and isinstance(item.get("players"), list)
            for item in all_rosters or []
        )
        ownership_blocker = None
        if catalog is None or all_rosters is None:
            ownership_blocker = "WAIVER_OWNERSHIP_RETRIEVAL_FAILED"
        elif not catalog_ok:
            ownership_blocker = "WAIVER_PLAYER_CATALOG_UNAVAILABLE"
        elif not rosters_ok:
            ownership_blocker = "WAIVER_ROSTER_DATA_INCOMPLETE"
        elif coverage["blockers"]:
            ownership_blocker = coverage["blockers"][0]
        owned_ids = {
            str(player_id)
            for item in all_rosters or []
            for player_id in item.get("players") or []
            if player_id is not None and str(player_id)
        }
        resolutions = [
            resolve_waiver_candidate_identity(row, catalog, name_normalizer)
            for row in rows
        ]
        ownership_freshness = waiver_ownership_freshness(
            source_record_time=None,
            retrieved_at=retrieved_at,
            source="Sleeper API",
        )
        ownership = waiver_evidence_contract(
            domain="waiver ownership",
            league_id=league_id,
            source="Sleeper API",
            source_record_time=None,
            retrieved_at=retrieved_at,
            age=ownership_freshness["age"],
            freshness_threshold_id=ownership_freshness["freshness_threshold_id"],
            freshness_state=ownership_freshness["freshness_state"],
            completeness_state="COMPLETE" if not ownership_blocker else "INCOMPLETE",
            blocker=ownership_blocker or ownership_freshness["blocker"],
            recommendation_impact="BLOCKED",
            expected_active_roster_count=coverage["expected_active_roster_count"],
            observed_active_roster_count=coverage["observed_active_roster_count"],
            unique_owned_player_ids=owned_ids,
            require_roster_coverage=True,
        )
        candidates = [
            {
                **row,
                "player_id": resolution.get("resolved_player_id"),
                "identity_resolution": resolution,
            }
            for row, resolution in zip(rows, resolutions)
        ]
        supported_positions = {
            str(position).upper().replace("DST", "DEF")
            for position in (league or {}).get("roster_positions") or []
            if str(position).upper().replace("DST", "DEF") in POSITIONS
        }
        availability = derived_waiver_availability(
            league_id=league_id,
            ownership={**ownership, "owned_player_ids": owned_ids},
            supported_player_ids=(catalog or {}).keys(),
            supported_positions=supported_positions,
            candidates=candidates,
            identity_diagnostics={
                "total_source_candidates": len(candidates),
                "directly_resolved_count": sum(
                    item["resolution_method"] == "DIRECT_SLEEPER_ID" for item in resolutions
                ),
                "uniquely_canonical_resolved_count": sum(
                    item["resolution_method"] == "UNIQUE_CANONICAL_MATCH" for item in resolutions
                ),
                "unresolved_count": sum(item["resolution_state"] == "UNRESOLVED" for item in resolutions),
                "ambiguous_count": sum(item["resolution_state"] == "AMBIGUOUS" for item in resolutions),
                "conflicting_count": sum(item["resolution_state"] == "CONFLICTING" for item in resolutions),
                "unsupported_count": sum(item["resolution_state"] == "UNSUPPORTED" for item in resolutions),
            },
        )
        result = evaluate_waiver_availability(
            candidates,
            {**ownership, "owned_player_ids": owned_ids},
            availability,
        )
        result["candidates"] = result["candidates"][:limit]
        decision_evidence = weekly_evidence_contract(
            domain="waiver ranking inputs", source=None, freshness_state="UNAVAILABLE", completeness_state="UNAVAILABLE",
            blocker="WAIVER_RANKING_SOURCE_UNVERIFIED", fallback_used="local player projections/rankings",
            recommendation_impact="Waiver candidates remain visible only as unranked research until automated ranking and projection evidence is available.",
        )
        result["decision_evidence"] = decision_evidence
        if not decision_evidence["authoritative"]:
            result["allowed"] = False
            result["candidates"] = []
            result["blockers"] = list(dict.fromkeys([*(result.get("blockers") or []), decision_evidence["blocker"]]))
        availability["identity_diagnostics"].update(
            rostered_exclusion_count=sum(
                item.get("resolved_player_id") in owned_ids
                for item in resolutions
                if item.get("resolved_player_id")
            ),
            verified_unrostered_count=len(result["candidates"]),
            published_count=len(result["candidates"]),
        )
        return result

    def waiver_pool(cur, context, roster, limit=40):
        return waiver_pool_with_evidence(cur, context, roster, limit)["candidates"]

    def faab_recommendations(pool, counts):
        targets = {"QB": 2, "RB": 4, "WR": 4, "TE": 2, "K": 1, "DEF": 1}
        recs = []
        for player in pool:
            need = max(0, targets.get(player["position"], 1) - counts.get(player["position"], 0))
            rank_value = max(0, 110 - (player["rank"] or 110))
            tier_value = max(0, 7 - (player["tier"] or 7)) * 5
            score = rank_value + tier_value + need * 20
            bid = max(0, min(35, round(score / 6)))
            if player["position"] in {"K", "DEF"}:
                bid = min(bid, 3)
            projection_info = waiver_projection_contribution(player)
            projection_contribution = projection_info["value"]
            recs.append({**player, "priority_score": round(score, 1), "faab": bid, "bid_low": max(0, bid - 3), "bid_high": min(40, bid + 4), "need": need, "projection_contribution": projection_contribution, "projection_contribution_state": projection_info["state"], "projection_warnings": projection_info["warnings"]})
        return sorted(recs, key=lambda p: (-p["priority_score"], -(p["projection_contribution"] if p["projection_contribution"] is not None else float("-inf")), p["rank"] or 9999))

    def other_mock_teams(cur, draft_id):
        cur.execute(
            """
            SELECT DISTINCT draft_slot, team_name
            FROM mock_picks
            WHERE draft_id = %s
            ORDER BY draft_slot
            """,
            (draft_id,),
        )
        return [{"slot": row[0], "name": row[1]} for row in cur.fetchall()]

    @bp.route("/team")
    def team_page():
        conn = get_db_connection(); cur = conn.cursor()
        try:
            context, roster, meta = current_roster(cur)
            preliminary_matchup_context = build_preliminary_matchup_context(
                current_app.config.get("PRELIMINARY_MATCHUP_EVIDENCE"),
                roster=roster,
            )
            opportunity_view = build_opportunity_view(current_app.config.get("OPPORTUNITY_EVIDENCE"))
            starters, bench, total, vacancies = optimize_lineup(roster)
            counts, grades, _, overall, score = roster_analysis(roster, vacancies)
            league_payload = get_league(current_app.config.get("SLEEPER_LEAGUE_ID", "")) or {} if context["mode"] == "LIVE" else {}
            league_settings = league_settings_contract(league_payload, source="Sleeper API" if context["mode"] == "LIVE" else "Season Sandbox", blocker=None if context["mode"] == "LIVE" else "LIVE_LEAGUE_SETTINGS_NOT_APPLICABLE")
            team_needs = team_needs_contract(roster, league_settings)
            needs = build_team_needs_summary(team_needs)
            if context["mode"] == "LIVE":
                fetched_at = next((player.get("health_fetched_at") for player in roster if player.get("health_fetched_at")), None)
                if fetched_at and any(player.get("health_status_available") for player in roster):
                    health_meta = health_freshness_from_report_date(fetched_at)
                    health_source = "Sleeper API"
                else:
                    health_meta = {"freshness_state": "UNAVAILABLE", "last_verified": None, "age": None}
                    health_source = "Sleeper API"
            else:
                health_meta = {"freshness_state": "UNAVAILABLE", "last_verified": None, "age": None}
                health_source = "Season Sandbox"
            team_health = team_health_contract(roster, source=health_source, **health_meta)
            team_accuracy = build_team_accuracy_contract(roster, starters, league_settings, team_needs, team_health)
            nflverse_records = current_app.config.get("NFLVERSE_PLAYER_METADATA")
            nflverse_lineage = current_app.config.get("NFLVERSE_PLAYER_METADATA_LINEAGE")
            if nflverse_records is None and not current_app.testing:
                metadata = acquire_nflverse_player_metadata()
                if metadata["state"] == "AVAILABLE":
                    nflverse_records = metadata["rows"]
                    nflverse_lineage = metadata["lineage"]
            opportunity_changes = build_team_opportunity_changes(
                conn,
                roster,
                season=meta.get("season"),
                week=meta.get("week"),
                nflverse_records=nflverse_records,
                nflverse_lineage=nflverse_lineage,
            )
        finally:
            cur.close(); conn.close()
        weekly_defaults = {
            "weekly_baseline": 0.0, "matchup_modifier": 0.0,
            "injury_multiplier": 1.0, "weekly_score": None,
            "is_bye": False, "bye_week": None, "opponent": None,
            "home_away": None, "game_time_pacific": None,
            "matchup_rank": None, "injury_status": "Unknown", "vacant": False,
        }
        for player in [*starters, *bench]:
            for key, value in weekly_defaults.items(): player.setdefault(key, value)
        health_source = team_health.get("source") or ("Sleeper" if context["mode"] == "LIVE" else "Season Sandbox")
        health_freshness = team_health.get("freshness_state") or "UNAVAILABLE"
        apply_player_health_to_recommendations(
            starters,
            source=health_source,
            freshness_state=health_freshness,
            blocker=(team_health.get("blocker") if team_health.get("state") == "BLOCKED" else None),
        )
        for player in [*starters, *bench]:
            player["weekly_value_state"] = "AVAILABLE" if player.get("weekly_score") is not None else "UNAVAILABLE"
            gaps = player.get("evidence_gaps") or []
            player["health_shared_only"] = team_health.get("state") != "AVAILABLE" and not any(
                gap not in {"HEALTH_UNAVAILABLE", "HEALTH_BLOCKED", "HEALTH_EVIDENCE_STALE", "HEALTH_REFRESH_FAILED", "TEAM_HEALTH_UNAVAILABLE", "TEAM_HEALTH_STALE"}
                for gap in gaps
            )
        team_priority_action = build_team_priority_action(starters, team_needs, team_health, team_accuracy)
        team_accuracy["recommendation_impact"] = team_priority_action["action"]
        team_trust = build_team_trust_summary(team_accuracy, team_health, starters, bench)
        bench_decisions = build_bench_decisions(starters, bench)
        bench_plan = build_bench_plan(bench_decisions)
        lineup_snapshot = build_lineup_snapshot(starters, bench_decisions)
        weekly_risks = build_weekly_risks(starters, team_needs, team_health, team_accuracy)
        roster_outlook = build_roster_outlook(team_needs, team_health)
        lineup_intelligence = build_lineup_intelligence(roster)
        decisions_by_slot = {d.get("slot"): d for d in lineup_intelligence.get("start_sit_decisions", [])}
        return render_template("team.html", title="My Team", context=context, roster=roster, meta=meta, starters=starters, bench=bench, total=total, vacancies=vacancies, counts=counts, grades=grades, needs=needs, overall=overall, roster_score=score, league_settings=league_settings, team_needs=team_needs, team_health=team_health, team_accuracy=team_accuracy, team_priority_action=team_priority_action, team_trust=team_trust, bench_decisions=bench_decisions, bench_plan=bench_plan, lineup_snapshot=lineup_snapshot, weekly_risks=weekly_risks, roster_outlook=roster_outlook, lineup_intelligence=lineup_intelligence, decisions_by_slot=decisions_by_slot, preliminary_matchup_context=preliminary_matchup_context, opportunity_view=opportunity_view, opportunity_changes=opportunity_changes)

    @bp.route("/lineup")
    def lineup_page():
        return redirect(url_for("owner_ops.team_page") + "#lineup", code=302)

    @bp.route("/waivers")
    def waivers_page():
        conn = get_db_connection(); cur = conn.cursor()
        try:
            context, roster, meta = current_roster(cur)
            starters, bench, total, vacancies = optimize_lineup(roster)
            counts, grades, needs, overall, score = roster_analysis(roster, vacancies)
            pool_evidence = waiver_pool_with_evidence(cur, context, roster)
            recommendations = faab_recommendations(pool_evidence["candidates"], counts)[:25]
        finally:
            cur.close(); conn.close()
        return render_template("waivers.html", title="Waiver and FAAB Center", context=context, meta=meta, recommendations=recommendations, needs=needs, vacancies=vacancies, faab_budget=100, waiver_evidence=pool_evidence, opportunity_view=build_opportunity_view(current_app.config.get("OPPORTUNITY_EVIDENCE")))

    @bp.route("/trades")
    def trades_page():
        conn = get_db_connection(); cur = conn.cursor()
        try:
            scenario=(current_app.config.get("TRADE_SCENARIO") or request.args.get("trade_scenario")) if current_app.testing else None
            if scenario:
                from services.trade_scenarios import build_trade_scenario
                trade_intelligence=build_trade_scenario(scenario)
                trade_target_center=build_trade_target_center(trade_intelligence)
                return render_template("trades.html",title="Trade Target Center",context={"mode":"SCENARIO"},meta={"team_name":"Controlled Team"},teams=[trade_intelligence["partner"]],target_slot=trade_intelligence["partner"].get("slot"),trade_intelligence=trade_intelligence,trade_target_center=trade_target_center)
            context, roster, meta = current_roster(cur)
            teams=[]; target_roster=[]; partner={}
            target_slot=request.args.get("team",type=int)
            if context["mode"] == "MOCK":
                teams=[t for t in other_mock_teams(cur,context["draft_id"]) if t["name"] != "My Mock Team"]
                partner=next((t for t in teams if t["slot"]==target_slot),{})
                if target_slot:target_roster=mock_roster(cur,context["draft_id"],target_slot);target_roster=enrich_players(cur,target_roster,current_week(cur))
            else:
                league_id=current_app.config.get("SLEEPER_LEAGUE_ID","")
                users=get_users(league_id) or [];sleep_rosters=get_rosters(league_id) or [];catalog=get_all_players() or {}
                sleeper_retrieved_at=datetime.now(timezone.utc).isoformat()
                users_by_id={str(u.get("user_id")):u for u in users};owner_ids={str(u.get("user_id")) for u in users if u.get("is_owner") is True}
                for item in sleep_rosters:
                    rid=int(item.get("roster_id") or 0);oid=str(item.get("owner_id") or "")
                    if oid in owner_ids:continue
                    user=users_by_id.get(oid,{}) or {};metadata=user.get("metadata") or {};name=metadata.get("team_name") or user.get("display_name") or f"Roster {rid}"
                    teams.append({"slot":rid,"name":name})
                    if target_slot==rid:
                        partner={"slot":rid,"name":name};raw=[]
                        for pid in item.get("players") or []:
                            data=catalog.get(str(pid),{}) or {};full=data.get("full_name") or " ".join(x for x in (data.get("first_name"),data.get("last_name")) if x)
                            if not full:continue
                            cur.execute("SELECT player_name,UPPER(position),nfl_team,ranking,projected_points,tier,adp,bye_week,injury_status,projection_retrieved_at,id FROM players WHERE REGEXP_REPLACE(REGEXP_REPLACE(LOWER(player_name),'[^a-z0-9]','','g'),'(jr|sr|ii|iii|iv|il|ill)$','','g')=%s LIMIT 1",(normalize_player_name(full),))
                            row=cur.fetchone()
                            player=row_to_player(row,row[9] if len(row)>9 else None,row[10] if len(row)>10 else None) if row else {"player":full,"position":str(data.get("position") or "NA").upper().replace("DST","DEF"),"nfl_team":data.get("team") or "FA","rank":None,"projection":None,"tier":None,"adp":None,"bye_week":None,"injury_status":"Unknown","pick_no":None,"round":None,"projection_retrieved_at":None,"local_player_id":None}
                            player["source_player_id"]=str(pid);player["normalized_name"]=normalize_player_name(full);player["identity_match_method"]="UNIQUE_NORMALIZED_NAME" if row else "LOCAL_PLAYER_UNAVAILABLE";player["identity_state"]="RESOLVED" if row else "UNRESOLVED"
                            player["roster_updated_at"]=sleeper_retrieved_at;player["roster_source"]="Sleeper API"
                            status=data.get("injury_status") or data.get("status")
                            player["injury_source"]="Sleeper API";player["health_status_available"]=bool(status)
                            if status:
                                player["injury_status"]=status;player["health_fetched_at"]=sleeper_retrieved_at;player["injury_updated_at"]=sleeper_retrieved_at
                            raw.append(player)
                        target_roster=enrich_players(cur,raw,current_week(cur))
            trade_intelligence=build_trade_intelligence(
                roster,
                target_roster,
                partner,
            )
            trade_target_center=build_trade_target_center(trade_intelligence)
        finally:
            cur.close();conn.close()
        return render_template("trades.html",title="Trade Target Center",context=context,meta=meta,teams=teams,target_slot=target_slot,trade_intelligence=trade_intelligence,trade_target_center=trade_target_center,opportunity_view=build_opportunity_view(current_app.config.get("OPPORTUNITY_EVIDENCE")))

    @bp.route("/gm")
    def gm_page():
        conn = get_db_connection(); cur = conn.cursor()
        try:
            context, roster, meta = current_roster(cur)
            starters, bench, total, vacancies = optimize_lineup(roster)
            counts, grades, needs, overall, score = roster_analysis(roster, vacancies)
            pool_evidence = waiver_pool_with_evidence(cur, context, roster, limit=20)
            waivers = faab_recommendations(pool_evidence["candidates"], counts)[:5]
            lineup_intelligence = build_lineup_intelligence(roster)
            matchup_intelligence = build_matchup_intelligence(roster, lineup_intelligence.get("starters"))
            extra_actions = []
            for vacancy in vacancies:
                extra_actions.append(build_action(action_id=f"roster:vacancy:{vacancy}", category="lineup", title=f"Fill {vacancy}", action=f"Fill vacant {vacancy} starter slot", reason="A vacant starter slot has a zero-point baseline until filled.", urgency="CRITICAL", confidence={"label":"HIGH","score":100}, risk_reduction=100, source="roster_analysis", metadata={"slot":vacancy}))
            for index, need in enumerate(needs[:5], 1):
                extra_actions.append(build_action(action_id=f"team-health:{index}", category="waiver", title="Address roster need", action=need, reason=need, urgency="HIGH", confidence={"label":"MEDIUM","score":70}, risk_reduction=50, source="roster_analysis"))
            for index, candidate in enumerate(waivers[:3], 1):
                extra_actions.append(build_action(action_id=f"waiver-watch:{index}:{candidate['player']}", category="waiver", title=f"Review {candidate['player']}", action=f"Review {candidate['player']} at ${candidate['faab']} FAAB", reason=f"Priority score {candidate['priority_score']:.1f}; roster need {candidate['need']}.", urgency="HIGH" if candidate.get("need") else "MEDIUM", confidence={"label":"MEDIUM","score":70}, risk_reduction=min(100,float(candidate.get("need") or 0)*25), source="waiver_watch", metadata={"faab":candidate.get("faab")}))
            incomplete = [p for p in roster if p.get("evidence_gaps")]
            if incomplete:
                extra_actions.append(build_action(action_id="data-integrity:weekly-evidence", category="matchup", title="Resolve weekly evidence", action=f"Resolve weekly evidence for {len(incomplete)} roster player(s)", reason="Schedule, bye, health, or matchup evidence is incomplete.", urgency="CRITICAL", confidence={"label":"LOW","score":0}, evidence_complete=False, blockers=sorted({gap for p in incomplete for gap in p.get("evidence_gaps",[])}), source="weekly_intelligence"))
            for index, player in enumerate(matchup_intelligence.get("favorable_matchups",[])[:3],1):
                extra_actions.append(build_action(action_id=f"matchup:{index}:{player['player']}", category="matchup", title=f"Exploit {player['player']} matchup", action=f"Prioritize {player['player']} against {player.get('opponent') or 'TBD'}", reason=f"Supplied matchup modifier is {player['matchup_modifier']:+.1%}.", urgency="MEDIUM", confidence=player.get("confidence"), expected_points_gain=max(0.0,player["weekly_score"]-player["weekly_baseline"]), evidence_complete=not player.get("evidence_gaps"), blockers=player.get("evidence_gaps") or (), source="matchup_intelligence", metadata={"position":player.get("position"),"matchup_rank":player.get("matchup_rank")}))
            decision_ranking = build_decision_ranking(lineup_intelligence=lineup_intelligence, extra_actions=extra_actions, limit=12)
        finally:
            cur.close(); conn.close()
        return render_template("gm.html", title="Weekly Command Center", context=context, meta=meta, overall=overall, roster_score=score, total=total, vacancies=vacancies, waivers=waivers, waiver_evidence=pool_evidence, roster=roster, lineup_intelligence=lineup_intelligence, decision_ranking=decision_ranking, matchup_intelligence=matchup_intelligence)

    return bp
