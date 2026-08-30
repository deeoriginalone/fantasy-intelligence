from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"

OLD_BLOCK = '''    active_strategy = session.get(
        "draft_strategy",
        DEFAULT_STRATEGY,
    )

    completed_picks = 0

    if "pick_forecast" in locals():

        completed_picks = int(
            pick_forecast.get("current_pick") or 0
        )
    league_size = 10
    try:
        draft_details = get_draft(SLEEPER_DRAFT_ID)
        league_size = int(
            (draft_details.get("settings") or {}).get("teams") or 10
        )
    except Exception:
        pass
    current_round = (completed_picks // league_size) + 1
'''

NEW_BLOCK = '''    active_strategy = session.get(
        "draft_strategy",
        DEFAULT_STRATEGY,
    )
    if active_strategy not in STRATEGY_PROFILES:
        active_strategy = DEFAULT_STRATEGY

    completed_picks = 0
    league_size = 10

    try:
        current_sleeper_picks = get_draft_picks(SLEEPER_DRAFT_ID) or []
        completed_picks = len(current_sleeper_picks)

        draft_details = get_draft(SLEEPER_DRAFT_ID)
        league_size = int(
            (draft_details.get("settings") or {}).get("teams") or 10
        )
    except Exception as exc:
        app.logger.warning(
            "Unable to determine Sleeper draft round: %s",
            exc,
        )

    current_round = (completed_picks // max(league_size, 1)) + 1
'''


def main():
    if not APP.exists():
        print("Place this script in ~/fantasy-intelligence and run it there.")
        print("Expected app.py in the same folder.")
        sys.exit(1)

    text = APP.read_text(encoding="utf-8")

    if OLD_BLOCK in text:
        updated = text.replace(OLD_BLOCK, NEW_BLOCK, 1)
    elif "current_sleeper_picks = get_draft_picks" in text:
        print("The strategy round-order repair is already installed.")
        return
    else:
        raise RuntimeError(
            "The expected strategy block was not found. "
            "No project file was changed."
        )

    # Fix an over-escaped word-boundary expression if present.
    updated = updated.replace(
        're.sub(r"\\\\b(jr|sr|ii|iii|iv)\\\\b", "", value)',
        're.sub(r"\\b(jr|sr|ii|iii|iv)\\b", "", value)',
    )

    # Compile before writing so a bad patch cannot replace the working file.
    compile(updated, str(APP), "exec")

    backup = ROOT / "app.py.before-strategy-round-repair"
    shutil.copy2(APP, backup)
    APP.write_text(updated, encoding="utf-8")

    print("Strategy round-order bug repaired successfully.")
    print(f"Backup created: {backup.name}")
    print(f"Completed-pick count now comes directly from Sleeper draft picks.")


if __name__ == "__main__":
    main()
