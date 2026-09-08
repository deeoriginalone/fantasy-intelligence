#!/usr/bin/env python3
"""Run read-only live Sleeper reconciliation.

A concrete local store factory is required. The CLI refuses to guess database
configuration or instantiate a fake store for a live operational report.
"""

import argparse
import importlib
import json
from pathlib import Path

from draft_events.live_reconciliation import LiveSleeperReconciliationService
from draft_events.providers.sleeper import from_sleeper_pick
from services.sleeper_service import get_draft, get_draft_picks


def load_symbol(spec):
    if ":" not in spec:
        raise ValueError("Store factory must use module:symbol format")
    module_name, symbol_name = spec.split(":", 1)
    return getattr(importlib.import_module(module_name), symbol_name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--league-id", required=True)
    parser.add_argument("--draft-id", required=True)
    parser.add_argument(
        "--store-factory",
        required=True,
        help="Import path module:symbol. Symbol must return the configured read-only-capable store.",
    )
    parser.add_argument("--output-dir", default="audit/f3_b3/live_reconciliation")
    args = parser.parse_args()

    factory = load_symbol(args.store_factory)
    store = factory()
    service = LiveSleeperReconciliationService(
        get_draft=get_draft,
        get_draft_picks=get_draft_picks,
        normalize_pick=from_sleeper_pick,
        store=store,
    )
    report = service.run(league_id=args.league_id, draft_id=args.draft_id)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = report.to_dict()
    (output_dir / "live_reconciliation.json").write_text(
        json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8"
    )
    (output_dir / "LIVE_RECONCILIATION.md").write_text(
        "# F3-B.3 Live Sleeper Reconciliation\n\n"
        f"- Draft ID: `{report.draft_id}`\n"
        f"- League ID: `{report.league_id}`\n"
        f"- Sleeper status: `{report.draft_status}`\n"
        f"- Source picks: `{report.source_pick_count}`\n"
        f"- Operational status: **{report.operational_status}**\n\n"
        "## Issues\n\n"
        + ("None\n" if not report.issues else "\n".join(
            f"- **{issue.severity}** `{issue.code}`: {issue.message}"
            for issue in report.issues
        ) + "\n"),
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, default=str))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
