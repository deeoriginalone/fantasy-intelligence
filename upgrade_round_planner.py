from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"
TEMPLATE = ROOT / "templates" / "draftboard.html"


def require(text, token, label):
    if token not in text:
        raise RuntimeError(
            f"Could not find {label}. No project files were changed."
        )


def patch_app(text):
    if "def build_round_plan(" not in text:
        marker = "def fetch_available_players(cur):\n"
        require(text, marker, "fetch_available_players()")
        helper = '''def build_round_plan(
    active_strategy,
    current_round,
    position_counts,
    roster_targets,
):
    """Build an explainable round-by-round plan for the active strategy."""
    plans = {
        "BEST_AVAILABLE": [
            (1, ["RB", "WR"], "Take the strongest elite value."),
            (2, ["RB", "WR", "TE"], "Preserve value while filling a core starter."),
            (3, ["RB", "WR"], "Build running back and wide receiver depth."),
            (4, ["QB", "TE", "RB", "WR"], "Address premium onesie value if available."),
            (5, ["RB", "WR"], "Continue building flexible depth."),
            (6, ["QB", "TE", "RB", "WR"], "Fill remaining offensive gaps."),
        ],
        "HERO_RB": [
            (1, ["RB"], "Secure an elite anchor running back."),
            (2, ["WR"], "Begin building wide receiver depth."),
            (3, ["WR"], "Add another starting-caliber wide receiver."),
            (4, ["WR", "TE"], "Continue receiver depth or capture tight end value."),
            (5, ["QB", "WR"], "Consider quarterback value without forcing it."),
            (6, ["RB", "WR"], "Add depth behind the hero running back."),
        ],
        "ZERO_RB": [
            (1, ["WR", "TE"], "Open with an elite receiver or premium tight end."),
            (2, ["WR", "TE"], "Continue building pass-catching advantage."),
            (3, ["WR"], "Add another high-volume wide receiver."),
            (4, ["WR", "QB", "TE"], "Capture elite onesie value or receiver depth."),
            (5, ["RB", "WR"], "Begin considering value running backs."),
            (6, ["RB"], "Build the first running back wave."),
        ],
        "ELITE_TE": [
            (1, ["TE", "RB", "WR"], "Take an elite tight end if value supports it."),
            (2, ["TE", "RB", "WR"], "Finish the premium tight end objective or take value."),
            (3, ["RB", "WR"], "Build core running back and receiver starters."),
            (4, ["RB", "WR"], "Continue core position depth."),
            (5, ["QB", "RB", "WR"], "Consider quarterback or best core value."),
            (6, ["RB", "WR"], "Add flexible offensive depth."),
        ],
    }

    selected = plans.get(active_strategy, plans["BEST_AVAILABLE"])
    rows = []
    for round_number, preferred_positions, objective in selected:
        target_met = all(
            position_counts.get(position, 0)
            >= min(1, roster_targets.get(position, 1))
            for position in preferred_positions
        )

        if round_number < current_round:
            status = "COMPLETE" if target_met else "MISSED"
        elif round_number == current_round:
            status = "ACTIVE"
        else:
            status = "UPCOMING"

        rows.append(
            {
                "round": round_number,
                "positions": preferred_positions,
                "objective": objective,
                "status": status,
            }
        )

    next_objective = next(
        (row for row in rows if row["round"] >= current_round),
        None,
    )
    target_progress = {
        position: {
            "current": position_counts.get(position, 0),
            "target": target,
            "remaining": max(0, target - position_counts.get(position, 0)),
        }
        for position, target in roster_targets.items()
    }

    return {
        "strategy": active_strategy,
        "current_round": current_round,
        "rounds": rows,
        "next_objective": next_objective,
        "target_progress": target_progress,
    }


'''
        text = text.replace(marker, helper + marker, 1)

    if "    round_plan = build_round_plan(" not in text:
        marker = "    recommendation_candidates = []\n"
        require(text, marker, "recommendation candidate engine")
        block = '''    round_plan = build_round_plan(
        active_strategy,
        current_round,
        position_counts,
        ROSTER_TARGETS,
    )

'''
        text = text.replace(marker, block + marker, 1)

    if "        round_plan=round_plan,\n" not in text:
        marker = "        current_round=current_round,\n"
        require(text, marker, "current_round template argument")
        text = text.replace(
            marker,
            marker + "        round_plan=round_plan,\n",
            1,
        )

    return text


def patch_template(text):
    if "Round-by-Round Draft Plan" not in text:
        anchor = '<section class="card">\n<h2>🏅 Top 5 Recommendations</h2>'
        require(text, anchor, "Top 5 Recommendations panel")
        panel = '''<section class="card">
<h2>🗺️ Round-by-Round Draft Plan</h2>
{% if round_plan.next_objective %}<div class="highlight"><div class="recommendation-label">Current Objective · Round {{ round_plan.next_objective.round }}</div><h2>{{ round_plan.next_objective.positions|join(" / ") }}</h2><p>{{ round_plan.next_objective.objective }}</p></div>{% endif %}
<div class="table-wrap"><table><thead><tr><th>Round</th><th>Preferred Positions</th><th>Objective</th><th>Status</th></tr></thead><tbody>
{% for row in round_plan.rounds %}<tr{% if row.status == "ACTIVE" %} style="background:#e8f5e9"{% endif %}><td>{{ row.round }}</td><td><strong>{{ row.positions|join(" / ") }}</strong></td><td>{{ row.objective }}</td><td>{{ row.status }}</td></tr>{% endfor %}
</tbody></table></div>
<h3>Final Roster Target Progress</h3>
<div class="roster-grid">{% for position in ["QB", "RB", "WR", "TE"] %}{% set progress = round_plan.target_progress[position] %}<div class="slot"><strong>{{ position }} {{ progress.current }} / {{ progress.target }}</strong><br>Remaining: {{ progress.remaining }}</div>{% endfor %}</div>
<p class="muted">The plan is guidance, not a rigid script. The recommendation engine can override the preferred position when value, scarcity, or tier risk is materially stronger elsewhere.</p>
</section>

'''
        text = text.replace(anchor, panel + anchor, 1)
    return text


def main():
    if not APP.exists() or not TEMPLATE.exists():
        print("Place this script in ~/fantasy-intelligence and run it there.")
        print("Expected app.py and templates/draftboard.html.")
        sys.exit(1)

    app_text = APP.read_text(encoding="utf-8")
    template_text = TEMPLATE.read_text(encoding="utf-8")
    new_app = patch_app(app_text)
    new_template = patch_template(template_text)
    compile(new_app, str(APP), "exec")

    shutil.copy2(APP, APP.with_suffix(".py.before-round-planner"))
    shutil.copy2(
        TEMPLATE,
        TEMPLATE.with_suffix(".html.before-round-planner"),
    )
    APP.write_text(new_app, encoding="utf-8")
    TEMPLATE.write_text(new_template, encoding="utf-8")

    print("Round-by-Round Draft Planner installed successfully.")
    print("Backups created with .before-round-planner suffixes.")


if __name__ == "__main__":
    main()
