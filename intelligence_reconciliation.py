"""Reconcile model, crowd, and market positions."""
from typing import Any, Dict, Optional

def reconcile(*, model_pick: str, model_probability: float,
              crowd_pick: Optional[str], market_favorite: Optional[str]) -> Dict[str, Any]:
    p = float(model_probability)
    if not 0 <= p <= 1:
        raise ValueError("model_probability must be between 0 and 1")
    agrees_crowd = bool(crowd_pick) and model_pick == crowd_pick
    agrees_market = bool(market_favorite) and model_pick == market_favorite
    if agrees_crowd and agrees_market:
        signal = "CONSENSUS"
    elif not agrees_crowd and not agrees_market and crowd_pick and market_favorite:
        signal = "EXTREME_CONTRARIAN"
    else:
        signal = "SPLIT_SIGNAL"
    return {
        "model_pick": model_pick,
        "model_probability": p,
        "crowd_pick": crowd_pick,
        "market_favorite": market_favorite,
        "agrees_with_crowd": agrees_crowd,
        "agrees_with_market": agrees_market,
        "signal": signal,
    }
