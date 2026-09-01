import pytest
from phase_f.identity_cache import IdentityCache
from phase_f.player_mapper import MappingStatus, PlayerMapper, PlayerMappingError
from phase_f.sleeper_identity_adapter import SleeperDraftEventAdapter
from phase_f.snapshot_identity import enrich_recommendation_snapshot

class Repo:
    def __init__(self, rows): self.rows=rows; self.calls=0
    def find_by_sleeper_id(self,sid): self.calls+=1; return self.rows.get(sid,[])

def test_exact_mapping():
    mapper=PlayerMapper(Repo({"3294":[(10,"Dak Prescott","QB","DAL")]}))
    result=mapper.resolve_sleeper_id("3294")
    assert result.status is MappingStatus.MATCHED and result.local_player_id=="10"

def test_unknown_is_unmatched():
    result=PlayerMapper(Repo({})).resolve_sleeper_id("unknown")
    assert result.status is MappingStatus.UNMATCHED

def test_multiple_local_ids_are_conflict():
    rows={"x":[(1,"Isaiah Williams","WR","DET"),(2,"Isaiah Williams","WR","CIN")]}
    result=PlayerMapper(Repo(rows)).resolve_sleeper_id("x")
    assert result.status is MappingStatus.CONFLICT

def test_cache_calls_repository_once():
    repo=Repo({"3294":[(10,"Dak Prescott","QB","DAL")]})
    cache=IdentityCache(PlayerMapper(repo)); cache.resolve_sleeper_id("3294"); cache.resolve_sleeper_id("3294")
    assert repo.calls==1

def test_sleeper_event_uses_local_id():
    mapper=PlayerMapper(Repo({"3294":[(10,"Dak Prescott","QB","DAL")]}))
    event={"pick_no":1,"round":1,"roster_id":1,"player_id":"3294","metadata":{}}
    pick=SleeperDraftEventAdapter(mapper).translate(event)
    assert pick.player_id=="10" and pick.player_name=="Dak Prescott"

def test_event_blocks_unmatched():
    adapter=SleeperDraftEventAdapter(PlayerMapper(Repo({})))
    with pytest.raises(PlayerMappingError):
        adapter.translate({"pick_no":1,"round":1,"roster_id":1,"player_id":"x"})

def test_snapshot_contains_both_identities():
    identity=PlayerMapper(Repo({"3294":[(10,"Dak Prescott","QB","DAL")]})).require_local_id("3294")
    row=enrich_recommendation_snapshot({"pick_no":1,"score":99},identity)
    assert row["local_player_id"]=="10" and row["source_player_id"]=="3294"
