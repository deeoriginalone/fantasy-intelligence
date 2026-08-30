"""Round-aware candidate filtering for Draft HQ.

Player tuple contract used by the live application:
0 rank, 1 name, 2 position, 3 NFL team, 4 starred, 5 drafted,
6 projection, 7 tier, 8 ADP.

The full available-player list is never mutated. This module returns a focused pool
for recommendations and prediction engines plus an audit payload.
"""
from __future__ import annotations

CORE = ("QB", "RB", "WR", "TE")
POSITION_FLOORS = {"QB": 10, "RB": 20, "WR": 20, "TE": 10}


def _number(value, default=999.0):
    try:
        number = float(value)
        return number if number >= 0 else default
    except (TypeError, ValueError):
        return default


def _field(player, index, default=None):
    try:
        value = player[index]
        return default if value is None else value
    except (TypeError, IndexError, KeyError):
        return default


def _name_key(player):
    return " ".join(str(_field(player, 1, "")).lower().split())


def _position(player):
    return str(_field(player, 2, "")).upper()


def _rank(player):
    return _number(_field(player, 0))


def _adp(player):
    value = _number(_field(player, 8))
    return value if value < 999 else 999.0


def _tier(player):
    return _number(_field(player, 7), 99.0)


def _projection(player):
    return _number(_field(player, 6), 0.0)


def _drafted(player):
    return bool(_field(player, 5, False))


def _limits(round_no):
    round_no = max(1, int(round_no or 1))
    if round_no <= 2:
        return 50, 45
    if round_no <= 4:
        return 65, 80
    if round_no <= 8:
        return 80, 140
    return 100, 240


def filter_candidate_pool(players, current_round=1, max_candidates=None):
    """Return ``(filtered_players, audit)`` without modifying ``players``.

    Protection rules:
    - only QB/RB/WR/TE
    - no drafted rows
    - deduplicate normalized player names, retaining the strongest record
    - keep players inside a round-aware rank/ADP window
    - always protect Tier 1/2 players
    - always protect top available players at each core position
    - cap the final recommendation pool while preserving protected players
    """
    source = list(players or [])
    round_no = max(1, int(current_round or 1))
    default_cap, market_limit = _limits(round_no)
    cap = max(20, int(max_candidates or default_cap))

    rejection = {
        "missing_name": 0,
        "non_core_position": 0,
        "already_drafted": 0,
        "duplicate": 0,
        "outside_market_window": 0,
    }

    # Deduplicate by normalized name. The better record wins by rank, ADP, then
    # projection. This protects the recommendation engine from duplicate imports.
    best_by_name = {}
    for player in source:
        name = _name_key(player)
        if not name:
            rejection["missing_name"] += 1
            continue
        position = _position(player)
        if position not in CORE:
            rejection["non_core_position"] += 1
            continue
        if _drafted(player):
            rejection["already_drafted"] += 1
            continue
        key = (_rank(player), _adp(player), -_projection(player))
        existing = best_by_name.get(name)
        if existing is None:
            best_by_name[name] = player
        else:
            rejection["duplicate"] += 1
            existing_key = (_rank(existing), _adp(existing), -_projection(existing))
            if key < existing_key:
                best_by_name[name] = player

    unique = list(best_by_name.values())
    protected_names = set()

    # Tier protection prevents a strong imported tier from disappearing because its
    # ADP or rank value is sparse or stale.
    for player in unique:
        if _tier(player) <= 2:
            protected_names.add(_name_key(player))

    # Position protection maintains enough viable options for positional comparisons.
    for position, floor in POSITION_FLOORS.items():
        positional = sorted(
            (p for p in unique if _position(p) == position),
            key=lambda p: (_rank(p), _adp(p), -_projection(p), _name_key(p)),
        )
        for player in positional[:floor]:
            protected_names.add(_name_key(player))

    eligible = []
    outside = []
    for player in unique:
        name = _name_key(player)
        in_window = _rank(player) <= market_limit or _adp(player) <= market_limit
        if in_window or name in protected_names:
            eligible.append(player)
        else:
            outside.append(player)
    rejection["outside_market_window"] = len(outside)

    # Sort by a market score rather than rank alone so a valid ADP can rescue a
    # partially ranked player while elite rank remains the primary signal.
    def sort_key(player):
        market = min(_rank(player), _adp(player))
        protected = 0 if _name_key(player) in protected_names else 1
        return (protected, market, _rank(player), _adp(player), -_projection(player), _name_key(player))

    eligible.sort(key=sort_key)

    # Protected entries are retained first. If protection exceeds the nominal cap,
    # the cap expands rather than silently removing a top positional or tier option.
    protected = [p for p in eligible if _name_key(p) in protected_names]
    regular = [p for p in eligible if _name_key(p) not in protected_names]
    effective_cap = max(cap, len(protected))
    filtered = (protected + regular)[:effective_cap]
    filtered.sort(key=lambda p: (_rank(p), _adp(p), -_projection(p), _name_key(p)))

    by_position = {position: 0 for position in CORE}
    for player in filtered:
        by_position[_position(player)] += 1

    audit = {
        "raw_candidates": len(source),
        "unique_core_candidates": len(unique),
        "filtered_candidates": len(filtered),
        "nominal_cap": cap,
        "effective_cap": effective_cap,
        "market_limit": market_limit,
        "current_round": round_no,
        "protected_candidates": len(protected_names),
        "by_position": by_position,
        "rejected": rejection,
        "full_board_preserved": True,
    }
    return filtered, audit
