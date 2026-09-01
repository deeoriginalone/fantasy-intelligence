import pytest
from services.draft_recommendation_service import Candidate, rank_candidates
TARGETS={"QB":1,"RB":4,"WR":5,"TE":2,"K":1,"DEF":1}
def tier(rank): return 1 if (rank or 9999)<=12 else 2
def bonus(strategy,pos,round_num): return 10 if strategy=="RB_HEAVY" and pos=="RB" else 0
def row(rank,name,pos,pid): return (rank,name,pos,"T",100.0,1,float(rank),pid)
def test_requires_id():
    with pytest.raises(ValueError,match="canonical player ID"):
        Candidate.from_row(row(1,"A","RB",None))
def test_ranks_and_preserves_shape():
    result=rank_candidates([row(2,"RB A","RB","p2"),row(1,"WR A","WR","p1")],{"QB":0,"RB":0,"WR":0,"TE":0,"K":0,"DEF":0},"RB_HEAVY",1,14,TARGETS,tier,bonus,2)
    assert result[0].candidate.player_id=="p2"
    assert result[0].as_legacy()["player"][7]=="p2"
def test_excludes_kicker_early():
    result=rank_candidates([row(1,"K A","K","k1"),row(2,"RB A","RB","r1")],{"QB":0,"RB":0,"WR":0,"TE":0,"K":0,"DEF":0},"BALANCED",1,14,TARGETS,tier,bonus,8)
    assert [x.candidate.position for x in result]==["RB"]
