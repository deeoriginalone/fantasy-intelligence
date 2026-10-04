from pathlib import Path
from jinja2 import Environment,FileSystemLoader
from services.trade_target_center import build_trade_target_center

def test_trade_template_renders_and_has_no_submission_endpoint():
 root=Path(__file__).resolve().parents[1];env=Environment(loader=FileSystemLoader(root/"templates"));env.globals["url_for"]=lambda endpoint,**kwargs:"/"
 package={"receive":[{"player":"Target","position":"WR","trade_value":200}],"send":[{"player":"Offer","position":"RB","trade_value":195},{"player":"Extra","position":"WR","trade_value":20}],"owner_gain":5,"partner_gain":4,"balance_gap":1,"verdict":"BALANCED","confidence":{"label":"HIGH","score":100},"reason":"Verified roster fit."}
 intel={"allowed":True,"partner":{"name":"Partner"},"blockers":[],"missing_evidence_players":[],"owner_profile":{"counts":{"QB":2,"RB":5,"WR":3,"TE":2,"K":1,"DEF":1},"needs":{"QB":0,"RB":0,"WR":1,"TE":0,"K":0,"DEF":0},"surplus":{"QB":0,"RB":1,"WR":0,"TE":0,"K":0,"DEF":0}},"partner_profile":{"counts":{"QB":2,"RB":3,"WR":5,"TE":2,"K":1,"DEF":1},"needs":{"QB":0,"RB":1,"WR":0,"TE":0,"K":0,"DEF":0},"surplus":{"QB":0,"RB":0,"WR":1,"TE":0,"K":0,"DEF":0}},"one_for_one":[{**package,"send":package["send"][:1]}],"two_for_one":[{**package,"receive":[{"player":"Target TE","position":"TE"}]}],"methodology":"No trade is submitted."}
 center=build_trade_target_center(intel)
 assert center["package_counts"]=={"generated":{"ONE_FOR_ONE":1,"TWO_FOR_ONE":1},"published":{"ONE_FOR_ONE":1,"TWO_FOR_ONE":0},"rejected":1}
 env.globals["ux_route_evidence"]=lambda *args:{"fields":{}}
 html=env.get_template("trades.html").render(context={"mode":"LIVE"},meta={"team_name":"Mine"},teams=[{"slot":2,"name":"Partner"}],target_slot=2,trade_intelligence=intel,trade_target_center=center)
 for text in ("Trade Intelligence Agent","One-for-One","Two-for-One","Target","Offer","Partner","Diagnostics","Evidence disclosure","RECEIVE","GIVE","POSITION CHANGE","PACKAGE REJECTED","Would increase WR deficit."):assert text in html
 assert "/trade/submit" not in html and "/transactions" not in html


def test_trade_template_keeps_partner_control_and_action_evidence_visible():
 root=Path(__file__).resolve().parents[1]/"templates";text=(root/"trades.html").read_text(encoding="utf-8")+(root/"_trade_manager_view.html").read_text(encoding="utf-8")
 for marker in ("<select name=\"team\">","<button type=\"submit\">Analyze</button>","TRADE RECOMMENDATION","WHY THIS HELPS / HURTS","Position impact","Depth trade-off","Risk introduced","trade-intelligence"):
  assert marker in text


def test_trade_template_separates_package_types_and_collapses_metric_definitions():
 root=Path(__file__).resolve().parents[1]/"templates";text=(root/"trades.html").read_text(encoding="utf-8")+(root/"_trade_manager_view.html").read_text(encoding="utf-8")
 for marker in ("One-for-One", "Two-for-One", "package.explanation", "target_fit", "partner_fit", "Trade Metric Definitions", "trade-metrics", "Recommended packages"):
  assert marker in text

def test_preliminary_trade_recommendation_discloses_inputs_and_renders_existing_packages():
 root=Path(__file__).resolve().parents[1];env=Environment(loader=FileSystemLoader(root/"templates"));env.globals["url_for"]=lambda endpoint,**kwargs:"/"
 env.globals["ux_route_evidence"]=lambda *args:{"fields":{}}
 preliminary={"state":"PRELIMINARY","benefits":{"owner_needs_addressable_by_partner_surplus":["WR"],"partner_needs_addressable_by_owner_surplus":["RB"],"roster_fit_basis_available":True},"evidence_domains":{"schedule":"PRELIMINARY","bye":"PRELIMINARY","matchup_signal":"PRELIMINARY","projection_source":"UNVERIFIED"},"risks":["SCHEDULE_FRESHNESS_THRESHOLD_UNVERIFIED","PROJECTION_PROVIDER_AUTHORITY_UNVERIFIED"]}
 package={"receive":[{"player":"Partner WR","position":"WR"}],"send":[{"player":"Owner RB","position":"RB"}],"owner_gain":8,"confidence":{"label":"HIGH","score":100},"roster_impact":{"position_change":"RB → WR","helps":["Addresses WR deficit."],"hurts":[],"need_improvement":1,"owner":{"before":{"QB":2,"RB":5,"WR":1,"TE":2,"K":1,"DEF":1},"after":{"QB":2,"RB":4,"WR":2,"TE":2,"K":1,"DEF":1},"minimum":{"QB":2,"RB":4,"WR":4,"TE":2,"K":1,"DEF":1},"deficits_before":{"QB":0,"RB":0,"WR":3,"TE":0,"K":0,"DEF":0},"deficits_after":{"QB":0,"RB":0,"WR":2,"TE":0,"K":0,"DEF":0},"flex_before":6,"flex_after":6,"starter_vacancies_before":{"QB":0,"RB":0,"WR":0,"TE":0,"K":0,"DEF":0,"FLEX":0},"starter_vacancies_after":{"QB":0,"RB":0,"WR":0,"TE":0,"K":0,"DEF":0,"FLEX":0}},"partner":{"before":{"QB":2,"RB":1,"WR":5,"TE":2,"K":1,"DEF":1},"after":{"QB":2,"RB":2,"WR":4,"TE":2,"K":1,"DEF":1},"minimum":{"QB":2,"RB":4,"WR":4,"TE":2,"K":1,"DEF":1},"deficits_before":{"QB":0,"RB":3,"WR":0,"TE":0,"K":0,"DEF":0},"deficits_after":{"QB":0,"RB":2,"WR":0,"TE":0,"K":0,"DEF":0},"flex_before":12,"flex_after":12,"starter_vacancies_before":{"QB":0,"RB":0,"WR":0,"TE":0,"K":0,"DEF":0,"FLEX":0},"starter_vacancies_after":{"QB":0,"RB":0,"WR":0,"TE":0,"K":0,"DEF":0,"FLEX":0}},"new_risk_count":0},"explanation":{"target_fit":"WR addresses a verified roster deficit.","assets_given_up":"Owner RB","risk_effect":"Bye and matchup evidence remain preliminary."}}
 intel={"allowed":True,"partner":{"name":"Partner"},"blockers":preliminary["risks"],"preliminary_analysis":preliminary,"owner_profile":{"counts":{"RB":5,"WR":1},"needs":{"WR":3},"surplus":{"RB":1}},"partner_profile":{"counts":{"RB":1,"WR":5},"needs":{"RB":3},"surplus":{"WR":1}},"informational_rosters":{"owner":[],"partner":[]}}
 domain={"source":"Controlled source","status":"UNKNOWN","completeness_state":"UNAVAILABLE","recommendation_impact":"BLOCKED","score":0,"timestamp":None,"age_seconds":None,"blocker":"SCHEDULE_FRESHNESS_THRESHOLD_UNVERIFIED"}
 integrity={"recommendation_ready":False,"completeness_score":0,"confidence":{"label":"LOW","score":50},"freshness":{"score":0,"domains":{"roster":domain,"injury":domain,"matchup":domain,"projection":domain}},"player_count":2,"healthy_players":0,"unknown_health_players":0,"missing_matchups":0,"blockers":preliminary["risks"],"diagnostics":[]}
 center={"allowed":True,"publication_state":"PRELIMINARY","ranked_opportunities":[package],"best_package":package,"one_for_one":[package],"two_for_one":[],"owner_needs":{"WR":3},"owner_surplus":{"RB":1},"integrity":integrity}
 html=env.get_template("trades.html").render(context={"mode":"LIVE"},meta={"team_name":"Mine"},teams=[{"slot":2,"name":"Partner"}],target_slot=2,trade_intelligence=intel,trade_target_center=center)
 for marker in ("PRELIMINARY TRADE RECOMMENDATION","<dt>Schedule</dt><dd>PRELIMINARY","<dt>Bye</dt><dd>PRELIMINARY","<dt>Matchup</dt><dd>PRELIMINARY","<dt>Projection</dt><dd>UNVERIFIED","Why this helps my team","WHY THIS TRADE EXISTS","Before:","After:","Need improved","WHY THIS HELPS / HURTS","Surplus used:","Position impact","One-for-One","Partner WR","<details class=\"trade-diagnostics\">"):
  assert marker in html
 for forbidden in ("AUTHORITATIVE","HIGH CONFIDENCE","CERTIFIED","GUARANTEED","TRADE SCORE","RECOMMENDED ACTION","PROBABILITY","ACCEPTANCE LIKELIHOOD","NEGOTIATION PREDICTION","TRADE FOR","TRADE AWAY"):
  assert forbidden not in html
 assert "WHY NO TRADE EXISTS" not in html
 diagnostics=html.index('<details class="trade-diagnostics">')
 assert html.index("PRELIMINARY TRADE RECOMMENDATION") < diagnostics
 assert html.index("Recommended packages") < diagnostics
 assert html.index("Evidence disclosure") < diagnostics
 assert html.index("SCHEDULE_FRESHNESS_THRESHOLD_UNVERIFIED") > diagnostics
 assert html.index("PROJECTION_PROVIDER_AUTHORITY_UNVERIFIED") > diagnostics

def test_no_package_recommendation_explains_verified_fit_and_monitor_takeaway():
 root=Path(__file__).resolve().parents[1];env=Environment(loader=FileSystemLoader(root/"templates"));env.globals["url_for"]=lambda endpoint,**kwargs:"/";env.globals["ux_route_evidence"]=lambda *args:{"fields":{}}
 intel={"allowed":True,"publication_state":"READY","partner":{"name":"Partner"},"owner_profile":{"needs":{"WR":2},"surplus":{"RB":1}},"partner_profile":{"needs":{"RB":1},"surplus":{"WR":2}},"one_for_one":[],"two_for_one":[],"integrity":None}
 center=build_trade_target_center(intel)
 html=env.get_template("trades.html").render(context={"mode":"LIVE"},meta={"team_name":"Mine"},teams=[{"slot":2,"name":"Partner"}],target_slot=2,trade_intelligence=intel,trade_target_center=center)
 for marker in ("NO TRADE RECOMMENDATION","WHY NO TRADE EXISTS","Owner needs WR; partner has WR surplus.","Partner needs RB; owner has RB surplus.","Monitor this team.","Team fit summary","Risks to revisit","Diagnostics"):
  assert marker in html
 assert "<details class=\"trade-diagnostics\" open" not in html
 assert "SCHEDULE_FRESHNESS_THRESHOLD_UNVERIFIED" not in html

def test_rejected_package_shows_coverage_reason_and_closest_path():
 root=Path(__file__).resolve().parents[1];env=Environment(loader=FileSystemLoader(root/"templates"));env.globals["url_for"]=lambda endpoint,**kwargs:"/";env.globals["ux_route_evidence"]=lambda *args:{"fields":{}}
 package={"receive":[{"player":"Partner WR","position":"WR","trade_value":200,"projection":272,"weekly_score":16}],"send":[{"player":"Owner TE","position":"TE","trade_value":195,"projection":204,"weekly_score":12}],"owner_gain":5,"partner_gain":4,"balance_gap":1,"confidence":{"label":"HIGH","score":90}}
 owner={"counts":{"QB":2,"RB":4,"WR":3,"TE":2,"K":1,"DEF":1},"needs":{"QB":0,"RB":0,"WR":1,"TE":0,"K":0,"DEF":0},"surplus":{"QB":0,"RB":0,"WR":0,"TE":0,"K":0,"DEF":0}}
 partner={"counts":{"QB":2,"RB":4,"WR":5,"TE":2,"K":1,"DEF":1},"needs":{"QB":0,"RB":0,"WR":0,"TE":0,"K":0,"DEF":0},"surplus":{"QB":0,"RB":0,"WR":1,"TE":0,"K":0,"DEF":0}}
 intel={"allowed":True,"partner":{"name":"Partner"},"owner_profile":owner,"partner_profile":partner,"one_for_one":[package],"two_for_one":[],"preliminary_analysis":{"state":"AUTHORITATIVE","evidence_domains":{}}}
 center=build_trade_target_center(intel)
 html=env.get_template("trades.html").render(context={"mode":"LIVE"},meta={"team_name":"Mine"},teams=[{"slot":2,"name":"Partner"}],target_slot=2,trade_intelligence=intel,trade_target_center=center)
 for marker in ("PACKAGE REJECTED","Owner TE (TE)","Partner WR (WR)","TE → WR","Owner: Would leave TE below minimum coverage.","CLOSEST TRADE PATH","Partner has WR available for an owner need.","Monitor if:","Re-evaluate if owner TE coverage changes."):
  assert marker in html
 assert "<details class=\"trade-diagnostics\" open" not in html
