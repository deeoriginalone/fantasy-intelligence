"""F3-D.5 waiver action publication boundary.

Uses the existing F3-B.4 readiness report and F3-C.1 PublicationGate.
It never submits waiver transactions and never invents a FAAB budget.
"""
from __future__ import annotations

from typing import Any, Mapping

from services.publication_gate import PublicationGate

WORKFLOW = "waiver_action_publication"


def build_waiver_publication(intel: Mapping[str, Any], readiness_report) -> dict[str, Any]:
    decision = PublicationGate().decide(readiness_report, workflow=WORKFLOW)
    blocked = {
        "allowed": False,
        "decision": decision.to_dict(),
        "waiver_candidates": [],
        "waiver_action_plans": [],
        "local_roster_context": {},
    }
    if not decision.publish_allowed:
        return blocked

    candidates = intel.get("waiver_candidates")
    plans = intel.get("waiver_action_plans")
    context = intel.get("local_roster_context")
    if not isinstance(candidates, list) or not isinstance(plans, list) or not isinstance(context, Mapping):
        blocked["decision"]["reason_codes"] = list(blocked["decision"].get("reason_codes", [])) + ["WAIVER_CONTRACT_INVALID"]
        return blocked

    safe_plans = []
    for raw in plans:
        if not isinstance(raw, Mapping):
            continue
        plan = dict(raw)
        drop = plan.get("drop")
        if drop is not None and not isinstance(drop, Mapping):
            continue
        # F3-D.4 only emits supplied bench rows as drop candidates. Keep the
        # presentation layer fail-closed if a row is explicitly marked starter.
        if isinstance(drop, Mapping) and drop.get("is_starter") is True:
            continue
        # F3-D.2 uses None when no explicit remaining budget is supplied.
        if plan.get("recommended_bid") is None:
            plan.pop("recommended_bid", None)
        safe_plans.append(plan)

    return {
        "allowed": True,
        "decision": decision.to_dict(),
        "waiver_candidates": list(candidates),
        "waiver_action_plans": safe_plans,
        "local_roster_context": dict(context),
    }
