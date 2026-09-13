from collections import Counter

REQUIRED_NEED_KEYS = ("QB", "RB", "WR", "TE", "FLEX", "K", "DEF")
FLEX_ELIGIBLE = ("RB", "WR", "TE")
DEFAULT_DEPTH_TARGETS = {"QB": 2, "RB": 4, "WR": 4, "TE": 2, "K": 1, "DEF": 1}


def normalize_position(value):
    value = str(value or "").upper()
    return "DEF" if value == "DST" else value


def league_settings_contract(league, source="Sleeper API", blocker=None):
    league = dict(league or {})
    raw = league.get("roster_positions")
    if blocker or not isinstance(raw, list) or not raw:
        return {
            "state": "BLOCKED",
            "source": source,
            "blocker": blocker or "LEAGUE_ROSTER_POSITIONS_UNAVAILABLE",
            "starter_slots": {},
            "flex_eligible_positions": [],
            "full_ppr": None,
        }
    aliases = {"BN": "BENCH", "W/R/T": "FLEX", "WRRB_FLEX": "FLEX", "REC_FLEX": "FLEX", "DST": "DEF"}
    slots = [aliases.get(str(item).upper(), str(item).upper()) for item in raw]
    starters = Counter(item for item in slots if item not in {"BENCH", "IR", "TAXI"})
    rec = (league.get("scoring_settings") or {}).get("rec")
    return {
        "state": "AVAILABLE",
        "source": source,
        "blocker": None,
        "starter_slots": dict(starters),
        "flex_eligible_positions": list(FLEX_ELIGIBLE) if starters.get("FLEX") else [],
        "full_ppr": rec in (1, 1.0),
    }


def _blocked_position(position, source, blocker):
    return {
        "position": position,
        "state": "BLOCKED",
        "source": source,
        "blocker": blocker,
        "required_slots": 0,
        "required_starters": 0,
        "rostered": None if position == "FLEX" else 0,
        "rostered_or_eligible": None,
        "shortage": None,
        "starter_shortage": None,
        "starter_coverage": "UNAVAILABLE",
        "eligible_positions": [],
        "eligible_depth": None,
        "depth_target": None,
        "depth_shortage": None,
        "depth_status": "UNAVAILABLE",
        "need": "UNAVAILABLE",
        "strategic_need": "UNAVAILABLE",
        "priority": "UNAVAILABLE",
        "drivers": [],
    }


def _available_position(position, required, rostered, depth_target, source, eligible_positions, eligible_depth=None):
    starter_shortage = max(0, required - rostered)
    depth_shortage = max(0, depth_target - rostered)
    starter_coverage = "SHORTAGE" if starter_shortage else "COVERED"
    if rostered < depth_target:
        depth_status = "BELOW_TARGET"
    elif rostered > depth_target:
        depth_status = "ABOVE_TARGET"
    else:
        depth_status = "AT_TARGET"
    if starter_shortage:
        strategic_need, priority = "ADD_STARTER", "HIGH"
        drivers = [f"{starter_shortage} required {position} starter slot(s) are uncovered."]
    elif depth_shortage:
        strategic_need, priority = "ADD_DEPTH", "MEDIUM"
        drivers = [f"{rostered} {position} option(s) are available against a depth target of {depth_target}."]
    else:
        strategic_need, priority = "NO_ACTION", "LOW"
        drivers = [f"{position} starter coverage and the supported depth target are satisfied."]
    return {
        "position": position,
        "state": "AVAILABLE",
        "source": source,
        "blocker": None,
        "required_slots": required,
        "required_starters": required,
        "rostered": None if position == "FLEX" else rostered,
        "rostered_or_eligible": rostered,
        "shortage": starter_shortage,
        "starter_shortage": starter_shortage,
        "starter_coverage": starter_coverage,
        "eligible_positions": list(eligible_positions),
        "eligible_depth": eligible_depth,
        "depth_target": depth_target,
        "depth_shortage": depth_shortage,
        "depth_status": depth_status,
        "need": strategic_need,
        "strategic_need": strategic_need,
        "priority": priority,
        "drivers": drivers,
    }


def team_needs_contract(roster, settings, source="shared team-needs contract"):
    settings = dict(settings or {})
    if settings.get("state") != "AVAILABLE":
        blocker = settings.get("blocker") or "LEAGUE_SETTINGS_UNAVAILABLE"
        return {key: _blocked_position(key, source, blocker) for key in REQUIRED_NEED_KEYS}

    counts = Counter(normalize_position((player or {}).get("position")) for player in (roster or []))
    slots = dict(settings.get("starter_slots") or {})
    flex_positions = [normalize_position(item) for item in settings.get("flex_eligible_positions") or []]
    result = {}

    for key in REQUIRED_NEED_KEYS:
        if key == "FLEX":
            required = int(slots.get("FLEX") or 0)
            base = sum(int(slots.get(position) or 0) for position in flex_positions)
            eligible_depth = max(0, sum(counts.get(position, 0) for position in flex_positions) - base)
            result[key] = _available_position(
                key,
                required,
                eligible_depth,
                required,
                source,
                flex_positions,
                eligible_depth=eligible_depth,
            )
        else:
            required = int(slots.get(key) or 0)
            rostered = int(counts.get(key) or 0)
            depth_target = max(required, int(DEFAULT_DEPTH_TARGETS.get(key, required)))
            result[key] = _available_position(key, required, rostered, depth_target, source, [key])
    return result


def build_team_needs_summary(team_needs):
    summary = []
    for position in REQUIRED_NEED_KEYS:
        item = dict((team_needs or {}).get(position) or {})
        state = item.get("state")
        strategic_need = item.get("strategic_need") or item.get("need")
        if state != "AVAILABLE":
            blocker = item.get("blocker") or "required evidence is unavailable"
            summary.append(f"{position} analysis unavailable: {blocker}.")
        elif strategic_need == "ADD_STARTER":
            summary.append(f"Add a {position} starter: {item.get('starter_shortage')} required starting slot(s) are uncovered.")
        elif strategic_need == "ADD_DEPTH":
            summary.append(f"Add {position} depth: {item.get('rostered_or_eligible')} available, target {item.get('depth_target')}.")
        elif strategic_need == "MONITOR":
            driver = (item.get("drivers") or [f"Review {position} evidence."])[0]
            summary.append(f"Monitor {position}: {driver}")
    return summary
