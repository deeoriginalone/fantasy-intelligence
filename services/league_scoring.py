"""Pure, deterministic league scoring of a projected per-game stat line with Sleeper scoring_settings.

Only rules that can be reproduced exactly from the provider stat line contribute to the value. A
rule that cannot be reproduced is listed as a missing scoring component; when its contribution can
be bounded from the stat line, the projection is reported as a range instead of a point value.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

SCHEMA_VERSION = "league-scored-projection.v1"
SCORING_BASIS = "SLEEPER_LEAGUE_SCORING_SETTINGS"
UNIT = "fantasy_points"
OFFENSE_POSITIONS = frozenset({"QB", "RB", "WR", "TE"})

OFFENSE_DIRECT = {
    "pass_yd": "passYds", "pass_td": "passTds", "pass_int": "passInts", "pass_att": "passAtt", "pass_cmp": "passCmp",
    "pass_fd": "passFd", "pass_sack": "sacks", "pass_int_td": "pickSix",
    "rush_yd": "rushYds", "rush_td": "rushTds", "rush_att": "rushAtt", "rush_fd": "rushFd",
    "rec": "receptions", "rec_yd": "recYds", "rec_td": "recTds", "rec_fd": "recFd",
    "fum_lost": "fumblesLost", "fum": "fumbles", "fum_rec_td": "fumbleRecoveryTds",
    "st_td": "stTds", "st_ff": "stFumblesForced", "st_fum_rec": "stFumbleRecoveries",
}
OFFENSE_COMBINED = (
    (("pass_2pt", "rush_2pt", "rec_2pt"), "twoPt", "Two-point conversions are one combined projected component."),
    (("kr_yd", "pr_yd"), "retYds", "Kick and punt return yards are one combined projected component."),
)
POSITION_RECEPTION_BONUS = {"bonus_rec_rb": "RB", "bonus_rec_wr": "WR", "bonus_rec_te": "TE"}
KICKER_DIRECT = {
    "fgm_0_19": "fgMade0to19", "fgm_20_29": "fgMade20to29", "fgm_30_39": "fgMade30to39", "fgm_40_49": "fgMade40to49",
    "fgmiss_0_19": "fgMissed0to19", "fgmiss_20_29": "fgMissed20to29", "fgmiss_30_39": "fgMissed30to39", "fgmiss_40_49": "fgMissed40to49",
    "xpm": "patMade", "xpmiss": "patMissed", "fgm": "fgMade", "fgm_yds": "fgMadeYds", "fgm_yds_over_30": "fgMadeYdsOver30",
}
KICKER_MISS_BUCKETS = ("fgMissed0to19", "fgMissed20to29", "fgMissed30to39", "fgMissed40to49", "fgMissed50plus")
KICKER_LONG = (
    (("fgm_50_59", "fgm_60p", "fgm_50p"), "fgMade50plus", "made"),
    (("fgmiss_50_59", "fgmiss_60p", "fgmiss_50p"), "fgMissed50plus", "missed"),
)
DEF_DIRECT = {
    "sack": "defSacks", "int": "defInterceptions", "safe": "defSafeties", "blk_kick": "defBlocks", "def_2pt": "defTwoPtReturns",
    "pts_allow": "pointsAllowed", "yds_allow": "yardsAllowed",
}
DEF_UNSPLIT = (
    ("fum_rec", "def_st_fum_rec", "defFumbleRecoveries", "Special-teams and defensive fumble recoveries are not separated in the stat line."),
    ("ff", "def_st_ff", "defFumblesForced", "Special-teams and defensive forced fumbles are not separated in the stat line."),
)
PA_TIER_KEYS = (("pts_allow_0", 0), ("pts_allow_1_6", 6), ("pts_allow_7_13", 13), ("pts_allow_14_20", 20), ("pts_allow_21_27", 27), ("pts_allow_28_34", 34), ("pts_allow_35p", 999))
PROVIDER_DEFAULT_PA_LADDER = ((0, 10.0), (6, 7.0), (13, 4.0), (20, 1.0), (27, 0.0), (34, -1.0), (999, -4.0))
YA_TIER_PREFIX = "yds_allow_"
DEF_ONLY_KEYS = frozenset({"sack", "int", "fum_rec", "ff", "safe", "blk_kick", "tkl", "tkl_solo", "tkl_ast", "tkl_loss", "qb_hit",
                           "int_ret_yd", "fum_ret_yd", "blk_kick_ret_yd", "fg_ret_yd", "bonus_sack_2p", "bonus_tkl_10p"})


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _position(value: Any) -> str:
    position = str(value or "").strip().upper()
    return {"DST": "DEF", "D/ST": "DEF", "PK": "K"}.get(position, position)


def rule_group(key: str) -> str:
    """Which roster position group a Sleeper scoring rule applies to."""
    if key.startswith("idp_"):
        return "IDP"
    if key.startswith(("fgm", "fgmiss", "xpm", "xpmiss")):
        return "K"
    if key.startswith(("def_", "pts_allow", "yds_allow", "bonus_def_")) or key in DEF_ONLY_KEYS:
        return "DEF"
    return "OFFENSE"


def _group_for(position: str) -> str | None:
    return "OFFENSE" if position in OFFENSE_POSITIONS else position if position in {"K", "DEF"} else None


def league_score_stat_line(stat_line: Mapping[str, Any] | None, scoring_settings: Mapping[str, Any] | None, *, position: Any,
                           breakdown: Mapping[str, Any] | None = None, coverage: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Score one projected per-game stat line with the league's exact rules; never fabricates a rule."""
    position = _position(position)
    result = {
        "schema_version": SCHEMA_VERSION, "unit": UNIT, "scoring_basis": SCORING_BASIS, "position": position,
        "value": None, "value_range": None, "reproduced_points": None, "scoring_completeness": "UNAVAILABLE",
        "components": [], "missing_scoring_components": [], "limitations": [], "blocker": None,
    }
    group = _group_for(position)
    if group is None:
        return {**result, "blocker": "SCORING_POSITION_UNSUPPORTED"}
    if not isinstance(scoring_settings, Mapping) or not scoring_settings:
        return {**result, "blocker": "LEAGUE_SCORING_UNAVAILABLE"}
    if not isinstance(stat_line, Mapping) or not stat_line:
        return {**result, "blocker": "PROJECTION_STAT_LINE_UNAVAILABLE"}
    coverage = coverage if isinstance(coverage, Mapping) else {}
    weights = {}
    for key, raw in scoring_settings.items():
        weight = _number(raw)
        if weight is None:
            if raw not in (None, ""):
                result["missing_scoring_components"].append({"rule": str(key), "weight": raw, "reason": "The league weight is not numeric.", "bounds": None})
            continue
        if weight and rule_group(str(key)) == group:
            weights[str(key)] = weight
    components, missing, limitations = [], result["missing_scoring_components"], []
    handled = set()

    def quantity(component: str) -> float | None:
        # The provider marks each stat-line component it models; any other listed state is not a usable projection.
        if component in coverage and str(coverage.get(component) or "").strip().lower() != "modeled":
            return None
        return _number(stat_line.get(component))

    def add(rule: str, weight: float, component: str, amount: float) -> None:
        components.append({"rule": rule, "weight": weight, "stat": component, "quantity": round(amount, 4), "points": round(weight * amount, 4)})

    def lack(rule: str, weight: Any, reason: str, bounds: tuple[float, float] | None) -> None:
        missing.append({"rule": rule, "weight": weight, "reason": reason, "bounds": None if bounds is None else {"low": round(bounds[0], 4), "high": round(bounds[1], 4)}})

    def direct(table: Mapping[str, str]) -> None:
        for rule, component in table.items():
            if rule not in weights:
                continue
            handled.add(rule)
            amount = quantity(component)
            if amount is None:
                lack(rule, weights[rule], f"The stat line has no '{component}' component.", None)
            else:
                add(rule, weights[rule], component, amount)

    def unsplit(rules: tuple[str, ...], component: str, reason: str) -> None:
        active = [rule for rule in rules if rule in weights]
        if not active:
            return
        handled.update(active)
        values = [weights.get(rule, 0.0) for rule in rules]
        amount = quantity(component)
        if amount is None:
            lack("/".join(rules), {rule: weights.get(rule, 0.0) for rule in rules}, f"The stat line has no '{component}' component.", None)
        elif len(set(values)) == 1:
            add("/".join(active) if len(active) > 1 else active[0], values[0], component, amount)
        else:
            lack("/".join(rules), {rule: weights.get(rule, 0.0) for rule in rules}, reason + " The league scores them differently.",
                 (amount * min(values), amount * max(values)))

    if group == "OFFENSE":
        direct(OFFENSE_DIRECT)
        for rules, component, reason in OFFENSE_COMBINED:
            unsplit(rules, component, reason)
        for rule, bonus_position in POSITION_RECEPTION_BONUS.items():
            if rule in weights:
                handled.add(rule)
                if position == bonus_position:
                    amount = quantity("receptions")
                    if amount is None:
                        lack(rule, weights[rule], "The stat line has no 'receptions' component.", None)
                    else:
                        add(rule, weights[rule], "receptions", amount)
    elif group == "K":
        direct(KICKER_DIRECT)
        if "fgmiss" in weights:
            handled.add("fgmiss")
            buckets = [quantity(component) for component in KICKER_MISS_BUCKETS]
            if any(amount is None for amount in buckets):
                lack("fgmiss", weights["fgmiss"], "Missed field goals by distance are incomplete in the stat line.", None)
            else:
                add("fgmiss", weights["fgmiss"], "+".join(KICKER_MISS_BUCKETS), sum(buckets))
        for (split_59, split_60, combined), component, verb in KICKER_LONG:
            w59, w60, w50 = weights.get(split_59, 0.0), weights.get(split_60, 0.0), weights.get(combined, 0.0)
            if not (w59 or w60 or w50):
                continue
            handled.update(rule for rule in (split_59, split_60, combined) if rule in weights)
            label = f"{split_59}/{split_60}/{combined}"
            amount = quantity(component)
            if amount is None:
                lack(label, {split_59: w59, split_60: w60, combined: w50}, f"The stat line has no '{component}' component.", None)
            elif w50 and (w59 or w60):
                lack(label, {split_59: w59, split_60: w60, combined: w50}, "Overlapping 50+ yard field-goal rules cannot be reproduced exactly.", None)
            elif w50:
                add(combined, w50, component, amount)
            elif w59 == w60:
                add(f"{split_59}/{split_60}", w59, component, amount)
            else:
                lack(label, {split_59: w59, split_60: w60, combined: w50},
                     f"The stat line combines {verb} field goals of 50+ yards; the league scores 50-59 ({w59:g}) and 60+ ({w60:g}) yards differently.",
                     (amount * min(w59, w60), amount * max(w59, w60)))
    else:
        direct(DEF_DIRECT)
        for defensive, special, component, reason in DEF_UNSPLIT:
            unsplit((defensive, special), component, reason)
        if "def_td" in weights or "def_st_td" in weights:
            handled.update(rule for rule in ("def_td", "def_st_td") if rule in weights)
            total, returns = quantity("defTds"), quantity("defReturnTds")
            if total is None or returns is None:
                lack("def_td/def_st_td", {"def_td": weights.get("def_td", 0.0), "def_st_td": weights.get("def_st_td", 0.0)},
                     "Defensive and return touchdowns are unavailable in the stat line.", None)
            else:
                if "def_td" in weights:
                    add("def_td", weights["def_td"], "defTds-defReturnTds", max(0.0, total - returns))
                if "def_st_td" in weights:
                    add("def_st_td", weights["def_st_td"], "defReturnTds", returns)
                if weights.get("def_td", 0.0) != weights.get("def_st_td", 0.0):
                    limitations.append("Blocked-kick return touchdowns are scored as defensive touchdowns, following the provider's event classification.")
        tier_rules = [rule for rule, _ in PA_TIER_KEYS if rule in weights]
        if tier_rules:
            handled.update(tier_rules)
            ladder = tuple((bound, weights.get(rule, 0.0)) for rule, bound in PA_TIER_KEYS)
            tier_points = [points for _, points in ladder]
            expected = _number((breakdown or {}).get("paTierExpectedPPG")) if isinstance(breakdown, Mapping) else None
            if ladder == PROVIDER_DEFAULT_PA_LADDER and expected is not None:
                components.append({"rule": "pts_allow tiers", "weight": None, "stat": "breakdown.paTierExpectedPPG", "quantity": None,
                                   "points": round(expected, 4), "method": "PROVIDER_TIER_EXPECTATION_UNDER_IDENTICAL_TIERS"})
                limitations.append("Points-allowed tiers use the provider's expected tier points, computed under tiers identical to this league's.")
            else:
                lack("pts_allow tiers", {rule: weights.get(rule, 0.0) for rule, _ in PA_TIER_KEYS},
                     "Tiered points allowed need the provider's tier expectation under identical tiers.", (min(tier_points), max(tier_points)))
        ya_rules = sorted(rule for rule in weights if rule.startswith(YA_TIER_PREFIX))
        if ya_rules:
            handled.update(ya_rules)
            tier_points = [weights[rule] for rule in ya_rules] + [0.0]
            lack("yds_allow tiers", {rule: weights[rule] for rule in ya_rules}, "Tiered yards allowed cannot be reproduced from a mean stat line.",
                 (min(tier_points), max(tier_points)))
    for rule in sorted(set(weights) - handled):
        lack(rule, weights[rule], "No projected stat-line component reproduces this league rule.", None)

    reproduced = sum(component["points"] for component in components)
    result.update(components=components, missing_scoring_components=sorted(missing, key=lambda item: item["rule"]), limitations=limitations,
                  reproduced_points=round(reproduced, 2))
    if not missing:
        value = round(reproduced, 2)
        return {**result, "value": value, "value_range": {"low": value, "high": value}, "scoring_completeness": "COMPLETE"}
    if all(item["bounds"] is not None for item in missing):
        low = reproduced + sum(item["bounds"]["low"] for item in missing)
        high = reproduced + sum(item["bounds"]["high"] for item in missing)
        return {**result, "value_range": {"low": round(low, 2), "high": round(high, 2)}, "scoring_completeness": "PARTIAL",
                "blocker": "LEAGUE_SCORING_PARTIAL"}
    return {**result, "scoring_completeness": "PARTIAL", "blocker": "LEAGUE_SCORING_UNREPRODUCIBLE"}
