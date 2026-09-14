from services.weekly_lineup_intelligence import build_lineup_intelligence,optimize_lineup

def p(name,pos,score,**kw):
 row={"player":name,"position":pos,"weekly_score":score,"weekly_baseline":score,"projection":score*17,"rank":100,"injury_status":"Healthy","injury_multiplier":1.0,"is_bye":False,"opponent":"X","matchup_rank":16,"matchup_modifier":0.0};row.update(kw);return row

def roster():return [p("QA","QB",20),p("QB","QB",18),p("RA","RB",18),p("RB","RB",17),p("RC","RB",16),p("WA","WR",19),p("WB","WR",15),p("WC","WR",14),p("TA","TE",11),p("TB","TE",8),p("KA","K",9),p("DA","DEF",10)]

def test_slots_flex_total_and_bench():
 s,b,total,v=optimize_lineup(roster());assert [x["slot"] for x in s]==["QB","RB1","RB2","WR1","WR2","TE","FLEX","K","DEF"];assert not v;assert next(x for x in s if x["slot"]=="FLEX")["player"]=="RC";assert total==sum(x["weekly_score"] for x in s);assert {x["player"] for x in b}=={"QB","TB","WC"}

def test_bye_and_out_are_benched():
 rows=roster();rows[0]["is_bye"]=True;rows[2].update({"injury_status":"Out","injury_multiplier":0});s,b,_,v=optimize_lineup(rows);assert next(x for x in s if x["slot"]=="QB")["player"]=="QB";assert {"QA","RA"}<={x["player"] for x in b};assert not v

def test_empty_and_incomplete_fail_closed():
 assert build_lineup_intelligence([])["blockers"]==["ROSTER_EMPTY","STARTER_SLOTS_VACANT"];assert build_lineup_intelligence([p("Q","QB",10)])["allowed"] is False

def test_missing_evidence_reported_and_inputs_preserved():
 rows=roster();rows[0]["weekly_score"]=None;rows[0]["weekly_baseline"]=None;before=[dict(x) for x in rows];result=build_lineup_intelligence(rows);assert "WEEKLY_EVIDENCE_INCOMPLETE" in result["blockers"];assert "QA" in result["missing_evidence_players"];assert rows==before

def test_decisions_use_explicit_actions_and_bench_order():
 result=build_lineup_intelligence(roster())
 assert {item["decision"] for item in result["start_sit_decisions"]} <= {"START", "FLEX", "MONITOR"}
 assert next(item for item in result["start_sit_decisions"] if item["slot"]=="FLEX")["decision"] == "FLEX"
 assert [player["bench_order"] for player in result["bench"]] == list(range(1, len(result["bench"])+1))
 assert all(player["decision"] == "SIT" for player in result["bench"])

def test_incomplete_evidence_is_monitor_not_zero():
 rows=roster();rows[0]["weekly_score"]=None;rows[0]["weekly_baseline"]=None
 rows[1].update({"injury_status":"Out","injury_multiplier":0})
 result=build_lineup_intelligence(rows)
 qb=next(item for item in result["starters"] if item["slot"]=="QB")
 assert qb["decision"] == "MONITOR"
 assert result["weekly_total_available"] is False
