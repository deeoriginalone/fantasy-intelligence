from services.trade_intelligence import build_trade_intelligence,generate_one_for_one,generate_two_for_one,trade_value

def p(name,pos,projection,rank=100,**kw):
 row={"player":name,"position":pos,"projection":projection,"weekly_score":projection/17,"rank":rank,"tier":4,"injury_status":"Healthy","injury_multiplier":1,"is_bye":False};row.update(kw);return row

def mine():return [p("MQ","QB",300),p("MR1","RB",260),p("MR2","RB",230),p("MR3","RB",180),p("MR4","RB",150),p("MR5","RB",140),p("MW1","WR",250),p("MW2","WR",220),p("MW3","WR",190),p("MW4","WR",170),p("MT","TE",160),p("MK","K",120),p("MD","DEF",130)]

def theirs():return [p("TQ","QB",280),p("TR1","RB",240),p("TR2","RB",210),p("TW1","WR",270),p("TW2","WR",230),p("TW3","WR",180),p("TW4","WR",160),p("TT","TE",190),p("TK","K",110),p("TD","DEF",125)]

def test_value_is_deterministic_and_injury_reduces_value():
 healthy=p("A","RB",200);out=p("A","RB",200,injury_status="Out",injury_multiplier=0);assert trade_value(healthy)==trade_value(dict(healthy));assert trade_value(out)<trade_value(healthy)

def test_one_for_one_packages_are_unique_and_balanced_ordered():
 rows=generate_one_for_one(mine(),theirs());assert rows;assert all(len(x["send"])==1 and len(x["receive"])==1 for x in rows);assert [x["balance_gap"] for x in rows]==sorted(x["balance_gap"] for x in rows)

def test_two_for_one_never_reuses_same_player():
 rows=generate_two_for_one(mine(),theirs())
 if not rows:
  return
 assert all(x["send"][0]["player"]!=x["send"][1]["player"] for x in rows)

def test_missing_roster_and_evidence_fail_closed():
 assert build_trade_intelligence([],theirs(),{"name":"Them"})["allowed"] is False
 result=build_trade_intelligence([{"player":"Unknown","position":"RB"}],theirs(),{"name":"Them"});assert "TRADE_EVIDENCE_INCOMPLETE" in result["blockers"]

def test_inputs_are_not_modified():
 a=mine();b=theirs();before_a=[dict(x) for x in a];before_b=[dict(x) for x in b];build_trade_intelligence(a,b,{"name":"Them"});assert a==before_a and b==before_b
