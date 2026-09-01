from __future__ import annotations

def evaluate_snapshot(snapshot, later_picks):
    player=snapshot["player_id"]
    later=[p for p in later_picks if p.player_id==player]
    if not later:
        return {"recommended_player":player,"drafted_later":False,"picks_until_drafted":None}
    selected=min(later,key=lambda p:p.pick_no)
    return {"recommended_player":player,"drafted_later":True,"picks_until_drafted":selected.pick_no-int(snapshot["pick_no"])}
