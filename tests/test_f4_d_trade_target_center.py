import pytest
from services.trade_target_center import build_trade_target_center, opportunity_score

def pkg(target="Target",offer="Offer",owner=8,partner=4,gap=4,confidence=90,target_weekly=8,offer_weekly=16):
 return {"receive":[{"player":target,"position":"WR","trade_value":200,"projection":272,"weekly_score":target_weekly}],"send":[{"player":offer,"position":"RB","trade_value":195,"projection":204,"weekly_score":offer_weekly}],"owner_gain":owner,"partner_gain":partner,"balance_gap":gap,"verdict":"LEAN ACCEPT","confidence":{"label":"HIGH","score":confidence},"reason":"Verified fit."}
def intel(rows): return {"allowed":True,"blockers":[],"partner":{"name":"Partner"},"owner_profile":{"counts":{"QB":2,"RB":5,"WR":3,"TE":2,"K":1,"DEF":1},"needs":{"QB":0,"RB":0,"WR":1,"TE":0,"K":0,"DEF":0},"surplus":{"QB":0,"RB":1,"WR":0,"TE":0,"K":0,"DEF":0}},"partner_profile":{"counts":{"QB":2,"RB":3,"WR":5,"TE":2,"K":1,"DEF":1},"needs":{"QB":0,"RB":1,"WR":0,"TE":0,"K":0,"DEF":0},"surplus":{"QB":0,"RB":0,"WR":1,"TE":0,"K":0,"DEF":0}},"one_for_one":rows,"two_for_one":[]}
def test_score_deterministic_bounded():
 assert opportunity_score(pkg())==opportunity_score(pkg()); assert 0<=opportunity_score(pkg())<=100
def test_ranking():
 r=build_trade_target_center(intel([pkg("A","X",2,1,10,70),pkg("B","Y",12,8,2,100)])); assert r["trade_targets"][0]["player"]=="B"; assert r["best_package"]["receive"][0]["player"]=="B"
def test_market_signals_from_supplied_fields():
 r=build_trade_target_center(intel([pkg()])); assert r["buy_low"][0]["player"]=="Target"; assert r["sell_high"][0]["player"]=="Offer"
def test_profiles_and_no_submission():
 r=build_trade_target_center(intel([pkg()])); assert r["owner_needs"]=={"WR":1}; assert r["owner_surplus"]=={"RB":1}; assert "No trade is submitted" in r["methodology"]
def test_blocked_empty_fails_closed():
 r=build_trade_target_center({"allowed":False,"blockers":["PARTNER_ROSTER_EMPTY"],"one_for_one":[],"two_for_one":[]}); assert not r["allowed"] and not r["ranked_opportunities"]
 assert r["package_rejection"] is None

def test_empty_package_reason_uses_roster_fit_evidence_and_monitor_guidance():
 data={"allowed":True,"one_for_one":[],"two_for_one":[],"owner_profile":{"needs":{"WR":2},"surplus":{"RB":1}},"partner_profile":{"needs":{"RB":1},"surplus":{"WR":2}}}
 result=build_trade_target_center(data)
 rejection=result["package_rejection"]
 assert rejection["state"]=="NO_QUALIFYING_PACKAGE"
 assert rejection["evidence"]==["Owner needs WR; partner has WR surplus.","Partner needs RB; owner has RB surplus."]
 assert "no qualifying package" in rejection["reason"]
 assert rejection["takeaway"]=="Monitor this team. Re-evaluate if the RB, WR roster balance changes."

def test_empty_package_reason_does_not_claim_alignment_or_show_for_packages():
 no_fit=build_trade_target_center({"allowed":True,"one_for_one":[],"two_for_one":[],"owner_profile":{"needs":{"WR":1},"surplus":{}},"partner_profile":{"needs":{"QB":1},"surplus":{}}})
 assert no_fit["package_rejection"]["evidence"]==["Current roster needs and surpluses do not overlap by position."]
 assert no_fit["package_rejection"]["reason"]=="No qualifying package is available for the current rosters."
 assert no_fit["package_rejection"]["takeaway"]=="Monitor this team. Re-evaluate after roster changes."
 qualifying=build_trade_target_center(intel([pkg()]))
 assert qualifying["package_rejection"] is None

def test_identical_opportunity_inputs_have_stable_name_tie_breaking():
 rows=[pkg("Zulu","Offer",8,4,4,90),pkg("Alpha","Offer",8,4,4,90)]
 first=build_trade_target_center(intel(rows))["ranked_opportunities"]
 second=build_trade_target_center(intel(rows))["ranked_opportunities"]
 assert [row["receive"][0]["player"] for row in first] == ["Alpha","Zulu"]
 assert first == second

def test_valid_package_publishes_position_change_and_preserves_flex_depth():
 result=build_trade_target_center(intel([pkg()]))
 assert not result["rejected_packages"], result["rejected_packages"][0]["reasons"]
 package=result["one_for_one"][0]
 assert package["roster_impact"]["position_change"]=="RB → WR"
 assert package["roster_impact"]["owner"]["flex_before"]==package["roster_impact"]["owner"]["flex_after"]
 assert package["roster_impact"]["helps"]==["Addresses WR deficit."]
 assert result["package_counts"]=={"generated":{"ONE_FOR_ONE":1,"TWO_FOR_ONE":0},"published":{"ONE_FOR_ONE":1,"TWO_FOR_ONE":0},"rejected":0}
 assert result["best_package"] is package
 assert package["roster_impact"]["need_improvement"]==1

def test_package_gate_rejects_only_te_and_minimum_rb_holes():
 only_te=intel([pkg()]);only_te["owner_profile"]["counts"]["TE"]=2
 only_te["owner_profile"]["needs"]["TE"]=0
 only_te["one_for_one"][0]["send"][0]["position"]="TE"
 result=build_trade_target_center(only_te)
 assert not result["one_for_one"]
 assert "Owner: Would leave TE below minimum coverage." in result["rejected_packages"][0]["reasons"]
 assert result["closest_trade_path"]["current_obstacle"]=="Owner: Would leave TE below minimum coverage."
 assert "owner TE coverage changes" in result["closest_trade_path"]["monitor_if"]
 minimum_rb=intel([pkg()]);minimum_rb["owner_profile"]["counts"]["RB"]=4
 minimum_rb["owner_profile"]["surplus"]["RB"]=0
 result=build_trade_target_center(minimum_rb)
 assert not result["one_for_one"]
 assert "Owner: Would leave RB below minimum coverage." in result["rejected_packages"][0]["reasons"]

def test_coverage_safe_package_is_rejected_when_it_improves_no_verified_need():
 neutral=intel([pkg()])
 neutral["one_for_one"][0]["receive"][0]["position"]="WR"
 neutral["one_for_one"][0]["send"][0]["position"]="WR"
 result=build_trade_target_center(neutral)
 assert not result["ranked_opportunities"]
 assert result["rejected_packages"][0]["reasons"]==["Does not improve any verified team need."]
 assert result["package_counts"]["rejected"]==1
 assert result["closest_trade_path"]["summary"]=="Position change WR → WR leaves verified needs unchanged."

def test_package_gate_also_protects_partner_minimum_coverage():
 data=intel([pkg()])
 data["partner_profile"]["counts"]["WR"]=4
 data["partner_profile"]["surplus"]["WR"]=0
 result=build_trade_target_center(data)
 assert not result["one_for_one"]
 assert "Partner: Would leave WR below minimum coverage." in result["rejected_packages"][0]["reasons"]

def test_package_gate_fails_closed_when_roster_coverage_is_missing():
 data=intel([pkg()])
 data["owner_profile"].pop("counts")
 result=build_trade_target_center(data)
 assert not result["ranked_opportunities"]
 assert "Owner: Required roster coverage is unavailable." in result["rejected_packages"][0]["reasons"]

def test_package_gate_rejects_worsened_deficit_and_reduced_flex_depth():
 deficit=intel([pkg(target_weekly=8,offer_weekly=16)])
 deficit["owner_profile"]["counts"]["WR"]=3
 deficit["owner_profile"]["needs"]["WR"]=1
 deficit["one_for_one"][0]["send"][0]["position"]="WR"
 deficit["one_for_one"][0]["receive"][0]["position"]="TE"
 result=build_trade_target_center(deficit)
 assert not result["one_for_one"]
 assert "Owner: Would increase WR deficit." in result["rejected_packages"][0]["reasons"]

 flex=intel([pkg()]);flex["one_for_one"][0]["receive"][0]["position"]="K"
 flex["one_for_one"][0]["send"][0]["position"]="RB"
 result=build_trade_target_center(flex)
 assert not result["one_for_one"]
 assert "Owner: Would reduce FLEX depth." in result["rejected_packages"][0]["reasons"]

@pytest.mark.parametrize("position",["QB","RB","WR","TE","K","DEF"])
def test_package_gate_never_drops_required_position_below_minimum(position):
 data=intel([pkg()])
 minimum={"QB":2,"RB":4,"WR":4,"TE":2,"K":1,"DEF":1}
 data["owner_profile"]["counts"][position]=minimum[position]
 data["owner_profile"]["needs"][position]=0
 data["owner_profile"]["surplus"][position]=0
 target_position="WR" if position=="TE" else "TE"
 data["one_for_one"][0]["send"][0]["position"]=position
 data["one_for_one"][0]["receive"][0]["position"]=target_position
 data["partner_profile"]["counts"]["TE"]=3
 data["partner_profile"]["surplus"]["TE"]=1
 result=build_trade_target_center(data)
 assert not result["ranked_opportunities"]
 assert f"Owner: Would leave {position} below minimum coverage." in result["rejected_packages"][0]["reasons"]

def test_unsafe_package_is_excluded_without_changing_valid_package_order():
 unsafe=pkg("Dangerous","RB")
 safe=pkg("Safe","RB")
 unsafe["send"][0]["position"]="TE"
 result=build_trade_target_center(intel([unsafe,safe]))
 assert [row["receive"][0]["player"] for row in result["one_for_one"]]==["Safe"]
 assert result["package_counts"]["rejected"]==1
 assert result["package_counts"]["published"]["ONE_FOR_ONE"]==1
 assert result["package_counts"]["generated"]["ONE_FOR_ONE"]==2
