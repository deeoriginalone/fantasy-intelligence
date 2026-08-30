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
    if "def build_value_gap_analysis(" not in text:
        marker = "def fetch_available_players(cur):\n"
        require(text, marker, "fetch_available_players()")
        helper = '''def build_value_gap_analysis(
    top_recommendations,
    recommendation_candidates,
    monte_carlo,
):
    """Compare current candidate value with the next option at that position."""
    simulation_by_name = {
        player["player"]: player
        for player in (monte_carlo.get("players") or [])
    }
    analysis = {
        "players": [],
        "best_action": None,
        "status": "READY",
    }

    if not top_recommendations:
        analysis["status"] = "NO CANDIDATES"
        return analysis

    candidates_by_position = {
        position: [] for position in ROSTER_TARGETS
    }
    for candidate in recommendation_candidates:
        position = candidate["player"][2]
        if position in candidates_by_position:
            candidates_by_position[position].append(candidate)

    for candidate in top_recommendations:
        player = candidate["player"]
        player_name = player[1]
        position = player[2]
        position_options = candidates_by_position.get(position, [])
        option_index = next(
            (
                index
                for index, option in enumerate(position_options)
                if option["player"][1] == player_name
            ),
            None,
        )
        next_option = (
            position_options[option_index + 1]
            if option_index is not None
            and option_index + 1 < len(position_options)
            else None
        )

        current_score = candidate["draft_score"]
        next_score = next_option["draft_score"] if next_option else 0
        value_gap = max(0, current_score - next_score)
        simulation = simulation_by_name.get(player_name, {})
        availability_pct = float(simulation.get("availability_pct", 100.0))
        urgency_score = round(
            value_gap + (100.0 - availability_pct) * 0.5,
            1,
        )

        if urgency_score >= 60:
            urgency = "HIGH"
            action = "DRAFT NOW"
        elif urgency_score >= 30:
            urgency = "MEDIUM"
            action = "LEAN DRAFT NOW"
        else:
            urgency = "LOW"
            action = "WAIT MAY BE SAFE"

        row = {
            "player": player_name,
            "position": position,
            "rank": player[0],
            "current_score": current_score,
            "next_option": next_option["player"][1] if next_option else None,
            "next_option_score": next_score,
            "value_gap": value_gap,
            "availability_pct": availability_pct,
            "urgency_score": urgency_score,
            "urgency": urgency,
            "action": action,
        }
        analysis["players"].append(row)

    analysis["players"].sort(
        key=lambda row: (-row["urgency_score"], row["rank"])
    )
    analysis["best_action"] = (
        analysis["players"][0] if analysis["players"] else None
    )
    return analysis


'''
        text = text.replace(marker, helper + marker, 1)

    if "    value_gap_analysis = build_value_gap_analysis(" not in text:
        marker = "    draft_now_wait = build_draft_now_wait_analysis(\n"
        require(text, marker, "Draft Now vs. Wait calculation")
        block = '''    value_gap_analysis = build_value_gap_analysis(
        top_recommendations,
        recommendation_candidates,
        monte_carlo,
    )

'''
        text = text.replace(marker, block + marker, 1)

    if "Value-gap analysis shows" not in text:
        marker = '''    if team_recommendation and monte_carlo.get("players"):\n'''
        require(text, marker, "Monte Carlo recommendation explanation")
        explanation = '''    if team_recommendation and value_gap_analysis.get("players"):
        recommended_gap = next(
            (
                row
                for row in value_gap_analysis["players"]
                if row["player"] == team_recommendation[1]
            ),
            None,
        )
        if recommended_gap and recommended_gap["value_gap"] >= 30:
            recommendation_reasons.append(
                f"Value-gap analysis shows a {recommended_gap['value_gap']}-point "
                f"drop to the next {recommended_gap['position']} option."
            )

'''
        text = text.replace(marker, explanation + marker, 1)

    if "        value_gap_analysis=value_gap_analysis,\n" not in text:
        marker = "        monte_carlo=monte_carlo,\n"
        require(text, marker, "Monte Carlo template argument")
        text = text.replace(
            marker,
            marker + "        value_gap_analysis=value_gap_analysis,\n",
            1,
        )

    return text


def patch_template(text):
    if "Value Gap Analysis" not in text:
        anchor = '<section class="card">\n<h2>🎲 Availability Simulation</h2>'
        require(text, anchor, "Availability Simulation panel")
        panel = '''<section class="card">
<h2>📊 Value Gap Analysis</h2>
<p class="muted">Value gap compares each candidate with the next available option at the same position. Urgency also incorporates simulated next-pick availability.</p>
{% if value_gap_analysis.players %}
<div class="table-wrap"><table><thead><tr><th>Player</th><th>Pos</th><th>Current Score</th><th>Next Option</th><th>Next Score</th><th>Value Gap</th><th>Next-Pick Availability</th><th>Action</th></tr></thead><tbody>
{% for row in value_gap_analysis.players %}<tr{% if loop.first %} style="background:#fff8e1"{% endif %}><td><strong>{{ row.player }}</strong></td><td>{{ row.position }}</td><td>{{ row.current_score }}</td><td>{{ row.next_option or "None" }}</td><td>{{ row.next_option_score }}</td><td><strong>{{ row.value_gap }}</strong></td><td>{{ row.availability_pct }}%</td><td><span class="scarcity-{{ row.urgency|lower }}">{{ row.action }}</span></td></tr>{% endfor %}
</tbody></table></div>
{% if value_gap_analysis.best_action %}<div class="tier-alert"><strong>Largest opportunity cost:</strong> {{ value_gap_analysis.best_action.player }} at {{ value_gap_analysis.best_action.position }}. Waiting projects a {{ value_gap_analysis.best_action.value_gap }}-point drop to the next positional option.</div>{% endif %}
{% else %}<p class="muted">Value-gap status: {{ value_gap_analysis.status }}.</p>{% endif %}
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

    shutil.copy2(APP, APP.with_suffix(".py.before-value-gap"))
    shutil.copy2(
        TEMPLATE,
        TEMPLATE.with_suffix(".html.before-value-gap"),
    )
    APP.write_text(new_app, encoding="utf-8")
    TEMPLATE.write_text(new_template, encoding="utf-8")

    print("Value Gap Analysis installed successfully.")
    print("Backups created with .before-value-gap suffixes.")


if __name__ == "__main__":
    main()
