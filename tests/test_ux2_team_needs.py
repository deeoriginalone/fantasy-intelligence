from services.team_needs import build_team_needs_summary, league_settings_contract, team_needs_contract
from owner_operations import apply_waiver_ranking, build_candidate_faab_guidance, build_waiver_decision_surface, build_waiver_universe_comparison


def league():
    return {"roster_positions":["QB","RB","RB","WR","WR","TE","FLEX","K","DEF","BN"],"scoring_settings":{"rec":1.0}}


def roster(*positions):
    return [{"player":str(i),"position":position} for i,position in enumerate(positions)]


def contract(*positions):
    return team_needs_contract(roster(*positions), league_settings_contract(league()))


def test_settings_expose_full_ppr_and_flex_eligibility():
    result=league_settings_contract(league())
    assert result["full_ppr"] is True
    assert result["starter_slots"]["FLEX"] == 1
    assert result["flex_eligible_positions"] == ["RB","WR","TE"]


def test_all_required_need_keys_exist():
    assert set(contract()) == {"QB","RB","WR","TE","FLEX","K","DEF"}


def test_covered_starters_can_still_need_rb_depth():
    result=contract("QB","RB","RB","RB","WR","WR","WR","TE","K","DEF")
    rb=result["RB"]
    assert rb["starter_coverage"] == "COVERED"
    assert rb["depth_status"] == "BELOW_TARGET"
    assert rb["strategic_need"] == "ADD_DEPTH"
    assert any(line.startswith("Add RB depth") for line in build_team_needs_summary(result))


def test_covered_te_starter_can_still_need_depth():
    result=contract("QB","RB","RB","RB","RB","WR","WR","WR","WR","TE","K","DEF")
    te=result["TE"]
    assert te["starter_coverage"] == "COVERED"
    assert te["depth_status"] == "BELOW_TARGET"
    assert te["strategic_need"] == "ADD_DEPTH"


def test_starter_shortage_takes_precedence_over_depth():
    result=contract("QB","RB","WR","WR","TE","K","DEF")
    assert result["RB"]["strategic_need"] == "ADD_STARTER"
    assert any(item.startswith("Add a RB starter") for item in build_team_needs_summary(result))


def test_summary_cannot_add_position_when_detail_says_no_action():
    result=contract("QB","QB","RB","RB","RB","RB","WR","WR","WR","WR","TE","TE","K","DEF")
    summary=build_team_needs_summary(result)
    for position,item in result.items():
        if item["strategic_need"] == "NO_ACTION":
            assert not any(line.startswith(f"Add {position}") or line.startswith(f"Add a {position}") for line in summary)


def test_flex_uses_supported_eligible_positions_after_base_slots():
    result=contract("RB","RB","RB","WR","WR","TE")
    assert result["FLEX"]["rostered"] is None
    assert result["FLEX"]["eligible_positions"] == ["RB","WR","TE"]
    assert result["FLEX"]["eligible_depth"] == 1
    assert result["FLEX"]["starter_coverage"] == "COVERED"


def test_dst_normalizes_to_def():
    assert contract("DST")["DEF"]["rostered_or_eligible"] == 1


def test_missing_settings_fail_closed():
    result=team_needs_contract([],league_settings_contract({}))
    assert all(item["state"] == "BLOCKED" for item in result.values())
    assert all(item["starter_coverage"] == "UNAVAILABLE" for item in result.values())
    assert all(item["strategic_need"] == "UNAVAILABLE" for item in result.values())
    assert all("analysis unavailable" in line for line in build_team_needs_summary(result))


def test_each_supported_result_has_a_driver():
    assert all(item["drivers"] for item in contract("QB","RB","RB","WR","WR","TE","K","DEF").values())


def test_shared_need_result_exposes_all_requested_fields_for_all_positions():
    result = contract("QB", "RB", "WR", "TE", "K", "DEF")
    assert set(result) == {"QB", "RB", "WR", "TE", "FLEX", "K", "DEF"}
    for item in result.values():
        assert {"available", "action", "strategic_need", "starter_coverage", "depth_current", "depth_target", "severity", "reasons", "blockers", "source", "freshness"} <= set(item)


def test_position_level_league_demand_is_not_player_pressure_or_faab_input():
    candidate = {"player": "RB", "position": "RB", "projection": 120, "projection_retrieved_at": "2026-09-30T00:00:00Z"}
    ranked = apply_waiver_ranking(build_waiver_universe_comparison([candidate], contract("QB")))
    assert "league_demand" in ranked[0]
    assert "player_bid_pressure" not in ranked[0]
    guidance = build_candidate_faab_guidance({"health": {"state": "USABLE", "risk_penalty": 0}, "roster_fit": {"state": "STRONG"}, "quality_score": 8, "team_need": {"strategic_need": "ADD_STARTER"}, "expected_role": {"state": "ESTABLISHED"}, "opportunity_duration": {"state": "ESTABLISHED"}}, {"competition_available": True, "demand_level": "HIGH"}, 100)
    assert guidance["competition_adjustment"] == 0


def test_comparison_basis_is_preliminary_or_exact_alphabetical_fallback():
    preliminary = build_waiver_decision_surface([
        {"player": "Zed", "position": "RB", "player_id": "z", "projection": 120, "projection_retrieved_at": "2026-09-30T00:00:00Z"},
    ], {"allowed": True, "blockers": [], "ownership": {"freshness_state": "FRESH", "completeness_state": "COMPLETE"}, "eligibility": {"freshness_state": "FRESH", "completeness_state": "COMPLETE"}}, position="RB")
    evidence = {"allowed": True, "blockers": [], "ownership": {"freshness_state": "FRESH", "completeness_state": "COMPLETE"}, "eligibility": {"freshness_state": "FRESH", "completeness_state": "COMPLETE"}}
    fallback = build_waiver_decision_surface([{"player": "Zed", "position": "RB", "player_id": "z"}], evidence, position="RB")
    assert preliminary["comparison_state"] == "PRELIMINARY"
    assert fallback["comparison_basis"] == "Alphabetical display, not recommendation order"
    assert preliminary["authoritative_rank"] is False
    assert preliminary["authoritative_faab"] is False
