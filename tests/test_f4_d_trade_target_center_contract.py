from pathlib import Path
from jinja2 import Environment,FileSystemLoader
def test_template_contract():
 root=Path(__file__).resolve().parents[1]; env=Environment(loader=FileSystemLoader(root/"templates"),autoescape=True); env.globals["url_for"]=lambda endpoint,**kwargs:"/"
 p={"receive":[{"player":"Target","position":"WR"}],"send":[{"player":"Offer","position":"RB"}],"opportunity_score":88,"owner_gain":5,"partner_gain":4,"balance_gap":1,"verdict":"BALANCED","confidence":{"label":"HIGH","score":100},"reason":"Verified fit."}
 domain={"source":"Controlled source","status":"UNKNOWN","completeness_state":"UNAVAILABLE","recommendation_impact":"BLOCKED","score":0,"timestamp":None,"age_seconds":None,"blocker":"MATCHUP_FRESHNESS_UNKNOWN"}
 diagnostic={"player_id":"owner-1","player_name":"<script>alert(1)</script>","roster_side":"OWNER","domain":"PROJECTION","failed_predicate":"projection freshness < stale","missing_field":"projection_retrieved_at","source":"<img src=x>","retrieved_at":None,"freshness_state":"EXPIRED","completeness_state":"UNAVAILABLE","blocker_code":"PROJECTION_DATA_EXPIRED","recommendation_impact":"BLOCKED"}
 integrity={"recommendation_ready":False,"completeness_score":0,"confidence":{"label":"LOW","score":0},"freshness":{"score":0,"domains":{"roster":domain,"injury":domain,"matchup":domain,"projection":{**domain,"blocker":"PROJECTION_FRESHNESS_UNKNOWN"}}},"player_count":0,"healthy_players":0,"unknown_health_players":0,"missing_matchups":0,"blockers":["ROSTER_FRESHNESS_UNKNOWN"],"diagnostics":[diagnostic]}
 c={"trade_targets":[{"player":"Target","position":"WR","opportunity_score":88,"market_signal":"BUY_LOW_SIGNAL","best_package":p}],"buy_low":[{"player":"Target","position":"WR"}],"sell_high":[],"owner_needs":{"WR":1},"owner_surplus":{"RB":1},"partner_needs":{"RB":1},"ranked_opportunities":[p],"integrity":integrity,"methodology":"No trade is submitted."}
 env.globals["ux_route_evidence"]=lambda *args:{"fields":{}}
 html=env.get_template("trades.html").render(context={"mode":"LIVE"},meta={"team_name":"Mine"},teams=[{"slot":2,"name":"Partner"}],target_slot=2,trade_intelligence={"partner":{"name":"Partner"},"blockers":["ROSTER_FRESHNESS_UNKNOWN"]},trade_target_center=c)
 for x in ("Trade Target Center","Partner Analysis","Team Needs Comparison","Positional Surplus Comparison","Schedule Impact","Bye Impact","Health Impact","Matchup Signal","Trade Risks","Why Recommendations Are Blocked","Player-level blocker details","ROSTER_FRESHNESS_UNKNOWN"): assert x in html
 assert '<details class="trade-diagnostic-details">' in html
 assert '<details class="trade-diagnostic-details" open' not in html
 assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html and "&lt;img src=x&gt;" in html
 assert "<script>alert(1)</script>" not in html and "<img src=x>" not in html
 assert "Trade Recommendation" not in html and "One-for-One Packages" not in html and "Two-for-One Packages" not in html
 assert "/trade/submit" not in html and "/transactions" not in html
def test_route_contract():
 t=Path("owner_operations.py").read_text(encoding="utf-8"); assert "from services.trade_target_center import build_trade_target_center" in t; assert "trade_target_center=build_trade_target_center(trade_intelligence)" in t; assert "trade_target_center=trade_target_center" in t; assert "if oid in owner_ids:continue" in t
