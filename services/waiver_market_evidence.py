"""W5 league FAAB market evidence (waiver.faab_market.v1): what this league has actually paid on waivers, with explicit samples.

A pure transformation of persisted, source-faithful Sleeper transaction weeks (GET /v1/league/{league_id}/transactions/{week},
stored by refresh_sleeper_transactions.py) plus the live league, users, rosters and player catalog the Waivers page already
loads. No network or database access and no writes. Descriptive only (INFORMATIONAL_ONLY): it never changes an ADD, DROP,
MONITOR, HOLD or PASS decision and never produces a bid amount, bid range, winning estimate, probability or demand score.

Sleeper semantics relied on, proven on this league's 2026 weeks 1-11:
- a waiver transaction is one manager's claim: one roster, one added player, an integer settings.waiver_bid, settings.seq (its
  processing order in the waiver run) and a provider outcome note in metadata.notes; free-agent adds carry no bid;
- returned claims are processed (complete or failed); unprocessed claims are not returned, so an open week is never history;
- a transaction keeps the week (leg) it was created in, and every claim in one waiver run shares one status_updated time;
- completed bids are what was charged (they sum to each roster's waiver_budget_used); failed bids are not charged.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from math import isfinite
from statistics import median
from typing import Any, Mapping, Sequence

MARKET_CONTRACT_ID = "waiver.faab_market.v1"
SOURCE = "Sleeper API"
ENDPOINT = "GET https://api.sleeper.app/v1/league/{league_id}/transactions/{week}"
STORAGE = "sleeper_api_snapshots (resource type 'transactions'; one row per league, season and week)"
REFRESH_COMMAND = "python refresh_sleeper_transactions.py"
POSITIONS = ("QB", "RB", "WR", "TE", "K", "DEF")
RECOMMENDATION_IMPACT = "INFORMATIONAL_ONLY"
NOT_A_BID = "Historical league evidence only; not a recommended bid."
LOST_NOTE = "This player was claimed by another owner."
ROSTER_LIMIT_NOTE = "Unfortunately, your roster will have too many players after this transaction."
STATE_LABELS = {"AVAILABLE": "MARKET HISTORY AVAILABLE", "PARTIAL": "PARTIAL MARKET HISTORY", "UNAVAILABLE": "MARKET COVERAGE BLOCKED",
                "CONTRADICTORY": "MARKET COVERAGE BLOCKED", "NOT_APPLICABLE": "NOT APPLICABLE"}
CONTEST_LABELS = {"CONTESTED": "CONTESTED CLAIM", "UNCONTESTED": "UNCONTESTED CLAIM", "OTHER_CLAIMS_ROSTER_LIMIT": "OTHER CLAIMS FAILED FOR ROSTER LIMITS",
                  "NO_COMPLETED_CLAIM": "NO CLAIM COMPLETED", "UNVERIFIED": "CONTEST GROUPING UNVERIFIED"}
FAILED_REASON_TEXT = {"LOST_TO_ANOTHER_TEAM": "lost to another team's claim", "OWN_OTHER_CLAIM_WON": "the same team's other claim won",
                      "ROSTER_LIMIT": "roster limit", "WINNER_NOT_IN_GROUP": "winning claim not in this waiver run's records",
                      "UNRECOGNIZED": "reason not recognized"}
GROUP_RULE = ("Claims are grouped only when they are for the same Sleeper player in the same league, season and week and were processed in the "
              "same waiver run (identical Sleeper status_updated time). A competing claim is another team's failed claim that Sleeper marks as "
              "claimed by another owner; claims that failed for roster limits did not compete on bid.")
TIEBREAK_LIMITATION = "Sleeper's transaction records do not publish the tiebreak rule: when bids tie, the record shows which claim won, not why."
VERIFIED_WEEK_STATES = ("FINAL", "CLOSED")


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def parse_bid(value: Any, budget: Any = None) -> tuple[str, int | None]:
    """VERIFIED only for a whole, finite, non-negative FAAB amount within a known league budget; a missing bid is never zero.

    A string must be plain digits, checked before conversion so nothing is rounded. Without a valid league budget an otherwise
    valid amount is BUDGET_UNVERIFIED, because "within the budget" cannot be checked.
    """
    if value is None:
        return "MISSING", None
    if isinstance(value, bool):
        return "INVALID", None
    if isinstance(value, str):
        if not re.fullmatch(r"\s*\d+\s*", value):
            return "INVALID", None
        value = int(value)
    elif isinstance(value, float):
        if not isfinite(value) or not value.is_integer():
            return "INVALID", None
        value = int(value)
    if not isinstance(value, int) or value < 0:
        return "INVALID", None
    if _int(budget) is None or budget < 0:
        return "BUDGET_UNVERIFIED", None
    return ("INVALID", None) if value > budget else ("VERIFIED", value)


def _ms(value: Any) -> int | None:
    return value if _int(value) is not None and value >= 0 else None


def _iso(ms: int | None) -> str | None:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat() if ms is not None else None


def _retrieved_ms(value: Any) -> int | None:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    value = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return int(value.timestamp() * 1000)


def money(value: Any) -> str:
    return f"${value:g}" if isinstance(value, (int, float)) and not isinstance(value, bool) else "unavailable"


def distribution(values: Sequence[int]) -> dict[str, Any]:
    """Observed bids only: the median is the midpoint; N is always published and nothing is shown for an empty population."""
    values = sorted(values)
    if not values:
        return {"n": 0, "sample": "NO_SAMPLE", "min": None, "median": None, "max": None, "text": "no observed bids"}
    mid = median(values)
    mid = int(mid) if float(mid).is_integer() else mid
    if len(values) == 1:
        return {"n": 1, "sample": "SINGLE_OBSERVATION", "min": values[0], "median": mid, "max": values[0], "text": f"{money(values[0])} (N=1, single observation)"}
    return {"n": len(values), "sample": "MULTIPLE_OBSERVATIONS", "min": values[0], "median": mid, "max": values[-1],
            "text": f"{money(values[0])}–{money(values[-1])}, median {money(mid)} (N={len(values)})"}


def _catalog_identity(catalog: Mapping[str, Any] | None, player_id: str | None) -> tuple[str | None, str | None]:
    record = (catalog or {}).get(str(player_id)) if player_id else None
    if not isinstance(record, dict):
        return None, None
    position = str(record.get("position") or "").upper()
    position = "DEF" if position in {"DST", "D/ST"} else position
    name = record.get("full_name") or " ".join(str(record.get(key)) for key in ("first_name", "last_name") if record.get(key)) or None
    return (position if position in POSITIONS else None), name


def _outcome(status: Any, note: Any) -> str:
    if status == "complete":
        return "COMPLETED"
    if status == "pending":
        return "PENDING"
    if status == "failed":
        return {LOST_NOTE: "CLAIMED_BY_ANOTHER", ROSTER_LIMIT_NOTE: "ROSTER_LIMIT"}.get(note, "UNRECOGNIZED")
    return "UNRECOGNIZED_STATUS"


def normalize_transaction(raw: Any, *, week: int, catalog: Mapping[str, Any] | None = None, budget: Any = None) -> dict[str, Any] | None:
    """One source transaction with exact Sleeper IDs; None for a record without a usable transaction_id. Nothing is invented."""
    if not isinstance(raw, dict):
        return None
    transaction_id = raw.get("transaction_id")
    if isinstance(transaction_id, bool) or not isinstance(transaction_id, (str, int)) or not str(transaction_id).strip():
        return None
    adds = raw.get("adds") if isinstance(raw.get("adds"), dict) else {}
    drops = raw.get("drops") if isinstance(raw.get("drops"), dict) else {}
    roster_ids = [value for value in raw.get("roster_ids") or [] if _int(value) is not None] if isinstance(raw.get("roster_ids"), list) else []
    settings = raw.get("settings") if isinstance(raw.get("settings"), dict) else {}
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    claim = {"transaction_id": str(transaction_id), "week": week, "leg": raw.get("leg"), "type": raw.get("type"), "status": raw.get("status"),
             "created_ms": _ms(raw.get("created")), "status_updated_ms": _ms(raw.get("status_updated")),
             "created_at": _iso(_ms(raw.get("created"))), "status_updated_at": _iso(_ms(raw.get("status_updated"))),
             "roster_ids": roster_ids, "roster_id": roster_ids[0] if len(roster_ids) == 1 else None, "creator": raw.get("creator"),
             "adds": {str(key): value for key, value in adds.items()}, "drops": {str(key): value for key, value in drops.items()},
             "faab_transfers": len(raw.get("waiver_budget")) if isinstance(raw.get("waiver_budget"), list) else 0,
             "canonical": json.dumps(raw, sort_keys=True, default=str)}
    if raw.get("type") != "waiver":
        return {**claim, "bid_state": "NOT_APPLICABLE", "bid": None}
    bid_state, bid = parse_bid(settings.get("waiver_bid"), budget)
    attributed = len(claim["adds"]) == 1 and claim["roster_id"] is not None and all(_int(value) == claim["roster_id"] for value in claim["adds"].values())
    player_id = next(iter(claim["adds"])) if attributed else None
    position, name = _catalog_identity(catalog, player_id)
    note = metadata.get("notes") if isinstance(metadata.get("notes"), str) else None
    return {**claim, "bid_state": bid_state, "bid": bid, "seq": _int(settings.get("seq")), "note": note, "outcome": _outcome(raw.get("status"), note),
            "attribution": "VERIFIED" if attributed else "UNVERIFIED", "player_id": player_id, "player": name or player_id,
            "position": position, "position_state": "RESOLVED" if position else "UNAVAILABLE"}


def _teams(users: Sequence[Mapping[str, Any]] | None, rosters: Sequence[Mapping[str, Any]] | None) -> dict[int, str]:
    """Roster ID to the fantasy team label, using the app's convention: team name, then Sleeper display name, then Roster N."""
    users_by_id = {str(user.get("user_id")): user for user in users or [] if isinstance(user, dict) and user.get("user_id")}
    labels = {}
    for roster in rosters or []:
        roster_id = _int((roster or {}).get("roster_id")) if isinstance(roster, dict) else None
        if roster_id is None:
            continue
        user = users_by_id.get(str(roster.get("owner_id"))) or {}
        labels[roster_id] = (user.get("metadata") or {}).get("team_name") or user.get("display_name") or f"Roster {roster_id}"
    return labels


def _weeks_text(weeks: Sequence[int]) -> str:
    weeks, spans = sorted(weeks), []
    for week in weeks:
        if spans and week == spans[-1][1] + 1:
            spans[-1][1] = week
        else:
            spans.append([week, week])
    return ", ".join(f"{start}–{end}" if start != end else f"{start}" for start, end in spans)


def _team(teams: Mapping[int, str], roster_id: Any) -> str:
    return teams.get(roster_id) or (f"Roster {roster_id}" if roster_id is not None else "an unidentified team")


def _bid_text(claim: Mapping[str, Any]) -> str:
    return money(claim["bid"]) if claim.get("bid_state") == "VERIFIED" else "bid unavailable"


def _failed_reason(claim: Mapping[str, Any], winner: Mapping[str, Any] | None) -> str:
    if claim["outcome"] == "ROSTER_LIMIT":
        return "ROSTER_LIMIT"
    if claim["outcome"] != "CLAIMED_BY_ANOTHER":
        return "UNRECOGNIZED"
    if winner is None:
        return "WINNER_NOT_IN_GROUP"
    return "OWN_OTHER_CLAIM_WON" if winner["roster_id"] == claim["roster_id"] else "LOST_TO_ANOTHER_TEAM"


def _group_view(key: tuple, claims: list[dict[str, Any]], teams: Mapping[int, str]) -> dict[str, Any]:
    """One waiver run's claims on one player. CONTESTED only when another team's claim lost to the completed claim."""
    week, player_id, processed_ms = key
    claims = sorted(claims, key=lambda claim: (claim["seq"] if claim["seq"] is not None else 10 ** 6, claim["transaction_id"]))
    completed = [claim for claim in claims if claim["status"] == "complete"]
    winner = completed[0] if len(completed) == 1 else None
    for claim in claims:
        if claim["status"] == "failed":
            claim["failed_reason"] = _failed_reason(claim, winner)
    others = [claim for claim in claims if claim["status"] == "failed" and winner is not None and claim["roster_id"] != winner["roster_id"]]
    competing = [claim for claim in others if claim["failed_reason"] == "LOST_TO_ANOTHER_TEAM"]
    unknown = [claim for claim in others if claim["failed_reason"] not in ("LOST_TO_ANOTHER_TEAM", "ROSTER_LIMIT")]
    if len(completed) > 1:
        state = "UNVERIFIED"
    elif winner is None:
        state = "NO_COMPLETED_CLAIM"
    else:
        state = "CONTESTED" if competing else "UNVERIFIED" if unknown else "OTHER_CLAIMS_ROSTER_LIMIT" if others else "UNCONTESTED"
    competing_bids = [claim["bid"] for claim in competing if claim["bid_state"] == "VERIFIED"]
    highest = max(competing_bids) if competing_bids else None
    tie = highest is not None and winner is not None and winner["bid_state"] == "VERIFIED" and highest == winner["bid"]
    first = claims[0]
    name, position = first["player"], first["position"]
    failed = [{"roster_id": claim["roster_id"], "team": _team(teams, claim["roster_id"]), "bid": claim["bid"], "bid_state": claim["bid_state"],
               "reason": claim["failed_reason"], "reason_text": FAILED_REASON_TEXT[claim["failed_reason"]]} for claim in claims if claim["status"] == "failed"]
    if state == "CONTESTED":
        detail = f"{_team(teams, winner['roster_id'])} completed at {_bid_text(winner)}; "
        detail += (f"1 competing claim from another team failed at {money(highest)}" if len(competing) == 1 else
                   f"{len(competing)} competing claims from other teams failed (highest observed failed competing bid {money(highest)})")
        detail += "; a failed bid tied the completed bid" if tie else ""
    elif state == "UNCONTESTED":
        detail = f"{_team(teams, winner['roster_id'])} completed at {_bid_text(winner)}; no competing claim from another team in this waiver run"
    elif state == "OTHER_CLAIMS_ROSTER_LIMIT":
        detail = f"{_team(teams, winner['roster_id'])} completed at {_bid_text(winner)}; other teams' claims failed for roster limits, not on bid"
    elif state == "NO_COMPLETED_CLAIM":
        detail = "no claim completed in this waiver run"
    else:
        detail = "the competing claims could not be verified from the provider records"
    text = (f"Week {week} · {name} ({position or 'position unavailable'}) · {len(claims)} claim{'s' if len(claims) != 1 else ''}: {detail}.")
    return {"key": f"{week}:{player_id}:{processed_ms}", "week": week, "player_id": player_id, "player": name, "position": position,
            "processed_at": _iso(processed_ms), "claims": len(claims), "teams": len({claim["roster_id"] for claim in claims}), "detail": detail,
            "completed_count": len(completed), "transaction_ids": [claim["transaction_id"] for claim in claims],
            "state": state, "label": CONTEST_LABELS[state], "completed": ({"roster_id": winner["roster_id"], "team": _team(teams, winner["roster_id"]),
                                                                          "bid": winner["bid"], "bid_state": winner["bid_state"]} if winner else None),
            "failed": failed, "competing_claims": len(competing), "highest_failed_competing_bid": highest, "tie": tie, "text": text}


def _summary(claims: Sequence[Mapping[str, Any]], groups: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    completed = [claim for claim in claims if claim["status"] == "complete"]
    failed = [claim for claim in claims if claim["status"] == "failed"]
    states = Counter(group["state"] for group in groups)
    ungrouped_completed = len(completed) - sum(group["completed_count"] for group in groups)
    return {
        "waiver_claims": len(claims), "completed": len(completed), "failed": len(failed),
        "pending": sum(claim["status"] == "pending" for claim in claims),
        "unrecognized_status": sum(claim["outcome"] == "UNRECOGNIZED_STATUS" for claim in claims),
        "verified_bids": sum(claim["bid_state"] == "VERIFIED" for claim in claims),
        "missing_bids": sum(claim["bid_state"] == "MISSING" for claim in claims), "invalid_bids": sum(claim["bid_state"] == "INVALID" for claim in claims),
        "budget_unverified_bids": sum(claim["bid_state"] == "BUDGET_UNVERIFIED" for claim in claims),
        "zero_bid_claims": sum(claim["bid_state"] == "VERIFIED" and claim["bid"] == 0 for claim in claims),
        "zero_bid_completed": sum(claim["bid_state"] == "VERIFIED" and claim["bid"] == 0 for claim in completed),
        "attribution_unverified": sum(claim["attribution"] != "VERIFIED" for claim in claims),
        "completed_bids": distribution([claim["bid"] for claim in completed if claim["bid_state"] == "VERIFIED"]),
        "failed_bids": distribution([claim["bid"] for claim in failed if claim["bid_state"] == "VERIFIED"]),
        "lost_bids": distribution([claim["bid"] for claim in failed if claim.get("failed_reason") == "LOST_TO_ANOTHER_TEAM" and claim["bid_state"] == "VERIFIED"]),
        "failed_reasons": dict(Counter(claim.get("failed_reason") or "WINNER_NOT_IN_GROUP" for claim in failed)),
        "failed_reasons_text": ", ".join(f"{count} {FAILED_REASON_TEXT[reason]}" for reason, count in
                                         Counter(claim.get("failed_reason") or "WINNER_NOT_IN_GROUP" for claim in failed).most_common()) or "none",
        "contested": states["CONTESTED"], "uncontested": states["UNCONTESTED"], "other_claims_roster_limit": states["OTHER_CLAIMS_ROSTER_LIMIT"],
        "no_completed_claim": states["NO_COMPLETED_CLAIM"],
        "contest_unverified": sum(group["completed_count"] for group in groups if group["state"] == "UNVERIFIED") + ungrouped_completed,
        "contested_bids": distribution([group["completed"]["bid"] for group in groups if group["state"] == "CONTESTED" and group["completed"]["bid_state"] == "VERIFIED"]),
        "uncontested_bids": distribution([group["completed"]["bid"] for group in groups if group["state"] == "UNCONTESTED" and group["completed"]["bid_state"] == "VERIFIED"]),
        "tied_groups": sum(group["tie"] for group in groups),
    }


def _contest_text(summary: Mapping[str, Any]) -> str:
    parts = [f"{summary['contested']} contested", f"{summary['uncontested']} uncontested"]
    if summary["other_claims_roster_limit"]:
        parts.append(f"{summary['other_claims_roster_limit']} with other claims failing only for roster limits")
    if summary["contest_unverified"]:
        parts.append(f"{summary['contest_unverified']} not verifiable")
    return ", ".join(parts)


def _budget_context(league: Mapping[str, Any], users, rosters, owner_balance: Mapping[str, Any] | None, teams: Mapping[int, str],
                    spend: Mapping[int, int], spend_weeks: Sequence[int], spend_complete: bool) -> dict[str, Any]:
    """Current Sleeper budgets per team, using the page's existing contract: league waiver_budget minus each roster's waiver_budget_used."""
    settings = league.get("settings") or {}
    budget = _int(settings.get("waiver_budget"))
    base = {"state": "UNAVAILABLE", "budget": budget, "teams": [], "verified": 0, "total": _int(league.get("total_rosters")), "distribution": None,
            "owner": None, "spend_reconciliation": None, "reason": "League FAAB budget settings are missing or inconsistent."}
    if budget is None or budget < 0 or not isinstance(rosters, list):
        return base
    owner_ids = {str(user.get("user_id")) for user in users or [] if isinstance(user, dict) and user.get("is_owner") is True and user.get("user_id")}
    entries, seen = [], set()
    for roster in rosters:
        roster_id = _int((roster or {}).get("roster_id")) if isinstance(roster, dict) else None
        if roster_id is None or roster_id in seen:
            continue
        seen.add(roster_id)
        used = _int((roster.get("settings") or {}).get("waiver_budget_used"))
        verified = used is not None and 0 <= used <= budget
        entries.append({"roster_id": roster_id, "team": _team(teams, roster_id), "is_owner": str(roster.get("owner_id")) in owner_ids and len(owner_ids) == 1,
                        "state": "VERIFIED" if verified else "UNAVAILABLE", "used": used if verified else None, "remaining": budget - used if verified else None,
                        "completed_bid_total": spend.get(roster_id, 0)})
    verified = [entry for entry in entries if entry["state"] == "VERIFIED"]
    total = base["total"]
    complete = total is not None and len(entries) == total == len(verified) and len(rosters) == total
    owners = [entry for entry in entries if entry["is_owner"]]
    owner = owners[0] if len(owners) == 1 else None
    owner_view = None
    if owner is not None:
        page = owner_balance or {}
        if page.get("state") != "AVAILABLE" or owner["remaining"] is None:
            reconciliation = "UNVERIFIED"
        else:
            reconciliation = "RECONCILED" if (page.get("remaining"), page.get("budget"), page.get("spent")) == (owner["remaining"], budget, owner["used"]) else "CONFLICT"
        owner_view = {**owner, "page_remaining": page.get("remaining"), "reconciliation": reconciliation}
    distribution_view = None
    if complete:
        remaining = sorted(entry["remaining"] for entry in verified)
        mid = median(remaining)
        distribution_view = {"n": len(remaining), "median_remaining": int(mid) if float(mid).is_integer() else mid, "highest_remaining": remaining[-1],
                             "lowest_remaining": remaining[0]}
    mismatched = [entry for entry in verified if entry["completed_bid_total"] != entry["used"]]
    spend_view = {"weeks": list(spend_weeks), "coverage": "COMPLETE" if spend_complete else "INCOMPLETE", "matched": len(verified) - len(mismatched),
                  "mismatched": [{"team": entry["team"], "used": entry["used"], "completed_bid_total": entry["completed_bid_total"]} for entry in mismatched],
                  "verified_teams": len(verified)}
    if spend_complete and not mismatched:
        spend_view["text"] = (f"Completed waiver bids in Weeks {_weeks_text(spend_weeks)} equal Sleeper's budget used for {len(verified)} of "
                              f"{len(verified)} verified teams.")
    else:
        spend_view["text"] = ("Completed waiver bids found in the stored weeks and Sleeper's budget used are shown separately"
                              + (f": {len(mismatched)} team{'s' if len(mismatched) != 1 else ''} differ" if mismatched else "")
                              + ("" if spend_complete else "; not every transaction week is stored") + ". Neither is adjusted.")
    state = ("CONFLICT" if owner_view and owner_view["reconciliation"] == "CONFLICT" else "AVAILABLE" if complete else "PARTIAL" if verified else "UNAVAILABLE")
    reason = {"CONFLICT": "FAAB BUDGET CONFLICT: this budget view and the page's FAAB remaining disagree, so neither is used for anything beyond display.",
              "AVAILABLE": f"All {total} team budgets are verified from the live Sleeper league.",
              "PARTIAL": f"{len(verified)} of {total if total is not None else len(entries)} team budgets are verified; no league distribution is shown.",
              "UNAVAILABLE": "No team budget could be verified."}[state]
    return {**base, "state": state, "teams": sorted(entries, key=lambda entry: (entry["remaining"] is None, -(entry["remaining"] or 0), entry["team"])),
            "verified": len(verified), "distribution": distribution_view, "owner": owner_view, "spend_reconciliation": spend_view, "reason": reason}


def _base(league_id: Any, season: Any) -> dict[str, Any]:
    return {"contract_id": MARKET_CONTRACT_ID, "state": "UNAVAILABLE", "label": STATE_LABELS["UNAVAILABLE"], "recommendation_impact": RECOMMENDATION_IMPACT,
            "source": {"provider": SOURCE, "endpoint": ENDPOINT, "storage": STORAGE, "refresh": REFRESH_COMMAND, "league_id": str(league_id or ""), "season": season},
            "season": season, "current_week": None, "through_week": None, "completeness": {"state": "UNAVAILABLE", "weeks": {}}, "blockers": [],
            "reason": None, "scope_text": None, "claims": [], "season_summary": None, "recent_summary": None, "position_summaries": {}, "groups": [],
            "players": {}, "budget_context": None, "manager_spending": [], "manager_table": [], "limitations": [], "contest_rule": GROUP_RULE, "disclaimer": NOT_A_BID}


def build_faab_market_evidence(*, league_id: Any, season: Any, league: Mapping[str, Any] | None, users: Sequence[Mapping[str, Any]] | None,
                               rosters: Sequence[Mapping[str, Any]] | None, history: Mapping[str, Any] | None, catalog: Mapping[str, Any] | None,
                               owner_balance: Mapping[str, Any] | None = None, mode: str = "LIVE") -> dict[str, Any]:
    """waiver.faab_market.v1 for one league and season; every dollar figure names its population and N."""
    result = _base(league_id, season)

    def blocked(state, blocker, reason):
        return {**result, "state": state, "label": STATE_LABELS[state], "blockers": [blocker], "reason": reason,
                "completeness": {**result["completeness"], "state": "UNAVAILABLE" if state != "CONTRADICTORY" else "CONTRADICTORY"}}

    league = league if isinstance(league, dict) else {}
    settings = league.get("settings") or {}
    if mode != "LIVE":
        return blocked("NOT_APPLICABLE", "LIVE_LEAGUE_ONLY", "League FAAB history is shown only for the live Sleeper league.")
    if settings.get("waiver_type") != 2:
        return blocked("NOT_APPLICABLE", "LEAGUE_NOT_FAAB", "The league is not verified as FAAB-based, so bid history is not applicable.")
    try:
        league_season = int(league.get("season"))
    except (TypeError, ValueError):
        league_season = None
    if league_season is None or league_season != season:
        return blocked("UNAVAILABLE", "SEASON_MISMATCH", f"The live league season ({league.get('season')}) does not match the page season ({season}).")
    if league.get("league_id") is not None and str(league.get("league_id")) != str(league_id):
        return blocked("UNAVAILABLE", "LEAGUE_MISMATCH", "The live league does not match the configured league.")
    current, start, budget = _int(settings.get("leg")), _int(settings.get("start_week")), _int(settings.get("waiver_budget"))
    if current is None or start is None or current < start:
        return blocked("UNAVAILABLE", "CURRENT_WEEK_UNVERIFIED", "Sleeper did not report the league's current transaction week, so completed weeks cannot be identified.")
    result.update(current_week=current)
    teams = _teams(users, rosters)
    if not isinstance(history, dict) or history.get("state") != "READ":
        return blocked("UNAVAILABLE", "TRANSACTION_HISTORY_UNREAD", "Stored transaction history could not be read for this page view.")

    weeks: dict[int, dict[str, Any]] = {}
    mismatched_rows = 0
    for row in history.get("rows") or []:
        week = _int((row or {}).get("week")) if isinstance(row, dict) else None
        if week is None:
            continue
        if str(row.get("league_id", league_id)) != str(league_id) or row.get("season", season) != season:
            mismatched_rows += 1
            continue
        payload, fetched_ms = row.get("payload"), _retrieved_ms(row.get("fetched_at"))
        view = {"week": week, "retrieved_at": _iso(fetched_ms), "fetched_ms": fetched_ms, "transactions": [], "malformed": 0, "problem": None}
        if not isinstance(payload, list):
            view["problem"] = "The stored payload is not a transaction list."
        else:
            for raw in payload:
                transaction = normalize_transaction(raw, week=week, catalog=catalog, budget=budget)
                if transaction is None:
                    view["malformed"] += 1
                elif transaction["leg"] != week:
                    view["problem"] = f"A stored Week {week} transaction belongs to week {transaction['leg']}."
                else:
                    view["transactions"].append(transaction)
        if fetched_ms is None and view["problem"] is None:
            view["problem"] = "The stored week has no retrieval time."
        weeks[week] = view

    by_id: dict[str, dict[str, Any]] = {}
    conflicts, duplicates = set(), 0
    for view in weeks.values():
        kept = []
        for transaction in view["transactions"]:
            prior = by_id.get(transaction["transaction_id"])
            if prior is None:
                by_id[transaction["transaction_id"]] = transaction
                kept.append(transaction)
            elif prior["canonical"] == transaction["canonical"]:
                duplicates += 1
            else:
                conflicts.add(transaction["transaction_id"])
        view["transactions"] = kept
    first_created: dict[int, int] = {}
    for view in weeks.values():
        if view["problem"] is None:
            for transaction in view["transactions"]:
                if transaction["created_ms"] is not None:
                    first_created[transaction["leg"]] = min(first_created.get(transaction["leg"], transaction["created_ms"]), transaction["created_ms"])

    def moved_past(week, fetched_ms, gap):
        # Sleeper had already opened a later week when this week was retrieved: a later-week transaction existed by then.
        return any(leg >= week + gap and created <= fetched_ms for leg, created in first_created.items())

    states = {}
    for week in range(start, current + 1):
        view = weeks.get(week)
        if view is None:
            states[week] = "MISSING" if week < current else "OPEN"
        elif view["problem"]:
            states[week] = "INVALID"
        elif week == current:
            states[week] = "OPEN"
        else:
            states[week] = "FINAL" if moved_past(week, view["fetched_ms"], 2) else "CLOSED" if moved_past(week, view["fetched_ms"], 1) else "OPEN_AT_RETRIEVAL"
    expected = list(range(start, current))
    verified = [week for week in expected if states[week] in VERIFIED_WEEK_STATES]
    through = None
    for week in expected:
        if states[week] not in VERIFIED_WEEK_STATES:
            break
        through = week
    latest = history.get("latest_refresh") if isinstance(history.get("latest_refresh"), dict) else None
    refresh_failed = latest is not None and latest.get("status") != "success"
    invalid = [week for week in expected if states[week] == "INVALID"]
    if conflicts or invalid:
        completeness = "CONTRADICTORY"
    elif not verified:
        completeness = "UNAVAILABLE"
    elif len(verified) == len(expected) and not refresh_failed:
        completeness = "COMPLETE"
    else:
        completeness = "PARTIAL"
    failed_weeks = sorted(int(week) for week, entry in (((latest or {}).get("resources") or {}).get("weeks") or {}).items()
                          if isinstance(entry, dict) and entry.get("ok") is False and str(week).isdigit())
    retrieved = [weeks[week]["retrieved_at"] for week in verified]
    open_view = weeks.get(current)
    open_claims = [transaction for transaction in (open_view or {}).get("transactions", []) if transaction["type"] == "waiver"] if open_view and not open_view["problem"] else []
    result["completeness"] = {
        "state": completeness, "expected_weeks": expected, "verified_weeks": verified, "weeks": {week: states[week] for week in sorted(states)},
        "final_weeks": [week for week in verified if states[week] == "FINAL"], "closed_not_final_weeks": [week for week in verified if states[week] == "CLOSED"],
        "missing_weeks": [week for week in expected if states[week] == "MISSING"], "open_at_retrieval_weeks": [week for week in expected if states[week] == "OPEN_AT_RETRIEVAL"],
        "invalid_weeks": invalid, "empty_verified_weeks": [week for week in verified if not weeks[week]["transactions"]],
        "conflicting_transaction_ids": sorted(conflicts), "duplicates_removed": duplicates, "mismatched_rows": mismatched_rows,
        "malformed_records": sum(view["malformed"] for view in weeks.values()),
        "open_week": {"week": current, "stored": open_view is not None, "processed_claims": len(open_claims), "retrieved_at": (open_view or {}).get("retrieved_at")},
        "latest_refresh": ({"status": latest.get("status"), "started_at": _iso(_retrieved_ms(latest.get("started_at"))), "completed_at": _iso(_retrieved_ms(latest.get("completed_at"))),
                            "failed_weeks": failed_weeks, "error": latest.get("error")} if latest else None),
        "oldest_retrieval": min(retrieved) if retrieved else None, "latest_retrieval": max(retrieved) if retrieved else None,
    }
    final, closed = result["completeness"]["final_weeks"], result["completeness"]["closed_not_final_weeks"]
    pieces = [f"final: Week{'s' if len(final) != 1 else ''} {_weeks_text(final)}" if final else "",
              f"closed, not yet final: Week{'s' if len(closed) != 1 else ''} {_weeks_text(closed)}" if closed else ""]
    gaps = [f"{label} Week{'s' if len(values) != 1 else ''} {_weeks_text(values)}" for label, values in
            (("missing:", result["completeness"]["missing_weeks"]), ("retrieved before Sleeper closed it:", result["completeness"]["open_at_retrieval_weeks"]),
             ("invalid:", invalid)) if values]
    result["completeness"]["text"] = (f"{len(verified)} of {len(expected)} closed week{'s' if len(expected) != 1 else ''} verified"
                                      + (f" ({'; '.join(piece for piece in pieces if piece)})" if any(pieces) else "")
                                      + (f"; {'; '.join(gaps)}" if gaps else "") + f"; Week {current} is open.")
    if latest:
        refresh = result["completeness"]["latest_refresh"]
        refresh["text"] = (f"Latest refresh attempt: {latest.get('status')}" + (f", completed {refresh['completed_at']}" if refresh["completed_at"] else
                                                                               f", started {refresh['started_at']} and not finished")
                           + (f"; failed for Week{'s' if len(failed_weeks) != 1 else ''} {_weeks_text(failed_weeks)}" if failed_weeks else "") + ".")
    result["through_week"] = through
    if completeness == "CONTRADICTORY":
        detail = (f"transaction IDs {', '.join(sorted(conflicts)[:3])} have conflicting stored records" if conflicts else
                  "; ".join(weeks[week]["problem"] for week in invalid))
        return {**result, "state": "CONTRADICTORY", "label": STATE_LABELS["CONTRADICTORY"], "blockers": ["TRANSACTION_HISTORY_CONTRADICTORY"],
                "reason": f"Stored transaction history is contradictory ({detail}), so no bid history is published."}
    if completeness == "UNAVAILABLE":
        reason = ("No completed transaction week exists yet this season." if not expected else
                  f"No transaction week is stored that Sleeper had closed when it was retrieved; run {REFRESH_COMMAND}.")
        return {**result, "state": "UNAVAILABLE", "label": STATE_LABELS["UNAVAILABLE"], "blockers": ["NO_VERIFIED_TRANSACTION_WEEK"], "reason": reason}

    claims = [transaction for week in verified for transaction in weeks[week]["transactions"] if transaction["type"] == "waiver"]
    others = [transaction for week in verified for transaction in weeks[week]["transactions"] if transaction["type"] != "waiver"]
    grouped: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for claim in claims:
        if claim["attribution"] == "VERIFIED" and claim["status"] in ("complete", "failed") and claim["status_updated_ms"] is not None:
            grouped[(claim["week"], claim["player_id"], claim["status_updated_ms"])].append(claim)
    groups = sorted((_group_view(key, members, teams) for key, members in grouped.items()), key=lambda group: (group["week"], group["processed_at"] or "", group["player"] or ""))
    for claim in claims:
        if claim["status"] == "failed" and "failed_reason" not in claim:
            claim["failed_reason"] = _failed_reason(claim, None)
    scope = f"Weeks {start}–{through}" if completeness == "COMPLETE" else f"across {len(verified)} verified transaction week{'s' if len(verified) != 1 else ''} (Weeks {_weeks_text(verified)})"
    season_summary = _summary(claims, groups)
    season_summary.update(free_agent_adds=sum(t["type"] == "free_agent" and t["status"] == "complete" and bool(t["adds"]) for t in others),
                          trades=sum(t["type"] == "trade" for t in others), other_types=sum(t["type"] not in ("free_agent", "trade") for t in others),
                          transactions=len(claims) + len(others), faab_transfers=sum(t["faab_transfers"] for t in [*claims, *others]))
    positions = {}
    for position in POSITIONS:
        members = [claim for claim in claims if claim["attribution"] == "VERIFIED" and claim["position"] == position]
        summary = _summary(members, [group for group in groups if group["position"] == position])
        summary["text"] = (f"{position} ({scope}): {summary['completed']} completed claim{'s' if summary['completed'] != 1 else ''}"
                           + (f", {summary['completed_bids']['text']}" if summary["completed_bids"]["n"] else "")
                           + f"; {_contest_text(summary)}; {summary['failed']} failed claim{'s' if summary['failed'] != 1 else ''}.")
        positions[position] = {"position": position, **summary}
    players: dict[str, dict[str, Any]] = {}
    for group in groups:
        entry = players.setdefault(group["player_id"], {"player_id": group["player_id"], "player": group["player"], "position": group["position"], "groups": []})
        entry["groups"].append(group)
    for entry in players.values():
        entry["claims"] = sum(group["claims"] for group in entry["groups"])
        entry["completed"] = sum(1 for group in entry["groups"] if group["completed"])
    latest_week = max(verified)
    recent = _summary([claim for claim in claims if claim["week"] == latest_week], [group for group in groups if group["week"] == latest_week])
    recent.update(week=latest_week, text=(f"Week {latest_week}: {recent['completed']} completed claim{'s' if recent['completed'] != 1 else ''}"
                                          + (f" ({recent['completed_bids']['text']})" if recent["completed_bids"]["n"] else "")
                                          + f", {recent['failed']} failed; {_contest_text(recent)}."))
    spend: dict[int, int] = defaultdict(int)
    spend_weeks = sorted(week for week, view in weeks.items() if start <= week <= current and not view["problem"])
    for week in spend_weeks:
        for transaction in weeks[week]["transactions"]:
            if transaction["type"] == "waiver" and transaction["status"] == "complete" and transaction["bid_state"] == "VERIFIED" and transaction["roster_id"] is not None:
                spend[transaction["roster_id"]] += transaction["bid"]
    budget_context = _budget_context(league, users, rosters, owner_balance, teams, spend, spend_weeks, spend_weeks == list(range(start, current + 1)))
    spending = []
    for roster_id in sorted({claim["roster_id"] for claim in claims if claim["roster_id"] is not None} | {entry["roster_id"] for entry in budget_context["teams"]}):
        won = [claim["bid"] for claim in claims if claim["roster_id"] == roster_id and claim["status"] == "complete" and claim["bid_state"] == "VERIFIED"]
        spending.append({"roster_id": roster_id, "team": _team(teams, roster_id), "completed_claims": sum(claim["roster_id"] == roster_id and claim["status"] == "complete" for claim in claims),
                         "completed_bid_total": sum(won), "completed_bids": distribution(won), "largest_completed_bid": max(won) if won else None})
    spent_by_roster = {entry["roster_id"]: entry for entry in spending}
    manager_table = [{"roster_id": team["roster_id"], "team": team["team"], "is_owner": team["is_owner"], "remaining": team["remaining"], "used": team["used"],
                      "completed_claims": spent_by_roster.get(team["roster_id"], {}).get("completed_claims", 0),
                      "largest_completed_bid": spent_by_roster.get(team["roster_id"], {}).get("largest_completed_bid")} for team in budget_context["teams"]]
    limitations = []
    if open_view is not None and not open_view["problem"]:
        limitations.append(f"Week {current} is still open on Sleeper: its waiver run has not been processed and unprocessed claims are not published, so its "
                           f"{len(open_claims)} processed claim{'s' if len(open_claims) != 1 else ''} so far {'are' if len(open_claims) != 1 else 'is'} not in this history.")
    else:
        limitations.append(f"Week {current} is still open on Sleeper; its claims are not part of this history.")
    late = sorted({claim["week"] for claim in claims if claim["status_updated_ms"] is not None and first_created.get(claim["week"] + 1) is not None
                   and claim["status_updated_ms"] > first_created[claim["week"] + 1]})
    unfinished = result["completeness"]["closed_not_final_weeks"]
    if current - 1 in unfinished:
        limitations.append(f"Week {current - 1} is closed on Sleeper, but a claim created in Week {current - 1} can still be processed after the week closes"
                           + (f" (this season Sleeper did so in Week{'s' if len(late) != 1 else ''} {_weeks_text(late)})" if late else "")
                           + f"; refresh after the Week {current} waiver run to make Week {current - 1} final.")
    older = [week for week in unfinished if week < current - 1]
    if older:
        limitations.append(f"Week{'s' if len(older) != 1 else ''} {_weeks_text(older)} {'were' if len(older) != 1 else 'was'} stored before the following week "
                           f"closed, so a new refresh will make {'them' if len(older) != 1 else 'it'} final.")
    if season_summary["tied_groups"]:
        limitations.append(TIEBREAK_LIMITATION)
    if season_summary["faab_transfers"]:
        limitations.append(f"{season_summary['faab_transfers']} trade record(s) moved FAAB between teams, so budget used can differ from completed bids.")
    unresolved = sum(claim["attribution"] == "VERIFIED" and claim["position"] is None for claim in claims)
    if unresolved:
        limitations.append(f"{unresolved} claim{'s' if unresolved != 1 else ''} could not be matched to a current Sleeper position; they count in the season "
                           "totals and the claim history, never in a position history.")
    if season_summary["attribution_unverified"]:
        limitations.append(f"PLAYER ATTRIBUTION UNVERIFIED for {season_summary['attribution_unverified']} claim(s) without exactly one added player; they count in the season totals only.")
    if result["completeness"]["malformed_records"]:
        limitations.append(f"{result['completeness']['malformed_records']} stored record(s) without a transaction ID were excluded.")
    if season_summary["budget_unverified_bids"]:
        limitations.append(f"The league FAAB budget is not published, so {season_summary['budget_unverified_bids']} bid(s) cannot be verified; those claims are "
                           "counted without bid figures.")
    if season_summary["missing_bids"] or season_summary["invalid_bids"]:
        limitations.append(f"{season_summary['missing_bids'] + season_summary['invalid_bids']} claim(s) without a valid bid are counted as claims but excluded from bid figures.")
    limitations.append("Sleeper does not publish cancelled or unprocessed claims, so they cannot be counted.")
    limitations.append("Free-agent adds carry no bid and are excluded from every bid figure.")
    if completeness == "COMPLETE":
        reason = (f"Completed market through Week {through}: all {len(expected)} closed week{'s' if len(expected) != 1 else ''} (Weeks {start}–{through}) "
                  "were retrieved after Sleeper closed them.")
    else:
        problems = []
        if result["completeness"]["missing_weeks"]:
            problems.append(f"Week{'s' if len(result['completeness']['missing_weeks']) != 1 else ''} {_weeks_text(result['completeness']['missing_weeks'])} not stored")
        early = result["completeness"]["open_at_retrieval_weeks"]
        if early:
            problems.append(f"Week{'s' if len(early) != 1 else ''} {_weeks_text(early)} retrieved before Sleeper closed {'them' if len(early) != 1 else 'it'}")
        if refresh_failed:
            problems.append(f"the latest refresh attempt ({latest.get('status')}) could not reverify completeness"
                            + (f"; it failed for Week{'s' if len(failed_weeks) != 1 else ''} {_weeks_text(failed_weeks)}" if failed_weeks else ""))
        reason = f"Partial market history {scope}: {'; '.join(problems)}. Showing the last verified snapshots; run {REFRESH_COMMAND}."
    return {**result, "state": "AVAILABLE" if completeness == "COMPLETE" else "PARTIAL", "label": STATE_LABELS["AVAILABLE" if completeness == "COMPLETE" else "PARTIAL"],
            "blockers": [] if completeness == "COMPLETE" else ["TRANSACTION_HISTORY_PARTIAL"], "reason": reason, "scope_text": scope,
            "claims": [{key: value for key, value in claim.items() if key != "canonical"} for claim in claims], "season_summary": season_summary, "recent_summary": recent, "position_summaries": positions, "groups": groups, "players": players,
            "budget_context": budget_context, "manager_spending": spending, "manager_table": manager_table, "limitations": limitations}


def market_context(market: Mapping[str, Any] | None, *, player_id: Any, position: Any, player: Any = None, rostered: bool = False,
                   monitor: bool = False) -> dict[str, Any]:
    """Exact-player history first, then same-position history, then league-wide history only when the position has no completed
    sample. The populations stay separate; nothing is combined into one number."""
    market = market or {}
    position = str(position or "").upper().replace("DST", "DEF")
    state = market.get("state")
    if state not in ("AVAILABLE", "PARTIAL"):
        reason = market.get("reason") or "League FAAB history is unavailable."
        return {"state": state or "UNAVAILABLE", "label": market.get("label") or STATE_LABELS["UNAVAILABLE"], "lines": [reason], "player_history": None}
    scope, name = market["scope_text"], player or player_id
    lines = []
    if rostered:
        lines.append(f"{name} is on a roster now; this history is informational and does not make this player available.")
    history = (market.get("players") or {}).get(str(player_id)) if player_id else None
    if history:
        events = "; ".join(f"Week {group['week']}, {group['claims']} claim{'s' if group['claims'] != 1 else ''} ({group['label'].lower()}): {group['detail']}"
                           for group in history["groups"])
        lines.append(f"Player history ({scope}): {events}.")
    else:
        lines.append(f"Player history: NO LEAGUE CLAIM HISTORY for {name} {('in ' + scope) if scope.startswith('Weeks') else scope}.")
    summary = (market.get("position_summaries") or {}).get(position)
    if summary:
        lines.append(summary["text"])
    fallback = not summary or not summary["completed_bids"]["n"]
    if fallback:
        season = market["season_summary"]
        lines.append(f"All positions ({scope}): {season['completed']} completed claims, {season['completed_bids']['text']}; {_contest_text(season)}.")
    if monitor:
        lines.append("This history does not make the move executable.")
    lines.append(NOT_A_BID)
    return {"state": state, "label": market.get("label"), "lines": lines, "player_state": "HISTORY" if history else "NO_OBSERVED_CLAIM_HISTORY",
            "player_history": history, "position_summary": summary, "league_fallback": fallback}
