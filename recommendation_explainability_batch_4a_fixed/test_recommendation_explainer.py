from recommendation_explainer import build_explanation
def c(n,s,t=10):return {"player":(1,n,"RB"),"draft_score":s,"weighted_components":{"talent":t,"need":5,"scarcity":2,"tier":1,"strategy":0,"league":0}}
def test_empty():assert not build_explanation([])["available"]
def test_deterministic():assert build_explanation([c("A",20),c("B",17)])==build_explanation([c("A",20),c("B",17)])
def test_factor():assert build_explanation([c("A",20,11),c("B",17)])["factors"][0]["value"]==11
def test_gap():assert build_explanation([c("A",20),c("B",17)])["alternatives"][0]["score_gap"]==3
def test_bounds():assert 0<=build_explanation([c("A",40),c("B",1)])["confidence"]<=100
def test_risk():assert build_explanation([c("A",20),c("B",17)],{"rows":[{"name":"A","survival_pct":80}]})["risk"]=="LOW"
