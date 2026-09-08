from pathlib import Path
from jinja2 import Environment,FileSystemLoader

def test_trade_template_renders_and_has_no_submission_endpoint():
 root=Path(__file__).resolve().parents[1];env=Environment(loader=FileSystemLoader(root/"templates"));env.globals["url_for"]=lambda endpoint,**kwargs:"/"
 package={"receive":[{"player":"Target","position":"WR","trade_value":200}],"send":[{"player":"Offer","position":"RB","trade_value":195},{"player":"Extra","position":"WR","trade_value":20}],"owner_gain":5,"partner_gain":4,"balance_gap":1,"verdict":"BALANCED","confidence":{"label":"HIGH","score":100},"reason":"Verified roster fit."}
 intel={"partner":{"name":"Partner"},"blockers":[],"missing_evidence_players":[],"owner_profile":{"needs":{"QB":0},"surplus":{}},"partner_profile":{"needs":{"RB":1},"surplus":{}},"one_for_one":[{**package,"send":package["send"][:1]}],"two_for_one":[package],"methodology":"No trade is submitted."}
 html=env.get_template("trades.html").render(context={"mode":"LIVE"},meta={"team_name":"Mine"},teams=[{"slot":2,"name":"Partner"}],target_slot=2,trade_intelligence=intel)
 for text in ("Trade Intelligence Agent","One-for-One Packages","Two-for-One Consolidation Packages","Target","Offer","Partner","HIGH 100%","BALANCED"):assert text in html
 assert "/trade/submit" not in html and "/transactions" not in html
