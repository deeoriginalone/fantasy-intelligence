from __future__ import annotations
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

class SnapshotWriter:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, pick_no, recommendation):
        row = {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "pick_no": pick_no,
            **asdict(recommendation),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        return row
