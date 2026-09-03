from sleeper_intelligence import estimate_faab, waiver_candidates

def test_tiers():
    assert estimate_faab(400,250,True,10)["urgency"]=="CRITICAL"
    assert estimate_faab(320,200,False,5)["recommended_bid_pct"]==12
    assert estimate_faab(220,100,False,3)["recommended_bid_pct"]==7
    assert estimate_faab(120,20,False,1)["recommended_bid_pct"]==3
    assert estimate_faab(50,1,False,0)["recommended_bid_pct"]==1

def test_primary_need_premium():
    base=estimate_faab(220,100,False,3);premium=estimate_faab(220,100,True,3)
    assert premium["recommended_bid_pct"]==base["recommended_bid_pct"]+3

def test_ranges_bounded():
    for score in (0,50,120,220,320,450):
        x=estimate_faab(score,0,False,0)
        assert 0<=x["bid_range_low_pct"]<=x["recommended_bid_pct"]<=x["bid_range_high_pct"]<=30

def test_budget_conversion():
    x=estimate_faab(320,100,False,3,remaining_budget=73)
    assert x["recommended_bid"]==9
    assert x["bid_range_low"]<=x["recommended_bid"]<=x["bid_range_high"]

def test_zero_budget():
    x=estimate_faab(400,250,True,10,remaining_budget=0)
    assert (x["recommended_bid"],x["bid_range_low"],x["bid_range_high"])==(0,0,0)

def test_candidate_has_faab_fields():
    row=waiver_candidates([{"player_id":"p1","name":"RB One","position":"RB","count":200}],{"primary_need":"RB","needs":{"RB":2}},{"RB":8},remaining_budget=100)[0]
    assert row["waiver_score"]==340
    assert row["recommended_bid_pct"]==15
    assert row["recommended_bid"]==15
    assert row["urgency"]=="HIGH"

def test_no_budget_keeps_percent_only():
    x=estimate_faab(220,100,False,3)
    assert x["remaining_budget"] is None and x["recommended_bid"] is None

def test_negative_budget_rejected():
    try: estimate_faab(220,100,False,3,remaining_budget=-1)
    except ValueError: pass
    else: raise AssertionError("negative budget accepted")
