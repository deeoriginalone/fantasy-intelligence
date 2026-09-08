from pathlib import Path
from jinja2 import Environment,FileSystemLoader

def test_playoff_template_renders_and_has_no_submission_endpoint():
 root=Path(__file__).resolve().parents[1]; env=Environment(loader=FileSystemLoader(root/'templates')); env.globals['url_for']=lambda endpoint,**kwargs:'/'
 intel={'blockers':['REMAINING_SCHEDULE_UNKNOWN'],'playoff_probability':55.0,'projected_seed':3,'risk_level':'MEDIUM','must_win':True,'schedule_strength':{'label':'UNKNOWN'},'recommendations':[{'action':'MUST_WIN','reason':'Urgent path.'}],'standings':[{'name':'Mine','wins':5,'losses':4,'ties':0,'win_pct':.556,'points_for':1050}],'methodology':'No transaction is submitted.'}
 html=env.get_template('playoffs.html').render(playoff_intelligence=intel)
 for text in ('Playoff Intelligence','55.0%','MUST WIN','Mine','No transaction is submitted.'): assert text in html
 for forbidden in ('submit_trade','submit_waiver','set_lineup'): assert forbidden not in html
