from pathlib import Path
from services.ux_evidence import evidence,page_evidence,lineup_explanations,waiver_explanations,gm_action_evidence,roster_lineage
ROOT=Path(__file__).resolve().parents[1]
def test_dashboard_truth():
 t=(ROOT/'templates/dashboard.html').read_text()
 for x in (
    '30,000 Simulations Completed',
    'READY FOR DRAFT DAY',
    '465 Projections Loaded',
    '401 VBD Tiers Loaded'
):
    assert x not in t
    assert 'Fantasy Intelligence Champions League logo' in t
def test_page_fail_closed(): assert not page_evidence(page='x',fields={'a':evidence(None)})['ready']
def test_lineup_reason(): assert lineup_explanations({'start_sit_decisions':[{'reason':'R'}]})['decisions'][0]['why']=='R'
def test_waiver_owned_filter(): assert [x['player'] for x in waiver_explanations([{'player':'A'},{'player':'B'}],['a'])]==['B']
def test_gm_source(): assert gm_action_evidence({'actions':[{'action':'A','source':'S'}]})['actions'][0]['source']=='S'
def test_lineage_unknown(): assert roster_lineage([{'player':'A'}])[0]['health']['state']=='UNKNOWN'
def test_panels():
 for n in ('lineup.html','waivers.html','trades.html','gm.html','team.html'):
  p=ROOT/'templates'/n
  if p.exists(): assert '_ux_completion_panel.html' in p.read_text()
