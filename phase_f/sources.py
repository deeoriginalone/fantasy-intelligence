from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import DraftPick


class JsonLinesPickSource:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def __iter__(self) -> Iterable[DraftPick]:
        if not self.path.exists():
            raise FileNotFoundError(self.path)
        with self.path.open("r", encoding="utf-8") as handle:
            for line_no, raw in enumerate(handle, start=1):
                raw = raw.strip()
                if not raw or raw.startswith("#"):
                    continue
                try:
                    data = json.loads(raw)
                    pick = DraftPick(**data)
                    pick.validate()
                except Exception as exc:
                    raise ValueError(
                        f"invalid draft event at {self.path}:{line_no}: {exc}"
                    ) from exc
                yield pick
