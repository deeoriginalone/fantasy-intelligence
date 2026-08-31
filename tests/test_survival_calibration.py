from survival_calibration import availability_confidence,build_comparison,severity
def test_thresholds():assert severity(9.99)=="LOW" and severity(10)=="MEDIUM" and severity(20)=="HIGH"
def test_confidence():assert availability_confidence("HIGH")=="REDUCED"
def test_missing():assert not build_comparison({}, {}, {})["available"]
def test_compare():
 e={"available":True,"player":"A","position":"RB","draft_score":10,"confidence":60};m={"run_id":1,"players":[{"player":"A","availability_pct":91.8}]};s={"rows":[{"name":"A","survival_pct":56.1}]};x=build_comparison(e,m,s);assert x["probability_difference"]==35.7 and x["severity"]=="HIGH"
def test_canonical():
 e={"available":True,"player":"A"};m={"players":[{"player":"A","availability_pct":50}]};s={"rows":[{"name":"A","survival_pct":50}]};assert build_comparison(e,m,s)["canonical_score_unchanged"]
