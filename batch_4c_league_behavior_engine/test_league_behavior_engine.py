from league_behavior_engine import build_behavior,classify_room,detect_runs,owner_tendencies,room_profile

def pick(no,pos,roster=1,round_num=1):return {"pick_no":no,"round":round_num,"roster_id":roster,"metadata":{"position":pos,"first_name":"P","last_name":str(no)}}
def test_empty_is_insufficient():assert room_profile([])["room_type"]=="INSUFFICIENT_DATA"
def test_rb_heavy():assert classify_room({"RB":5,"WR":3,"QB":1,"TE":1},10)=="RB_HEAVY"
def test_run_detection():
 r=detect_runs([pick(1,"RB"),pick(2,"RB"),pick(3,"WR"),pick(4,"WR"),pick(5,"WR")]);assert r[-1]["run_length"]==3 and r[-1]["active"]
def test_owner_low_sample_not_claimed():
 h=[{"owner_id":"o","owner_name":"X","draft_slot":1,"position":"RB","round":1}];assert owner_tendencies(h)[0]["preferred_strategy"]=="INSUFFICIENT_DATA"
def test_build_preserves_score():
 x=build_behavior([],[],[],{},{});assert x["canonical_score_unchanged"] and not x["data_sufficient"]
