"""Generate a report only from supplied, validated recommendations."""
from typing import Any, Dict, Iterable, List

def _best(rows: List[Dict[str, Any]], key: str, reverse: bool = True):
    eligible = [r for r in rows if r.get(key) is not None]
    return sorted(eligible, key=lambda r: (float(r[key]), str(r.get("model_pick", ""))), reverse=reverse)[0] if eligible else None

def build_weekly_report(*, season: int, week: int, recommendations: Iterable[Dict[str, Any]],
                        survivor: Dict[str, Any] = None, readiness: Dict[str, Any] = None) -> Dict[str, Any]:
    rows = list(recommendations)
    ready = readiness or {"publishable": False, "status": "UNKNOWN", "blockers": ["readiness not supplied"]}
    if not ready.get("publishable"):
        return {"season": season, "week": week, "status": "BLOCKED", "readiness": ready, "recommendations": []}
    lock = _best(rows, "model_probability")
    values = [r for r in rows if r.get("contrarian_edge") is not None]
    best_value = _best(values, "contrarian_edge")
    upsets = [r for r in rows if float(r.get("crowd_percentage", 1)) <= .35]
    traps = [r for r in rows if float(r.get("crowd_percentage", 0)) >= .70 and float(r.get("model_probability", 1)) < .60]
    confidence_order = sorted(rows, key=lambda r: (float(r.get("model_probability", 0)), str(r.get("model_pick", ""))), reverse=True)
    return {
        "season": season, "week": week, "status": "PUBLISHABLE", "readiness": ready,
        "lock_of_week": lock, "best_value": best_value, "best_upset": _best(upsets, "model_probability"),
        "biggest_public_trap": _best(traps, "crowd_percentage"), "survivor": survivor or {},
        "expected_correct_picks": sum(float(r.get("model_probability", 0)) for r in rows),
        "confidence_order": confidence_order,
    }
