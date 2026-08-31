from monte_carlo_survival import curve,enhance,run_risks,seed_for,urgency
def test_curve_monotonic():
 c=curve(40,5);assert c[0]["survival_pct"]==100 and c[-1]["survival_pct"]==40 and all(c[i]["survival_pct"]>=c[i+1]["survival_pct"] for i in range(len(c)-1))
def test_curve_bounds():assert all(0<=x["survival_pct"]<=100 for x in curve(20,8))
def test_seed_deterministic():assert seed_for('d',0,5,500,[])==seed_for('d',0,5,500,[])
def test_urgency():assert urgency(30,'LOW')=='DRAFT NOW' and urgency(80,'LOW')=='SAFE TO WAIT'
def test_run_risk():assert run_risks({"projected_gone":{"RB":3},"position_pressure":{"RB":20},"teams_needing_position":{"RB":2}})["RB"]["level"]=='HIGH'
def test_enhance_preserves_terminal():
 b={"simulations":500,"picks_until_next":3,"players":[{"player":"A","position":"RB","availability_pct":55}]};x=enhance(b,{"next_pick":5},'d',1,[]);assert x["players"][0]["survival_curve"][-1]["survival_pct"]==55 and x["canonical_score_unchanged"]
