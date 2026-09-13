from pathlib import Path
from jinja2 import Environment,FileSystemLoader

def test_trade_template_renders_and_has_no_submission_endpoint():
 root=Path(__file__).resolve().parents[1];env=Environment(loader=FileSystemLoader(root/"templates"));env.globals["url_for"]=lambda endpoint,**kwargs:"/"
 package={"receive":[{"player":"Target","position":"WR","trade_value":200}],"send":[{"player":"Offer","position":"RB","trade_value":195},{"player":"Extra","position":"WR","trade_value":20}],"owner_gain":5,"partner_gain":4,"balance_gap":1,"verdict":"BALANCED","confidence":{"label":"HIGH","score":100},"reason":"Verified roster fit."}
 intel={"partner":{"name":"Partner"},"blockers":[],"missing_evidence_players":[],"owner_profile":{"needs":{"QB":0},"surplus":{}},"partner_profile":{"needs":{"RB":1},"surplus":{}},"one_for_one":[{**package,"send":package["send"][:1]}],"two_for_one":[package],"methodology":"No trade is submitted."}
 env.globals["ux_route_evidence"]=lambda *args:{"fields":{}}
 html=env.get_template("trades.html").render(context={"mode":"LIVE"},meta={"team_name":"Mine"},teams=[{"slot":2,"name":"Partner"}],target_slot=2,trade_intelligence=intel)
 for text in ("Trade Intelligence Agent","One-for-One Packages","Two-for-One Consolidation Packages","Target","Offer","Partner","HIGH 100%"):assert text in html
 assert "/trade/submit" not in html and "/transactions" not in html


def test_trade_template_keeps_partner_control_and_action_evidence_visible():
 text=(Path(__file__).resolve().parents[1]/"templates/trades.html").read_text(encoding="utf-8")
 for marker in ("<select name=\"team\">","<button type=\"submit\">Analyze</button>","Trade Recommendation","ROSTER WEAKNESS ADDRESSED","LINEUP IMPACT","DEPTH IMPACT","RISK IMPACT","RECOMMENDATION CONFIDENCE","trade-intelligence"):
  assert marker in text


def test_trade_template_separates_package_types_and_collapses_metric_definitions():
 text=(Path(__file__).resolve().parents[1]/"templates/trades.html").read_text(encoding="utf-8")
 for marker in ("One-for-One Packages", "Two-for-One Packages", "package.type_rank", "package.explanation.target_fit", "package.explanation.partner_fit", "feasibility_state", "Why These Packages Rank Here", "Trade Metric Definitions", "trade-metrics"):
  assert marker in text
