from services.matchup_intelligence import build_matchup_intelligence

def p(name,pos,mod,rank=20,score=10,gaps=None,bye=False,opponent="X"):
    return {"player":name,"position":pos,"matchup_modifier":mod,"matchup_rank":rank,"weekly_baseline":9,"weekly_score":score,"fp_allowed":24,"injury_status":"Healthy","is_bye":bye,"opponent":opponent,"evidence_gaps":gaps or []}

def test_favorable_and_difficult():
    r=build_matchup_intelligence([p("Good","WR",.1,28,14),p("Hard","RB",-.1,4,7)])
    assert r["favorable_matchups"][0]["player"]=="Good" and r["difficult_matchups"][0]["player"]=="Hard"

def test_missing_evidence_is_preserved():
    r=build_matchup_intelligence([p("Unknown","QB",0,None,gaps=["SCHEDULE_NOT_LOADED_FOR_WEEK"],opponent=None)])
    assert r["blockers"]==["SCHEDULE_NOT_LOADED_FOR_WEEK"] and r["unavailable_matchups"][0]["classification"]=="UNKNOWN"

def test_starter_filter():
    r=build_matchup_intelligence([p("Starter","WR",.08),p("Bench","WR",-.08)],[{"player":"Starter"}])
    assert r["starter_count"]==1 and not r["difficult_matchups"]

def test_bye_unavailable():
    r=build_matchup_intelligence([p("Bye","TE",.12,bye=True,score=0)])
    assert not r["favorable_matchups"] and r["unavailable_matchups"][0]["classification"]=="BYE"
