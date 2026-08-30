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
    if "def build_league_tendencies(" not in text:
        marker = "def build_opponent_forecast(available_players, scarcity):\n"
        require(text, marker, "build_opponent_forecast()")
        helper = '''def build_league_tendencies():
    """Summarize positional behavior from completed Sleeper draft picks."""
    positions = ["QB", "RB", "WR", "TE"]
    result = {
        "counts": {position: 0 for position in positions},
        "percentages": {position: 0.0 for position in positions},
        "bias": {position: "LOW" for position in positions},
        "bonus": {position: 0 for position in positions},
        "total": 0,
        "sample_status": "NO DATA",
        "expected_next_run": None,
    }

    try:
        picks = get_draft_picks(SLEEPER_DRAFT_ID) or []
        for pick in picks:
            metadata = pick.get("metadata") or {}
            position = metadata.get("position")
            if position in result["counts"]:
                result["counts"][position] += 1
                result["total"] += 1

        if result["total"] == 0:
            return result

        if result["total"] < 10:
            result["sample_status"] = "EARLY SAMPLE"
        elif result["total"] < 30:
            result["sample_status"] = "DEVELOPING"
        else:
            result["sample_status"] = "ESTABLISHED"

        for position in positions:
            count = result["counts"][position]
            percentage = round(count / result["total"] * 100, 1)
            result["percentages"][position] = percentage

            if percentage >= 40:
                result["bias"][position] = "HIGH"
                result["bonus"][position] = 25
            elif percentage >= 25:
                result["bias"][position] = "MEDIUM"
                result["bonus"][position] = 12
            else:
                result["bias"][position] = "LOW"
                result["bonus"][position] = 0

        result["expected_next_run"] = max(
            positions,
            key=lambda position: (
                result["percentages"][position],
                result["counts"][position],
            ),
        )
    except Exception as exc:
        result["error"] = str(exc)

    return result


'''
        text = text.replace(marker, helper + marker, 1)

    # Extend the opponent model signature and establish a safe default.
    old_signature = "def build_opponent_forecast(available_players, scarcity):\n"
    new_signature = "def build_opponent_forecast(available_players, scarcity, league_tendencies=None):\n"
    if old_signature in text:
        text = text.replace(old_signature, new_signature, 1)

    if "    league_tendencies = league_tendencies or {\"bonus\": {}}\n" not in text:
        marker = '''    result = {
        "current_pick": 0,
'''
        require(text, marker, "opponent forecast result dictionary")
        text = text.replace(
            marker,
            '    league_tendencies = league_tendencies or {"bonus": {}}\n\n' + marker,
            1,
        )

    # Add league-behavior bonus to each simulated opponent selection.
    old_lambda = '''                    max(0, 101 - player[0])
                    + need_pressure.get(player[2], 0)
                    + (
'''
    new_lambda = '''                    max(0, 101 - player[0])
                    + need_pressure.get(player[2], 0)
                    + (league_tendencies.get("bonus") or {}).get(player[2], 0)
                    + (
'''
    if old_lambda in text:
        text = text.replace(old_lambda, new_lambda, 1)
    elif 'league_tendencies.get("bonus")' not in text:
        raise RuntimeError(
            "Could not find the opponent-selection scoring expression. "
            "No project files were changed."
        )

    # Build tendencies before the opponent forecast and pass them into it.
    old_call = "    pick_forecast = build_opponent_forecast(available_players, scarcity)\n"
    new_call = '''    league_tendencies = build_league_tendencies()
    pick_forecast = build_opponent_forecast(
        available_players,
        scarcity,
        league_tendencies,
    )
'''
    if old_call in text:
        text = text.replace(old_call, new_call, 1)
    elif "    league_tendencies = build_league_tendencies()\n" not in text:
        raise RuntimeError(
            "Could not find the opponent forecast call. "
            "No project files were changed."
        )

    # Add a modest tendency bonus to actual candidate scoring.
    if "        player_league_bonus = league_tendencies" not in text:
        marker = '''        player_strategy_bonus = get_strategy_bonus(
            active_strategy,
            position,
            current_round,
        )
'''
        require(text, marker, "candidate strategy bonus")
        replacement = marker + '''        player_league_bonus = (
            league_tendencies.get("bonus") or {}
        ).get(position, 0)
'''
        text = text.replace(marker, replacement, 1)

        score_marker = '''            + player_tier_bonus
            + player_strategy_bonus
'''
        require(text, score_marker, "candidate score components")
        text = text.replace(
            score_marker,
            score_marker + "            + player_league_bonus\n",
            1,
        )

        field_marker = '                "strategy_bonus": player_strategy_bonus,\n'
        require(text, field_marker, "candidate strategy field")
        text = text.replace(
            field_marker,
            field_marker + '                "league_bonus": player_league_bonus,\n',
            1,
        )

    # Explain significant league behavior for the winning position.
    if "This league is drafting" not in text:
        marker = "    recommended_tier = (\n"
        require(text, marker, "recommended tier calculation")
        explanation = '''    league_bonus_for_pick = 0
    if team_recommendation:
        recommended_position = team_recommendation[2]
        league_bonus_for_pick = (
            league_tendencies.get("bonus") or {}
        ).get(recommended_position, 0)
        position_bias = (
            league_tendencies.get("bias") or {}
        ).get(recommended_position, "LOW")
        position_share = (
            league_tendencies.get("percentages") or {}
        ).get(recommended_position, 0)

        if position_bias == "HIGH":
            recommendation_reasons.append(
                f"This league is drafting {recommended_position} aggressively "
                f"({position_share}% of completed offensive picks)."
            )
        elif position_bias == "MEDIUM":
            recommendation_reasons.append(
                f"League demand for {recommended_position} is elevated "
                f"({position_share}% of completed offensive picks)."
            )

'''
        text = text.replace(marker, explanation + marker, 1)

    # Pass data to the template.
    if "        league_tendencies=league_tendencies,\n" not in text:
        marker = "        pick_forecast=pick_forecast,\n"
        require(text, marker, "pick_forecast template argument")
        text = text.replace(
            marker,
            marker
            + "        league_tendencies=league_tendencies,\n"
            + "        league_bonus_for_pick=league_bonus_for_pick,\n",
            1,
        )

    return text


def patch_template(text):
    if "League Tendencies" not in text:
        anchor = '<section class="card">\n<h2>⏱️ Draft Now vs. Wait</h2>'
        require(text, anchor, "Draft Now vs. Wait panel")
        panel = '''<section class="card">
<h2>📈 League Tendencies</h2>
<p><strong>Completed offensive picks:</strong> {{ league_tendencies.total }}</p>
<p><strong>Sample status:</strong> {{ league_tendencies.sample_status }}</p>
{% if league_tendencies.expected_next_run %}<p><strong>Current positional run:</strong> {{ league_tendencies.expected_next_run }}</p>{% endif %}
<div class="table-wrap"><table><thead><tr><th>Position</th><th>Drafted</th><th>Share</th><th>Bias</th><th>Score Bonus</th></tr></thead><tbody>
{% for position in ["QB", "RB", "WR", "TE"] %}<tr><td><strong>{{ position }}</strong></td><td>{{ league_tendencies.counts[position] }}</td><td>{{ league_tendencies.percentages[position] }}%</td><td><span class="scarcity-{{ league_tendencies.bias[position]|lower }}">{{ league_tendencies.bias[position] }}</span></td><td>{% if league_tendencies.bonus[position] > 0 %}+{% endif %}{{ league_tendencies.bonus[position] }}</td></tr>{% endfor %}
</tbody></table></div>
{% if league_tendencies.total < 10 %}<p class="muted">League tendencies are intentionally conservative until at least 10 offensive picks have been completed.</p>{% endif %}
</section>

'''
        text = text.replace(anchor, panel + anchor, 1)

    # Add the league bonus to the Top 5 comparison table.
    old_header = '<th>Strategy</th><th>Draft Score</th>'
    if old_header in text:
        text = text.replace(
            old_header,
            '<th>Strategy</th><th>League</th><th>Draft Score</th>',
            1,
        )
    old_cells = '''<td>{% if candidate.strategy_bonus > 0 %}+{% endif %}{{ candidate.strategy_bonus }}</td><td><strong>{{ candidate.draft_score }}</strong></td>'''
    if old_cells in text:
        text = text.replace(
            old_cells,
            '''<td>{% if candidate.strategy_bonus > 0 %}+{% endif %}{{ candidate.strategy_bonus }}</td><td>{% if candidate.league_bonus > 0 %}+{% endif %}{{ candidate.league_bonus }}</td><td><strong>{{ candidate.draft_score }}</strong></td>''',
            1,
        )

    if "League Bias Bonus</span>" not in text:
        marker = '<div class="metric metric-total"><span class="metric-label">Draft Score</span>'
        require(text, marker, "Draft Score metric")
        metric = '''<div class="metric"><span class="metric-label">League Bias Bonus</span><span class="metric-value">{% if league_bonus_for_pick > 0 %}+{% endif %}{{ league_bonus_for_pick }}</span></div>
'''
        text = text.replace(marker, metric + marker, 1)

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

    shutil.copy2(APP, APP.with_suffix(".py.before-league-tendencies"))
    shutil.copy2(
        TEMPLATE,
        TEMPLATE.with_suffix(".html.before-league-tendencies"),
    )
    APP.write_text(new_app, encoding="utf-8")
    TEMPLATE.write_text(new_template, encoding="utf-8")

    print("League Tendencies installed successfully.")
    print("Backups created with .before-league-tendencies suffixes.")


if __name__ == "__main__":
    main()
