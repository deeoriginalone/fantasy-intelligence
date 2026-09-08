from services.trade_target_center import build_trade_target_center, opportunity_score

def pkg(target="Target",offer="Offer",owner=8,partner=4,gap=4,confidence=90,target_weekly=8,offer_weekly=16):
 return {"receive":[{"player":target,"position":"WR","trade_value":200,"projection":272,"weekly_score":target_weekly}],"send":[{"player":offer,"position":"RB","trade_value":195,"projection":204,"weekly_score":offer_weekly}],"owner_gain":owner,"partner_gain":partner,"balance_gap":gap,"verdict":"LEAN ACCEPT","confidence":{"label":"HIGH","score":confidence},"reason":"Verified fit."}
def intel(rows): return {"allowed":True,"blockers":[],"partner":{"name":"Partner"},"owner_profile":{"needs":{"WR":1},"surplus":{"RB":1}},"partner_profile":{"needs":{"RB":1},"surplus":{"WR":1}},"one_for_one":rows,"two_for_one":[]}
def test_score_deterministic_bounded():
 assert opportunity_score(pkg())==opportunity_score(pkg()); assert 0<=opportunity_score(pkg())<=100
def test_ranking():
 r=build_trade_target_center(intel([pkg("A","X",2,1,10,70),pkg("B","Y",12,8,2,100)])); assert r["trade_targets"][0]["player"]=="B"
def test_market_signals_from_supplied_fields():
 r=build_trade_target_center(intel([pkg()])); assert r["buy_low"][0]["player"]=="Target"; assert r["sell_high"][0]["player"]=="Offer"
def test_profiles_and_no_submission():
 r=build_trade_target_center(intel([pkg()])); assert r["owner_needs"]=={"WR":1}; assert r["owner_surplus"]=={"RB":1}; assert "No trade is submitted" in r["methodology"]
def test_blocked_empty_fails_closed():
 r=build_trade_target_center({"allowed":False,"blockers":["PARTNER_ROSTER_EMPTY"],"one_for_one":[],"two_for_one":[]}); assert not r["allowed"] and not r["ranked_opportunities"]
