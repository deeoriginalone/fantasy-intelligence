from __future__ import annotations
import json
from pathlib import Path

def load_config(path):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("mode") != "sandbox":
        raise ValueError("Batch F2 supports sandbox mode only")
    rec=data.get("recommendation") or {}
    if not rec.get("target"):
        raise ValueError("recommendation.target is required")
    if rec.get("read_only") is not True:
        raise ValueError("recommendation adapter must be declared read_only")
    return data
