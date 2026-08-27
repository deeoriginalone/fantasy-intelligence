from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"

EARLY_MARKER = '''    active_strategy = session.get(
        "draft_strategy",
        DEFAULT_STRATEGY,
    )
'''

EARLY_REPLACEMENT = '''    # League tendencies must exist before candidate scoring uses league bonuses.
    league_tendencies = build_league_tendencies()

    active_strategy = session.get(
        "draft_strategy",
        DEFAULT_STRATEGY,
    )
'''

LATE_BLOCK = '''    league_tendencies = build_league_tendencies()
    pick_forecast = build_opponent_forecast(
        available_players,
        scarcity,
        league_tendencies,
    )
'''

LATE_REPLACEMENT = '''    pick_forecast = build_opponent_forecast(
        available_players,
        scarcity,
        league_tendencies,
    )
'''


def main():
    if not APP.exists():
        print("Place this file in ~/fantasy-intelligence and run it there.")
        print("Expected app.py in the same directory.")
        sys.exit(1)

    text = APP.read_text(encoding="utf-8")

    if "def build_league_tendencies(" not in text:
        raise RuntimeError(
            "build_league_tendencies() was not found. "
            "Install the League Tendencies upgrade first."
        )

    already_fixed = (
        "# League tendencies must exist before candidate scoring uses league bonuses."
        in text
    )

    if already_fixed:
        print("League Tendencies initialization order is already repaired.")
        return

    if EARLY_MARKER not in text:
        raise RuntimeError(
            "The active strategy block was not found. "
            "No project file was changed."
        )

    updated = text.replace(EARLY_MARKER, EARLY_REPLACEMENT, 1)

    # Remove the later duplicate assignment but preserve the opponent forecast call.
    if LATE_BLOCK in updated:
        updated = updated.replace(LATE_BLOCK, LATE_REPLACEMENT, 1)
    else:
        # Support a one-line variant produced by an earlier installer.
        one_line = (
            "    league_tendencies = build_league_tendencies()\n"
            "    pick_forecast = build_opponent_forecast(available_players, scarcity, league_tendencies)\n"
        )
        one_line_replacement = (
            "    pick_forecast = build_opponent_forecast("
            "available_players, scarcity, league_tendencies)\n"
        )
        if one_line in updated:
            updated = updated.replace(one_line, one_line_replacement, 1)

    # Guard against accidental duplicate initialization inside draftboard().
    draftboard_start = updated.find('def draftboard():')
    next_route = updated.find('\n@app.route(', draftboard_start + 1)
    draftboard_body = updated[
        draftboard_start: next_route if next_route != -1 else len(updated)
    ]
    assignment_count = draftboard_body.count(
        "league_tendencies = build_league_tendencies()"
    )
    if assignment_count != 1:
        raise RuntimeError(
            "Expected exactly one league_tendencies assignment inside "
            f"draftboard(), found {assignment_count}. No file was changed."
        )

    # Validate Python before writing over the working application.
    compile(updated, str(APP), "exec")

    backup = ROOT / "app.py.before-league-tendencies-order-repair"
    shutil.copy2(APP, backup)
    APP.write_text(updated, encoding="utf-8")

    print("League Tendencies initialization order repaired successfully.")
    print(f"Backup created: {backup.name}")
    print("league_tendencies now initializes before recommendation scoring.")


if __name__ == "__main__":
    main()
