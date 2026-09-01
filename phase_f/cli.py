from __future__ import annotations

import argparse
import json

from .adapters import CallableRecommendationAdapter, NoOpRecommendationAdapter
from .simulator import DraftSimulator
from .sources import JsonLinesPickSource


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Replay deterministic mock draft events")
    parser.add_argument("--events", required=True, help="JSON Lines draft event file")
    parser.add_argument("--teams", required=True, type=int)
    parser.add_argument("--rounds", required=True, type=int)
    parser.add_argument(
        "--recommendation-adapter",
        help="Optional module:function callable invoked after each accepted pick",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    adapter = (
        CallableRecommendationAdapter(args.recommendation_adapter)
        if args.recommendation_adapter
        else NoOpRecommendationAdapter()
    )
    simulator = DraftSimulator(args.teams, args.rounds, adapter)
    result = simulator.replay(JsonLinesPickSource(args.events))
    payload = {
        "status": "complete" if result.state.complete else "partial",
        "accepted_picks": len(result.state.picks),
        "expected_picks": result.state.expected_picks,
        "next_pick_no": result.state.next_pick_no,
        "drafted_player_ids": sorted(result.state.drafted_player_ids),
        "rosters": result.state.roster_player_ids,
        "recommendations_generated": len(result.recommendations),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
