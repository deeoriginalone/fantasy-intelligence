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
    if "import random\n" not in text:
        marker = "import unicodedata\n"
        require(text, marker, "standard-library imports")
        text = text.replace(marker, marker + "import random\n", 1)

    if "MONTE_CARLO_SIMULATIONS =" not in text:
        marker = 'SLEEPER_DRAFT_ID = "1398094331272794112"\n'
        require(text, marker, "Sleeper draft configuration")
        text = text.replace(
            marker,
            marker + "MONTE_CARLO_SIMULATIONS = 500\n",
            1,
        )

    if "def run_monte_carlo_availability(" not in text:
        marker = "def fetch_available_players(cur):\n"
        require(text, marker, "fetch_available_players()")
        helper = '''def run_monte_carlo_availability(
    available_players,
    top_recommendations,
    pick_forecast,
    league_tendencies,
    simulations=MONTE_CARLO_SIMULATIONS,
):
    """Estimate Top-5 availability using weighted, reproducible simulations."""
    results = {
        "simulations": simulations,
        "picks_until_next": int(pick_forecast.get("picks_until_next") or 0),
        "players": [],
        "status": "READY",
    }

    if not top_recommendations:
        results["status"] = "NO CANDIDATES"
        return results

    if not pick_forecast.get("next_pick"):
        results["status"] = "NO NEXT PICK"
        return results

    picks_until_next = results["picks_until_next"]
    if picks_until_next <= 0:
        for candidate in top_recommendations:
            player = candidate["player"]
            results["players"].append(
                {
                    "player": player[1],
                    "position": player[2],
                    "rank": player[0],
                    "available_count": simulations,
                    "availability_pct": 100.0,
                    "risk": "LOW",
                }
            )
        return results

    offensive_pool = [
        player
        for player in available_players
        if player[2] in ROSTER_TARGETS
    ]
    targets = {
        candidate["player"][1]: candidate
        for candidate in top_recommendations
    }
    survived = {name: 0 for name in targets}

    league_bonus = league_tendencies.get("bonus") or {}
    pressure = pick_forecast.get("position_pressure") or {}
    projected_gone = pick_forecast.get("projected_gone") or {}
    seed_value = (
        int(pick_forecast.get("current_pick") or 0) * 1009
        + len(offensive_pool) * 37
        + picks_until_next
    )
    rng = random.Random(seed_value)

    for _ in range(simulations):
        pool = list(offensive_pool)
        drafted_names = set()

        for pick_index in range(picks_until_next):
            if not pool:
                break

            candidate_window = pool[: min(60, len(pool))]
            weights = []
            for player in candidate_window:
                rank, _, position, _ = player[:4]
                rank_weight = max(2, 125 - min(rank, 123))
                tendency_weight = league_bonus.get(position, 0)
                pressure_weight = int(pressure.get(position, 0) / 5)
                run_weight = projected_gone.get(position, 0) * 5
                tier = get_player_tier(rank)
                tier_remaining = sum(
                    1
                    for pool_player in pool
                    if pool_player[2] == position
                    and get_player_tier(pool_player[0]) == tier
                )
                tier_weight = 20 if tier_remaining <= 2 else 8 if tier_remaining <= 4 else 0
                noise = rng.uniform(0.85, 1.15)
                weights.append(
                    max(
                        1.0,
                        (
                            rank_weight
                            + tendency_weight
                            + pressure_weight
                            + run_weight
                            + tier_weight
                        )
                        * noise,
                    )
                )

            chosen = rng.choices(candidate_window, weights=weights, k=1)[0]
            pool.remove(chosen)
            drafted_names.add(chosen[1])

        for player_name in targets:
            if player_name not in drafted_names:
                survived[player_name] += 1

    for candidate in top_recommendations:
        player = candidate["player"]
        player_name = player[1]
        availability_pct = round(
            survived[player_name] / simulations * 100,
            1,
        )
        if availability_pct <= 25:
            risk = "HIGH"
        elif availability_pct <= 55:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        results["players"].append(
            {
                "player": player_name,
                "position": player[2],
                "rank": player[0],
                "available_count": survived[player_name],
                "availability_pct": availability_pct,
                "risk": risk,
            }
        )

    return results


'''
        text = text.replace(marker, helper + marker, 1)

    if "    monte_carlo = run_monte_carlo_availability(" not in text:
        marker = "    draft_now_wait = build_draft_now_wait_analysis(\n"
        require(text, marker, "Draft Now vs. Wait calculation")
        block = '''    monte_carlo = run_monte_carlo_availability(
        available_players,
        top_recommendations,
        pick_forecast,
        league_tendencies,
    )

'''
        text = text.replace(marker, block + marker, 1)

    if "Monte Carlo estimates only" not in text:
        marker = '''    if team_recommendation and pick_forecast.get("next_pick"):\n'''
        require(text, marker, "opponent recommendation explanations")
        explanation = '''    if team_recommendation and monte_carlo.get("players"):
        recommended_simulation = next(
            (
                player
                for player in monte_carlo["players"]
                if player["player"] == team_recommendation[1]
            ),
            None,
        )
        if recommended_simulation:
            availability_pct = recommended_simulation["availability_pct"]
            if availability_pct <= 25:
                recommendation_reasons.append(
                    f"Monte Carlo estimates only a {availability_pct}% chance "
                    "the player reaches your next pick."
                )
            elif availability_pct >= 70:
                recommendation_reasons.append(
                    f"Monte Carlo estimates a {availability_pct}% chance "
                    "the player remains available at your next pick."
                )

'''
        text = text.replace(marker, explanation + marker, 1)

    if "        monte_carlo=monte_carlo,\n" not in text:
        marker = "        draft_now_wait=draft_now_wait,\n"
        require(text, marker, "draft_now_wait template argument")
        text = text.replace(
            marker,
            marker + "        monte_carlo=monte_carlo,\n",
            1,
        )

    return text


def patch_template(text):
    if "Availability Simulation" not in text:
        anchor = '<section class="card">\n<h2>📈 League Tendencies</h2>'
        require(text, anchor, "League Tendencies panel")
        panel = '''<section class="card">
<h2>🎲 Availability Simulation</h2>
<p><strong>Simulations:</strong> {{ monte_carlo.simulations }} · <strong>Selections before next pick:</strong> {{ monte_carlo.picks_until_next }}</p>
{% if monte_carlo.players %}
<div class="table-wrap"><table><thead><tr><th>Player</th><th>Pos</th><th>Overall</th><th>Available Next Pick</th><th>Risk of Being Gone</th></tr></thead><tbody>
{% for result in monte_carlo.players %}<tr><td><strong>{{ result.player }}</strong></td><td>{{ result.position }}</td><td>#{{ result.rank }}</td><td><strong>{{ result.availability_pct }}%</strong></td><td><span class="scarcity-{{ result.risk|lower }}">{{ result.risk }}</span></td></tr>{% endfor %}
</tbody></table></div>
{% else %}<p class="muted">Simulation status: {{ monte_carlo.status }}. Availability estimates will appear when Sleeper exposes a usable next pick.</p>{% endif %}
<p class="muted">This is a reproducible weighted simulation using rank, league tendencies, opponent pressure, projected position runs, and tier depth. Percentages are planning estimates, not guarantees.</p>
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

    shutil.copy2(APP, APP.with_suffix(".py.before-monte-carlo"))
    shutil.copy2(
        TEMPLATE,
        TEMPLATE.with_suffix(".html.before-monte-carlo"),
    )
    APP.write_text(new_app, encoding="utf-8")
    TEMPLATE.write_text(new_template, encoding="utf-8")

    print("Monte Carlo availability simulator installed successfully.")
    print("Backups created with .before-monte-carlo suffixes.")


if __name__ == "__main__":
    main()
