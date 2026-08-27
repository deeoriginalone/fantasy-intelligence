from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"
TEMPLATE = ROOT / "templates" / "draftboard.html"


def require(text, token, label):
    if token not in text:
        raise RuntimeError(f"Could not find {label}. No project files were changed.")


def patch_app(text):
    old = '''    team_recommendation = next(
        (
            player
            for player in available_players
            if player[2] in needed_positions
        ),
        best_available,
    )

    rank_score = 0
    agent_draft_score = 0

    if team_recommendation:

        recommended_position = team_recommendation[2]
        overall_rank = team_recommendation[0]

        rank_score = max(
            0,
            101 - overall_rank
        )

        agent_draft_score = (
            rank_score
            + need_score.get(recommended_position, 0)
            + scarcity_score.get(recommended_position, 0)
            + tier_bonus.get(recommended_position, 0)
        )
'''

    new = '''    recommendation_candidates = []

    for player in available_players:
        position = player[2]
        if position not in ROSTER_TARGETS:
            continue

        player_rank_score = max(0, 101 - player[0])
        player_need_score = need_score.get(position, 0)
        player_scarcity_score = scarcity_score.get(position, 0)
        player_tier = get_player_tier(player[0])
        players_left_in_tier = tier_counts[position][player_tier]

        if players_left_in_tier <= 2:
            player_tier_bonus = 100
        elif players_left_in_tier <= 4:
            player_tier_bonus = 50
        else:
            player_tier_bonus = 0

        player_draft_score = (
            player_rank_score
            + player_need_score
            + player_scarcity_score
            + player_tier_bonus
        )

        recommendation_candidates.append(
            {
                "player": player,
                "rank_score": player_rank_score,
                "need_score": player_need_score,
                "scarcity_score": player_scarcity_score,
                "tier": player_tier,
                "tier_remaining": players_left_in_tier,
                "tier_bonus": player_tier_bonus,
                "draft_score": player_draft_score,
            }
        )

    recommendation_candidates.sort(
        key=lambda candidate: (
            -candidate["draft_score"],
            candidate["player"][0],
        )
    )
    top_recommendations = recommendation_candidates[:5]
    team_recommendation = (
        top_recommendations[0]["player"]
        if top_recommendations
        else best_available
    )

    rank_score = 0
    agent_draft_score = 0

    if top_recommendations:
        rank_score = top_recommendations[0]["rank_score"]
        agent_draft_score = top_recommendations[0]["draft_score"]
'''

    if old in text:
        text = text.replace(old, new, 1)
    elif "recommendation_candidates = []" not in text:
        raise RuntimeError(
            "Could not find the current recommendation-selection block. "
            "Run the position-target upgrade first. No project files were changed."
        )

    if "        top_recommendations=top_recommendations,\n" not in text:
        marker = "        team_recommendation=team_recommendation,\n"
        require(text, marker, "team_recommendation template argument")
        text = text.replace(
            marker,
            marker
            + "        top_recommendations=top_recommendations,\n"
            + "        recommendation_candidates=recommendation_candidates,\n",
            1,
        )

    return text


def patch_template(text):
    if "Top 5 Recommendations" not in text:
        anchor = '<section class="card">\n<h2>🧱 Tier Intelligence</h2>'
        require(text, anchor, "the Tier Intelligence panel")
        panel = '''<section class="card">
<h2>🏅 Top 5 Recommendations</h2>
<p class="muted">Players are ranked by overall value, roster need, positional scarcity, and tier-drop risk.</p>
<div class="table-wrap"><table><thead><tr><th>#</th><th>Player</th><th>Pos</th><th>Overall</th><th>Rank</th><th>Need</th><th>Scarcity</th><th>Tier Bonus</th><th>Draft Score</th></tr></thead><tbody>
{% for candidate in top_recommendations %}{% set player = candidate.player %}<tr{% if loop.first %} style="background:#e8f5e9"{% endif %}><td>{{ loop.index }}</td><td><strong>{{ player[1] }}</strong></td><td>{{ player[2] }}</td><td>#{{ player[0] }}</td><td>{{ candidate.rank_score }}</td><td>{{ candidate.need_score }}</td><td>{{ candidate.scarcity_score }}</td><td>{{ candidate.tier_bonus }}</td><td><strong>{{ candidate.draft_score }}</strong></td></tr>{% endfor %}
</tbody></table></div>
</section>

'''
        text = text.replace(anchor, panel + anchor, 1)

    # The backend now owns the final score. Use it directly in the hero card.
    template_score = "{{ recommendation_draft_score }}"
    if template_score in text:
        text = text.replace(template_score, "{{ agent_draft_score }}", 1)

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

    shutil.copy2(APP, APP.with_suffix(".py.before-recommendation-engine"))
    shutil.copy2(
        TEMPLATE,
        TEMPLATE.with_suffix(".html.before-recommendation-engine"),
    )
    APP.write_text(new_app, encoding="utf-8")
    TEMPLATE.write_text(new_template, encoding="utf-8")

    print("Scored recommendation engine and Top 5 board installed.")
    print("Backups created with .before-recommendation-engine suffixes.")


if __name__ == "__main__":
    main()
