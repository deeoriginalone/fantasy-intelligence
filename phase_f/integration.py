from __future__ import annotations
from importlib import import_module
from .contracts import NormalizedRecommendation

class VerifiedCallableAdapter:
    def __init__(self, target: str, *, read_only: bool, synthetic: bool=False):
        if not read_only:
            raise ValueError("sandbox adapter must be read-only")
        if ":" not in target:
            raise ValueError("target must use module:function")
        module_name, function_name=target.split(":",1)
        fn=getattr(import_module(module_name), function_name, None)
        if not callable(fn):
            raise ValueError(f"target is not callable: {target}")
        self.fn=fn; self.target=target; self.synthetic=synthetic

    def recommend(self, state):
        result=NormalizedRecommendation.from_value(self.fn(state))
        if result.player_id in state.drafted_player_ids:
            raise ValueError(f"adapter recommended drafted player: {result.player_id}")
        metadata=dict(result.metadata)
        metadata.update({"adapter_target":self.target,"synthetic":self.synthetic})
        return NormalizedRecommendation(result.player_id,result.reason,result.score,metadata)
