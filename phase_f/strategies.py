from __future__ import annotations
STRATEGIES={
 "balanced":{"QB":1.0,"RB":1.0,"WR":1.0,"TE":1.0},
 "hero_rb":{"QB":0.95,"RB":1.15,"WR":1.05,"TE":0.95},
 "zero_rb":{"QB":1.0,"RB":0.80,"WR":1.20,"TE":1.05},
 "rb_heavy":{"QB":0.9,"RB":1.25,"WR":0.95,"TE":0.9},
 "wr_heavy":{"QB":0.9,"RB":0.95,"WR":1.25,"TE":0.9},
 "elite_qb":{"QB":1.20,"RB":1.0,"WR":1.0,"TE":0.95},
}
def get_strategy(name):
    if name not in STRATEGIES:
        raise ValueError(f"unknown strategy: {name}")
    return dict(STRATEGIES[name])
