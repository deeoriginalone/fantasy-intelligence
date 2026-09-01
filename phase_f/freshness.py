from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping

@dataclass(frozen=True)
class SourceStatus:
    name: str
    updated_at: datetime | None
    required: bool
    max_age_hours: float

    def evaluate(self, now=None):
        now=now or datetime.now(timezone.utc)
        if self.updated_at is None:
            return "BLOCKED" if self.required else "WARNING"
        current=self.updated_at if self.updated_at.tzinfo else self.updated_at.replace(tzinfo=timezone.utc)
        age=(now-current).total_seconds()/3600
        return "BLOCKED" if self.required and age>self.max_age_hours else ("WARNING" if age>self.max_age_hours else "READY")

def gate(statuses):
    results={s.name:s.evaluate() for s in statuses}
    overall="BLOCKED" if "BLOCKED" in results.values() else ("WARNING" if "WARNING" in results.values() else "READY")
    return overall, results
