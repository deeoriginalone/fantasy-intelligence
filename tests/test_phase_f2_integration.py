from datetime import datetime, timedelta, timezone
import json
import pytest
from phase_f.contracts import NormalizedRecommendation
from phase_f.freshness import SourceStatus, gate
from phase_f.integration import VerifiedCallableAdapter
from phase_f.models import DraftPick, DraftState
from phase_f.outcomes import evaluate_snapshot
from phase_f.snapshots import SnapshotWriter
from phase_f.strategies import get_strategy

def test_normalizes_mapping():
    value=NormalizedRecommendation.from_value({'player_id':'p1','reason':'best','score':8.5})
    assert value.player_id=='p1' and value.score==8.5

def test_requires_read_only():
    with pytest.raises(ValueError,match='read-only'):
        VerifiedCallableAdapter('examples.synthetic_adapter:recommend',read_only=False)

def test_blocks_drafted_recommendation(monkeypatch):
    adapter=VerifiedCallableAdapter('examples.synthetic_adapter:recommend',read_only=True,synthetic=True)
    state=DraftState(teams=2,rounds=1); state.drafted_player_ids.add('synthetic-recommendation-1')
    with pytest.raises(ValueError,match='drafted player'): adapter.recommend(state)

def test_freshness_gate():
    now=datetime.now(timezone.utc)
    overall,details=gate([SourceStatus('players',now-timedelta(hours=1),True,2),SourceStatus('projections',None,True,6)])
    assert overall=='BLOCKED' and details['projections']=='BLOCKED'

def test_snapshot_writer(tmp_path):
    path=tmp_path/'s.jsonl'; SnapshotWriter(path).append(1,NormalizedRecommendation('p1','reason',1.0,{})); row=json.loads(path.read_text())
    assert row['pick_no']==1 and row['player_id']=='p1'

def test_outcome_evaluation():
    picks=[DraftPick(3,1,'2','p1')]
    result=evaluate_snapshot({'pick_no':1,'player_id':'p1'},picks)
    assert result['drafted_later'] and result['picks_until_drafted']==2

def test_known_strategy():
    assert get_strategy('balanced')['RB']==1.0
