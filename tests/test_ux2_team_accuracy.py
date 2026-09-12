from services.ux2_team_accuracy import build_team_accuracy_contract

POSITIONS = ("QB", "RB", "WR", "TE", "FLEX", "K", "DEF")
def settings(full_ppr=True): return {"state":"AVAILABLE","source":"Sleeper API","blocker":None,"starter_slots":{"QB":1,"RB":2,"WR":2,"TE":1,"FLEX":1,"K":1,"DEF":1},"flex_eligible_positions":["RB","WR","TE"],"full_ppr":full_ppr}
def needs(): return {key:{"state":"AVAILABLE","required_slots":1,"rostered":1,"shortage":0,"need":"COVERED","blocker":None} for key in POSITIONS}
def health(): return {"state":"AVAILABLE","source":"Sleeper","freshness_state":"FRESH","blocker":None}
def starter(**changes):
    row={"player":"A","position":"WR","opponent":"SF","matchup_rank":12,"matchup_modifier":0.05,"evidence_gaps":[],"is_bye":False}; row.update(changes); return row

def test_complete_evidence_is_trusted():
    result=build_team_accuracy_contract([], [starter()], settings(), needs(), health())
    assert result["trusted"] is True
    assert result["scoring"]["format"] == "Full PPR"
    assert set(result["team_needs"]["positions"]) == set(POSITIONS)

def test_non_full_ppr_blocks_full_ppr_claim():
    result=build_team_accuracy_contract([], [starter()], settings(False), needs(), health())
    assert result["trusted"] is False
    assert "FULL_PPR_SCORING_NOT_VERIFIED" in result["blockers"]

def test_missing_matchup_is_unavailable_not_neutral():
    result=build_team_accuracy_contract([], [starter(opponent=None,matchup_rank=None,matchup_modifier=None)], settings(), needs(), health())
    assert result["matchups"]["rows"][0]["state"] == "UNAVAILABLE"
    assert "MATCHUP_RANK_MISSING" in result["matchups"]["rows"][0]["blockers"]

def test_blocked_health_reduces_trust():
    blocked={"state":"BLOCKED","source":"Sleeper","freshness_state":"BLOCKED","blocker":"HEALTH_REFRESH_FAILED"}
    result=build_team_accuracy_contract([], [starter()], settings(), needs(), blocked)
    assert result["trusted"] is False
    assert "HEALTH_REFRESH_FAILED" in result["blockers"]
