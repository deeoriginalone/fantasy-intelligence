from services.team_needs import league_settings_contract, team_needs_contract

def league():
    return {"roster_positions":["QB","RB","RB","WR","WR","TE","FLEX","K","DEF","BN"],"scoring_settings":{"rec":1.0}}

def roster(*positions):
    return [{"player":str(i),"position":p} for i,p in enumerate(positions)]

def test_settings_expose_full_ppr_and_flex_eligibility():
    x=league_settings_contract(league()); assert x["full_ppr"] is True; assert x["starter_slots"]["FLEX"]==1; assert x["flex_eligible_positions"]==["RB","WR","TE"]

def test_all_required_need_keys_exist():
    x=team_needs_contract([],league_settings_contract(league())); assert set(x)=={"QB","RB","WR","TE","FLEX","K","DEF"}

def test_flex_is_slot_not_player_position():
    x=team_needs_contract(roster("RB","RB","RB","WR","WR","TE"),league_settings_contract(league())); assert x["FLEX"]["rostered"] is None; assert x["FLEX"]["eligible_positions"]==["RB","WR","TE"]

def test_surplus_rb_covers_flex_after_base_slots():
    x=team_needs_contract(roster("RB","RB","RB","WR","WR","TE"),league_settings_contract(league())); assert x["FLEX"]["eligible_depth"]==1; assert x["FLEX"]["need"]=="COVERED"

def test_only_base_eligible_players_leave_flex_shortage():
    x=team_needs_contract(roster("RB","RB","WR","WR","TE"),league_settings_contract(league())); assert x["FLEX"]["eligible_depth"]==0; assert x["FLEX"]["shortage"]==1

def test_qb_k_def_do_not_cover_flex():
    x=team_needs_contract(roster("QB","QB","RB","RB","WR","WR","TE","K","DEF","DEF"),league_settings_contract(league())); assert x["FLEX"]["shortage"]==1

def test_dst_normalizes_to_def():
    x=team_needs_contract(roster("DST"),league_settings_contract(league())); assert "DST" not in x; assert x["DEF"]["rostered"]==1

def test_missing_settings_fail_closed():
    x=team_needs_contract([],league_settings_contract({})); assert all(v["state"]=="BLOCKED" for v in x.values()); assert x["FLEX"]["shortage"] is None
