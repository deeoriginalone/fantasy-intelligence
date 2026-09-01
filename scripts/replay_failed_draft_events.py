from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent)
)
from app import get_db_connection, SLEEPER_LEAGUE_ID, SLEEPER_DRAFT_ID
from services.sleeper_service import get_rosters
from draft_events.runtime import build_runtime_ingestion


def main():
    rosters = get_rosters(SLEEPER_LEAGUE_ID) or []
    valid = [row.get("roster_id") for row in rosters]
    ingestion = build_runtime_ingestion(get_db_connection, valid)
    results = ingestion.processor.replay_failed()
    for result in results:
        print(result)
    print(f"replayed={len(results)}")

if __name__ == "__main__": main()
