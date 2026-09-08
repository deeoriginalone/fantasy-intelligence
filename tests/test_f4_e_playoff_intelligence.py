from services.playoff_intelligence import build_playoff_intelligence, standings_order

def teams(): return [
 {'name':'Mine','wins':5,'losses':4,'ties':0,'points_for':1050},
 {'name':'Alpha','wins':7,'losses':2,'ties':0,'points_for':1100},
 {'name':'Beta','wins':6,'losses':3,'ties':0,'points_for':1080},
 {'name':'Gamma','wins':4,'losses':5,'ties':0,'points_for':990},
]
def test_standings_order_is_deterministic(): assert [x['name'] for x in standings_order(teams())]==['Alpha','Beta','Mine','Gamma']
def test_playoff_contract_and_no_input_mutation():
 rows=teams(); before=[dict(x) for x in rows]; result=build_playoff_intelligence(rows,'Mine',2,3,[{'opponent':'Alpha'},{'opponent':'Gamma'}]); assert rows==before; assert result['projected_seed']==3; assert 0<=result['playoff_probability']<=100; assert result['must_win'] is True; assert 'submit' in result['methodology'].lower()
def test_missing_owner_fails_closed(): assert build_playoff_intelligence(teams(),'Missing',2,3,[])['allowed'] is False
def test_unknown_schedule_is_reported_not_invented(): assert 'REMAINING_SCHEDULE_UNKNOWN' in build_playoff_intelligence(teams(),'Mine',2,3,None)['blockers']
