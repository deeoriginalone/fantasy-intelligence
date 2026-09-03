"""Shared roster-slot assignment used by draft and waiver workflows."""

STARTER_SLOT_ORDER = ("QB", "RB1", "RB2", "WR1", "WR2", "TE", "FLEX")
CORE_POSITIONS = ("QB", "RB", "WR", "TE")


def build_roster_slots(roster):
    """Return starter slots and bench using the repository's roster tuple shape.

    Expected rows contain at least: id, player_name, position. Additional
    columns are preserved. Assignment intentionally matches the former app.py
    implementation exactly.
    """
    slots = {name: None for name in STARTER_SLOT_ORDER}
    bench = []
    for player in roster or []:
        if not isinstance(player, (list, tuple)) or len(player) < 3:
            continue
        position = str(player[2] or "").upper()
        if position == "QB" and slots["QB"] is None:
            slots["QB"] = player
        elif position == "RB" and slots["RB1"] is None:
            slots["RB1"] = player
        elif position == "RB" and slots["RB2"] is None:
            slots["RB2"] = player
        elif position == "WR" and slots["WR1"] is None:
            slots["WR1"] = player
        elif position == "WR" and slots["WR2"] is None:
            slots["WR2"] = player
        elif position == "TE" and slots["TE"] is None:
            slots["TE"] = player
        elif position in {"RB", "WR", "TE"} and slots["FLEX"] is None:
            slots["FLEX"] = player
        else:
            bench.append(player)
    return slots, bench
