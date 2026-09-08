"""F4-C cross-domain Decision Ranking Engine.

This module normalizes lineup, waiver, trade, matchup, playoff, schedule,
probability, and league-intelligence recommendations into one deterministic,
fail-closed action contract. It performs decision support only and never
submits an external transaction.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping, Sequence

VALID_CATEGORIES = {
    "lineup", "waiver", "trade", "matchup", "playoff",
    "schedule", "win_probability", "league",
}
VALID_URGENCY = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "WATCH"}
URGENCY_WEIGHT = {"CRITICAL": 100.0, "HIGH": 80.0, "MEDIUM": 55.0, "LOW": 30.0, "WATCH": 10.0}
CATEGORY_WEIGHT = {
    "lineup": 12.0,
    "waiver": 11.0,
    "matchup": 10.0,
    "trade": 8.0,
    "win_probability": 7.0,
    "playoff": 5.0,
    "schedule": 4.0,
    "league": 1.0,
}


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: Any, low: float, high: float) -> float:
    return max(low, min(high, _number(value)))


def _text(value: Any) -> str:
    return str(value or "").strip()


def _confidence(value: Any) -> tuple[str, int]:
    if isinstance(value, Mapping):
        score = round(_clamp(value.get("score"), 0, 100))
        label = _text(value.get("label")).upper()
    else:
        score = round(_clamp(value, 0, 100))
        label = ""
    if not label:
        label = "HIGH" if score >= 80 else "MEDIUM" if score >= 60 else "LOW"
    return label, score


@dataclass(frozen=True)
class DecisionAction:
    action_id: str
    category: str
    title: str
    action: str
    reason: str
    urgency: str = "MEDIUM"
    confidence_label: str = "LOW"
    confidence_score: int = 0
    expected_points_gain: float | None = None
    win_probability_gain: float | None = None
    playoff_probability_gain: float | None = None
    risk_reduction: float = 0.0
    evidence_complete: bool = True
    blockers: tuple[str, ...] = field(default_factory=tuple)
    source: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    priority_score: float = 0.0
    priority: int | None = None

    @property
    def allowed(self) -> bool:
        return self.evidence_complete and not self.blockers

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["blockers"] = list(self.blockers)
        payload["metadata"] = dict(self.metadata)
        payload["allowed"] = self.allowed
        return payload


def build_action(
    *, action_id: str, category: str, title: str, action: str, reason: str,
    urgency: str = "MEDIUM", confidence: Any = None,
    expected_points_gain: Any = None, win_probability_gain: Any = None,
    playoff_probability_gain: Any = None, risk_reduction: Any = 0,
    evidence_complete: bool = True, blockers: Iterable[str] = (),
    source: str = "", metadata: Mapping[str, Any] | None = None,
) -> DecisionAction:
    category = _text(category).lower()
    urgency = _text(urgency).upper() or "MEDIUM"
    if category not in VALID_CATEGORIES:
        raise ValueError(f"unsupported decision category: {category!r}")
    if urgency not in VALID_URGENCY:
        urgency = "MEDIUM"
    if not _text(action_id) or not _text(title) or not _text(action) or not _text(reason):
        raise ValueError("action_id, title, action, and reason are required")
    label, score = _confidence(confidence)
    clean_blockers = tuple(dict.fromkeys(_text(x) for x in blockers if _text(x)))
    return DecisionAction(
        action_id=_text(action_id), category=category, title=_text(title),
        action=_text(action), reason=_text(reason), urgency=urgency,
        confidence_label=label, confidence_score=score,
        expected_points_gain=None if expected_points_gain is None else round(_number(expected_points_gain), 2),
        win_probability_gain=None if win_probability_gain is None else round(_number(win_probability_gain), 4),
        playoff_probability_gain=None if playoff_probability_gain is None else round(_number(playoff_probability_gain), 4),
        risk_reduction=round(_clamp(risk_reduction, 0, 100), 2),
        evidence_complete=bool(evidence_complete), blockers=clean_blockers,
        source=_text(source), metadata=dict(metadata or {}),
    )


def score_action(item: DecisionAction) -> float:
    """Return a deterministic 0-100 score without inventing unavailable gains."""
    if not item.allowed:
        return 0.0
    urgency = URGENCY_WEIGHT[item.urgency] * 0.28
    confidence = _clamp(item.confidence_score, 0, 100) * 0.22
    category = CATEGORY_WEIGHT[item.category]
    points = _clamp(item.expected_points_gain, 0, 30) / 30 * 18 if item.expected_points_gain is not None else 0.0
    win = _clamp(item.win_probability_gain, 0, 0.35) / 0.35 * 20 if item.win_probability_gain is not None else 0.0
    playoff = _clamp(item.playoff_probability_gain, 0, 0.35) / 0.35 * 10 if item.playoff_probability_gain is not None else 0.0
    risk = _clamp(item.risk_reduction, 0, 100) / 100 * 8
    evidence_penalty = 0.0 if any(v is not None for v in (
        item.expected_points_gain, item.win_probability_gain, item.playoff_probability_gain
    )) else 6.0
    return round(_clamp(urgency + confidence + category + points + win + playoff + risk - evidence_penalty, 0, 100), 2)


def rank_actions(actions: Iterable[DecisionAction], limit: int | None = None) -> dict[str, Any]:
    rows = list(actions or [])
    seen: set[str] = set()
    duplicates: list[str] = []
    for row in rows:
        if row.action_id in seen:
            duplicates.append(row.action_id)
        seen.add(row.action_id)
    if duplicates:
        raise ValueError(f"duplicate action_id values: {sorted(set(duplicates))}")

    allowed = []
    blocked = []
    for row in rows:
        scored = DecisionAction(**{**row.__dict__, "priority_score": score_action(row)})
        (allowed if scored.allowed else blocked).append(scored)
    allowed.sort(key=lambda x: (-x.priority_score, -x.confidence_score, x.category, x.action_id))
    ranked = [DecisionAction(**{**row.__dict__, "priority": index}) for index, row in enumerate(allowed, 1)]
    if limit is not None:
        ranked = ranked[:max(0, int(limit))]
    blocked.sort(key=lambda x: (x.category, x.action_id))
    return {
        "allowed": bool(ranked),
        "actions": [row.to_dict() for row in ranked],
        "blocked_actions": [row.to_dict() for row in blocked],
        "action_count": len(ranked),
        "blocked_count": len(blocked),
        "methodology": "Deterministic cross-domain ranking from supplied urgency, confidence, measured gains, risk reduction, evidence completeness, and blockers. No external transaction is submitted.",
    }


def lineup_actions(intelligence: Mapping[str, Any]) -> list[DecisionAction]:
    blockers = tuple(intelligence.get("blockers") or ())
    missing = set(intelligence.get("missing_evidence_players") or ())
    rows = []
    for index, decision in enumerate(intelligence.get("start_sit_decisions") or (), 1):
        if decision.get("action") != "SWAP":
            continue
        start = decision.get("start") or {}
        sit = decision.get("sit") or {}
        player = _text(start.get("player"))
        local_blockers = blockers if player in missing else ()
        rows.append(build_action(
            action_id=f"lineup:{decision.get('slot')}:{player}:{_text(sit.get('player'))}",
            category="lineup", title=f"Start {player}",
            action=f"Start {player} over {_text(sit.get('player'))}",
            reason=_text(decision.get("reason")) or "Higher supplied weekly score.",
            urgency="HIGH", confidence=decision.get("confidence"),
            expected_points_gain=decision.get("weekly_score_delta"),
            evidence_complete=not local_blockers, blockers=local_blockers,
            source="weekly_lineup_intelligence", metadata={"slot": decision.get("slot")},
        ))
    return rows


def waiver_actions(plans: Sequence[Mapping[str, Any]], blockers: Iterable[str] = ()) -> list[DecisionAction]:
    rows = []
    inherited = tuple(blockers or ())
    for index, plan in enumerate(plans or (), 1):
        add = plan.get("add") or {}
        drop = plan.get("drop") or {}
        name = _text(add.get("name") or add.get("player"))
        action = f"Add {name}"
        if drop:
            action += f" and drop {_text(drop.get('player_name') or drop.get('player'))}"
        rows.append(build_action(
            action_id=f"waiver:{index}:{name}", category="waiver",
            title=f"Claim {name}", action=action,
            reason=_text(add.get("reason")) or _text(plan.get("summary")) or "Waiver priority from supplied evidence.",
            urgency=_text(plan.get("urgency")) or "MEDIUM",
            confidence={"score": 100 if not inherited else 0},
            risk_reduction=_number(add.get("need_score")) * 10,
            evidence_complete=not inherited, blockers=inherited,
            source="waiver_intelligence",
            metadata={"recommended_bid_pct": plan.get("recommended_bid_pct"), "recommended_bid": plan.get("recommended_bid")},
        ))
    return rows


def trade_actions(intelligence: Mapping[str, Any], limit: int = 5) -> list[DecisionAction]:
    inherited = tuple(intelligence.get("blockers") or ())
    rows = []
    packages = [*(intelligence.get("one_for_one") or ()), *(intelligence.get("two_for_one") or ())]
    for index, package in enumerate(packages[:max(0, int(limit))], 1):
        receive = package.get("receive") or []
        send = package.get("send") or []
        if not receive or not send:
            continue
        target = _text(receive[0].get("player"))
        offered = " + ".join(_text(x.get("player")) for x in send)
        rows.append(build_action(
            action_id=f"trade:{index}:{target}:{offered}", category="trade",
            title=f"Target {target}", action=f"Offer {offered} for {target}",
            reason=_text(package.get("reason")) or "Evidence-supported trade package.",
            urgency="MEDIUM", confidence=package.get("confidence"),
            expected_points_gain=max(0.0, _number(package.get("owner_gain"))),
            evidence_complete=not inherited, blockers=inherited,
            source="trade_intelligence",
            metadata={"verdict": package.get("verdict"), "balance_gap": package.get("balance_gap"), "partner_gain": package.get("partner_gain")},
        ))
    return rows


def build_decision_ranking(
    *, lineup_intelligence: Mapping[str, Any] | None = None,
    waiver_plans: Sequence[Mapping[str, Any]] | None = None,
    waiver_blockers: Iterable[str] = (),
    trade_intelligence: Mapping[str, Any] | None = None,
    extra_actions: Iterable[DecisionAction] = (), limit: int | None = None,
) -> dict[str, Any]:
    actions = []
    if lineup_intelligence is not None:
        actions.extend(lineup_actions(lineup_intelligence))
    if waiver_plans is not None:
        actions.extend(waiver_actions(waiver_plans, waiver_blockers))
    if trade_intelligence is not None:
        actions.extend(trade_actions(trade_intelligence))
    actions.extend(extra_actions or ())
    return rank_actions(actions, limit=limit)

