from services.team_needs import build_team_needs_summary, league_settings_contract, team_needs_contract


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
