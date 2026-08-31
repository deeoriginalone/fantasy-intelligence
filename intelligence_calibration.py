"""Outcome calibration metrics with no external dependencies."""
from typing import Any, Dict, Iterable, List

def calibration_summary(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    values: List[Dict[str, float]] = []
    for row in rows:
        p = float(row["probability"])
        y = int(row["outcome"])
        if not 0 <= p <= 1 or y not in (0, 1):
            raise ValueError("probability must be 0..1 and outcome must be 0 or 1")
        values.append({"p": p, "y": y})
    if not values:
        return {"count": 0, "accuracy": None, "brier_score": None, "buckets": []}
    accuracy = sum((v["p"] >= .5) == bool(v["y"]) for v in values) / len(values)
    brier = sum((v["p"] - v["y"]) ** 2 for v in values) / len(values)
    buckets = []
    for low in [i / 10 for i in range(10)]:
        high = low + .1
        bucket = [v for v in values if low <= v["p"] < high or (high == 1 and v["p"] == 1)]
        if bucket:
            buckets.append({
                "range": [low, high], "count": len(bucket),
                "mean_probability": sum(v["p"] for v in bucket) / len(bucket),
                "observed_rate": sum(v["y"] for v in bucket) / len(bucket),
            })
    return {"count": len(values), "accuracy": accuracy, "brier_score": brier, "buckets": buckets}
