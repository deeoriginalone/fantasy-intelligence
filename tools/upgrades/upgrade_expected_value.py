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
    if "def build_expected_value_analysis(" not in text:
        marker = "def fetch_available_players(cur):\n"
        require(text, marker, "fetch_available_players()")
        helper = '''def build_expected_value_analysis(
    top_recommendations,
    recommendation_candidates,
    monte_carlo,
):
    """Estimate the recommendation value lost by waiting until the next pick."""
    simulation_by_name = {
        row["player"]: row
        for row in (monte_carlo.get("players") or [])
    }
    candidates_by_position = {
        position: [] for position in ROSTER_TARGETS
    }
    for candidate in recommendation_candidates:
        position = candidate["player"][2]
        if position in candidates_by_position:
            candidates_by_position[position].append(candidate)

    result = {
        "players": [],
        "highest_value_at_risk": None,
        "status": "READY",
    }
    if not top_recommendations:
        result["status"] = "NO CANDIDATES"
        return result

    for candidate in top_recommendations:
        player = candidate["player"]
        player_name = player[1]
        position = player[2]
        current_value = float(candidate["draft_score"])
        position_options = candidates_by_position.get(position, [])

        option_index = next(
            (
                index
                for index, option in enumerate(position_options)
                if option["player"][1] == player_name
            ),
            None,
        )
        fallback = (
            position_options[option_index + 1]
            if option_index is not None
            and option_index + 1 < len(position_options)
            else None
        )
        fallback_name = fallback["player"][1] if fallback else None
        fallback_value = float(fallback["draft_score"]) if fallback else 0.0

        simulation = simulation_by_name.get(player_name, {})
        availability_pct = float(simulation.get("availability_pct", 100.0))
        survival_probability = max(0.0, min(1.0, availability_pct / 100.0))

        expected_future_value = round(
            survival_probability * current_value
            + (1.0 - survival_probability) * fallback_value,
            1,
        )
        expected_value_loss = round(
            max(0.0, current_value - expected_future_value),
            1,
        )
        ev_priority_score = round(current_value + expected_value_loss, 1)

        if expected_value_loss >= 60:
            value_risk = "HIGH"
            action = "DRAFT NOW"
        elif expected_value_loss >= 25:
            value_risk = "MEDIUM"
            action = "LEAN DRAFT NOW"
        else:
            value_risk = "LOW"
            action = "WAIT MAY BE SAFE"

        result["players"].append(
            {
                "player": player_name,
                "position": position,
                "rank": player[0],
                "current_value": round(current_value, 1),
                "availability_pct": round(availability_pct, 1),
                "fallback_player": fallback_name,
                "fallback_value": round(fallback_value, 1),
                "expected_future_value": expected_future_value,
                "expected_value_loss": expected_value_loss,
                "ev_priority_score": ev_priority_score,
                "value_risk": value_risk,
                "action": action,
            }
        )

    result["players"].sort(
        key=lambda row: (
            -row["expected_value_loss"],
            -row["ev_priority_score"],
            row["rank"],
        )
    )
    result["highest_value_at_risk"] = (
        result["players"][0] if result["players"] else None
    )
    return result


'''
        text = text.replace(marker, helper + marker, 1)

    if "    expected_value_analysis = build_expected_value_analysis(" not in text:
        marker = "    value_gap_analysis = build_value_gap_analysis(\n"
        require(text, marker, "Value Gap Analysis calculation")
        block = '''    expected_value_analysis = build_expected_value_analysis(
        top_recommendations,
        recommendation_candidates,
        monte_carlo,
    )

'''
        text = text.replace(marker, block + marker, 1)

    if "Expected-value analysis estimates" not in text:
        marker = '''    if team_recommendation and value_gap_analysis.get("players"):\n'''
        require(text, marker, "Value Gap recommendation explanation")
        explanation = '''    if team_recommendation and expected_value_analysis.get("players"):
        recommended_ev = next(
            (
                row
                for row in expected_value_analysis["players"]
                if row["player"] == team_recommendation[1]
            ),
            None,
        )
        if recommended_ev and recommended_ev["expected_value_loss"] >= 25:
            recommendation_reasons.append(
                f"Expected-value analysis estimates "
                f"{recommended_ev['expected_value_loss']} points of value at risk "
                "if you wait until the next pick."
            )

'''
        text = text.replace(marker, explanation + marker, 1)

    if "        expected_value_analysis=expected_value_analysis,\n" not in text:
        marker = "        value_gap_analysis=value_gap_analysis,\n"
        require(text, marker, "Value Gap template argument")
        text = text.replace(
            marker,
            marker + "        expected_value_analysis=expected_value_analysis,\n",
            1,
        )

    return text


def patch_template(text):
    if "Expected Value Analysis" not in text:
        anchor = '<section class="card">\n<h2>📊 Value Gap Analysis</h2>'
        require(text, anchor, "Value Gap Analysis panel")
        panel = '''<section class="card">
<h2>📉 Expected Value Analysis</h2>
<p class="muted">Expected future value blends the chance the player survives to your next pick with the value of the next same-position fallback.</p>
{% if expected_value_analysis.players %}
<div class="table-wrap"><table><thead><tr><th>Player</th><th>Pos</th><th>Current Value</th><th>Available Next Pick</th><th>Fallback</th><th>Fallback Value</th><th>Expected Future Value</th><th>Value at Risk</th><th>Action</th></tr></thead><tbody>
{% for row in expected_value_analysis.players %}<tr{% if loop.first %} style="background:#f8d7da"{% endif %}><td><strong>{{ row.player }}</strong></td><td>{{ row.position }}</td><td>{{ row.current_value }}</td><td>{{ row.availability_pct }}%</td><td>{{ row.fallback_player or "None" }}</td><td>{{ row.fallback_value }}</td><td>{{ row.expected_future_value }}</td><td><strong>{{ row.expected_value_loss }}</strong></td><td><span class="scarcity-{{ row.value_risk|lower }}">{{ row.action }}</span></td></tr>{% endfor %}
</tbody></table></div>
{% if expected_value_analysis.highest_value_at_risk %}<div class="tier-alert"><strong>Highest value at risk:</strong> {{ expected_value_analysis.highest_value_at_risk.player }}. Waiting is estimated to put {{ expected_value_analysis.highest_value_at_risk.expected_value_loss }} recommendation points at risk.</div>{% endif %}
{% else %}<p class="muted">Expected-value status: {{ expected_value_analysis.status }}.</p>{% endif %}
<p class="muted">Expected value uses recommendation points, not projected fantasy points or monetary value. Results are planning estimates and are not guarantees.</p>
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

    shutil.copy2(APP, APP.with_suffix(".py.before-expected-value"))
    shutil.copy2(
        TEMPLATE,
        TEMPLATE.with_suffix(".html.before-expected-value"),
    )
    APP.write_text(new_app, encoding="utf-8")
    TEMPLATE.write_text(new_template, encoding="utf-8")

    print("Expected Value Drafting installed successfully.")
    print("Backups created with .before-expected-value suffixes.")


if __name__ == "__main__":
    main()
