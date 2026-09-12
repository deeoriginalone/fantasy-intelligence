from collections import Counter

REQUIRED_NEED_KEYS = ("QB", "RB", "WR", "TE", "FLEX", "K", "DEF")
FLEX_ELIGIBLE = ("RB", "WR", "TE")

def normalize_position(value):
    value = str(value or "").upper()
    return "DEF" if value == "DST" else value

def league_settings_contract(league, source="Sleeper API", blocker=None):
    league = dict(league or {})
    raw = league.get("roster_positions")
    if blocker or not isinstance(raw, list) or not raw:
        return {"state":"BLOCKED","source":source,"blocker":blocker or "LEAGUE_ROSTER_POSITIONS_UNAVAILABLE","starter_slots":{},"flex_eligible_positions":[],"full_ppr":None}
    aliases={"BN":"BENCH","W/R/T":"FLEX","WRRB_FLEX":"FLEX","REC_FLEX":"FLEX","DST":"DEF"}
    slots=[aliases.get(str(x).upper(),str(x).upper()) for x in raw]
    starters=Counter(x for x in slots if x not in {"BENCH","IR","TAXI"})
    rec=(league.get("scoring_settings") or {}).get("rec")
    return {"state":"AVAILABLE","source":source,"blocker":None,"starter_slots":dict(starters),"flex_eligible_positions":list(FLEX_ELIGIBLE) if starters.get("FLEX") else [],"full_ppr":rec in (1,1.0)}

def team_needs_contract(roster, settings, source="shared team-needs contract"):
    settings=dict(settings or {})
    if settings.get("state") != "AVAILABLE":
        blocker=settings.get("blocker") or "LEAGUE_SETTINGS_UNAVAILABLE"
        return {key:{"state":"BLOCKED","source":source,"blocker":blocker,"required_slots":0,"rostered":None if key=="FLEX" else 0,"shortage":None,"eligible_positions":[],"eligible_depth":None,"need":"UNAVAILABLE"} for key in REQUIRED_NEED_KEYS}
    counts=Counter(normalize_position((p or {}).get("position")) for p in (roster or []))
    slots=dict(settings.get("starter_slots") or {})
    flex_positions=[normalize_position(x) for x in settings.get("flex_eligible_positions") or []]
    result={}
    for key in REQUIRED_NEED_KEYS:
        if key == "FLEX":
            required=int(slots.get("FLEX") or 0)
            base=sum(int(slots.get(p) or 0) for p in flex_positions)
            depth=max(0,sum(counts.get(p,0) for p in flex_positions)-base)
            shortage=max(0,required-depth)
            result[key]={"state":"AVAILABLE","source":source,"blocker":None,"required_slots":required,"rostered":None,"shortage":shortage,"eligible_positions":flex_positions,"eligible_depth":depth,"need":"HIGH" if shortage else "COVERED"}
        else:
            required=int(slots.get(key) or 0); rostered=int(counts.get(key) or 0); shortage=max(0,required-rostered)
            result[key]={"state":"AVAILABLE","source":source,"blocker":None,"required_slots":required,"rostered":rostered,"shortage":shortage,"eligible_positions":[key],"eligible_depth":max(0,rostered-required),"need":"HIGH" if shortage else "COVERED"}
    return result
