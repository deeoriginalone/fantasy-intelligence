from sleeper_intelligence import available_trending, waiver_candidates

def my_team():
    return {"primary_need":"RB","needs":{"QB":0,"RB":2,"WR":0,"TE":0}}

def candidates():
    return [
        {"player_id":"p1","name":"Trending RB","position":"RB","team":"MIN","count":200},
        {"player_id":"p2","name":"Trending WR","position":"WR","team":"SEA","count":300},
        {"player_id":"p3","name":"Trending QB","position":"QB","team":"LV","count":50},
    ]

def test_owned_players_are_filtered():
    trends=[{"player_id":"p1","count":100},{"player_id":"p2","count":80}]
    rosters=[{"players":["p1"]}]
    players={"p1":{"full_name":"Owned","position":"RB"},"p2":{"full_name":"Available","position":"WR"}}
    assert [x["player_id"] for x in available_trending(trends,rosters,players)] == ["p2"]

def test_primary_need_bonus_can_change_rank():
    assert waiver_candidates(candidates(),my_team(),{"QB":0,"RB":8,"WR":2,"TE":1})[0]["player_id"] == "p1"

def test_score_is_explainable():
    row=waiver_candidates(candidates(),my_team(),{"QB":0,"RB":8,"WR":2,"TE":1})[0]
    assert row["waiver_score"] == (
        row["trend_count"]
        + row["need_score"] * 25
        + row["pressure_score"] * 5
        + row["primary_need_bonus"]
    )
    assert row["reason"]

def test_non_core_positions_are_ignored():
    rows=waiver_candidates(candidates()+[{"player_id":"k","name":"K","position":"K","count":999}],my_team(),{})
    assert "k" not in {x["player_id"] for x in rows}

def test_limit_is_enforced():
    assert len(waiver_candidates(candidates(),my_team(),{},limit=2)) == 2

def test_empty_inputs_are_safe():
    assert waiver_candidates([],None,{}) == []

def test_reason_mentions_primary_need():
    row=waiver_candidates(candidates(),my_team(),{"RB":8})[0]
    assert "primary roster need" in row["reason"]

def test_zero_trend_candidate_is_deterministic():
    team={"primary_need":"TE","needs":{"TE":1}}
    row=waiver_candidates([{"player_id":"x","name":"X","position":"TE","count":0}],team,{"TE":3})[0]
    assert row["waiver_score"] == 90
    assert row["primary_need_bonus"] == 50
    assert row["primary_need_match"] is True
