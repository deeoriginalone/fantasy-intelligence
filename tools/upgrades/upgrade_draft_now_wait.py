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
    if "def build_draft_now_wait_analysis(" not in text:
        marker = "def fetch_available_players(cur):\n"
        require(text, marker, "fetch_available_players()")
        helper = '''def build_draft_now_wait_analysis(
    recommendation,
    top_recommendations,
    pick_forecast,
    tier_counts,
    need_score,
):
    """Estimate whether the recommended player can survive until the next pick."""
    analysis = {
        "decision": "DRAFT NOW",
        "risk_level": "HIGH",
        "survival_probability": 0,
        "next_pick": pick_forecast.get("next_pick"),
        "picks_until_next": pick_forecast.get("picks_until_next"),
        "reasons": [],
    }

    if not recommendation:
        analysis.update(
            decision="NO RECOMMENDATION",
            risk_level="UNKNOWN",
            survival_probability=0,
        )
        analysis["reasons"].append("No available recommendation could be scored.")
        return analysis

    if not pick_forecast.get("next_pick"):
        analysis.update(
            decision="DRAFT NOW",
            risk_level="UNKNOWN",
            survival_probability=0,
        )
        analysis["reasons"].append(
            "Sleeper has not exposed a usable next-pick forecast."
        )
        return analysis

    player_name = recommendation[1]
    position = recommendation[2]
    overall_rank = recommendation[0]
    picks_until_next = int(pick_forecast.get("picks_until_next") or 0)
    projected_picks = pick_forecast.get("projected_picks") or []
    projected_names = {
        str(pick.get("player") or "").lower()
        for pick in projected_picks
    }
    projected_position_picks = int(
        (pick_forecast.get("projected_gone") or {}).get(position, 0)
    )
    needy_teams = int(
        (pick_forecast.get("teams_needing_position") or {}).get(position, 0)
    )

    tier = get_player_tier(overall_rank)
    tier_remaining = int(tier_counts.get(position, {}).get(tier, 0))

    score = 82
    if player_name.lower() in projected_names:
        score -= 65
        analysis["reasons"].append(
            "The opponent model projects this player to be selected before your next pick."
        )
    if overall_rank <= picks_until_next + 3:
        score -= 25
        analysis["reasons"].append(
            "Overall rank places the player inside the expected selection window."
        )
    if projected_position_picks >= 2:
        score -= min(30, projected_position_picks * 10)
        analysis["reasons"].append(
            f"The model projects {projected_position_picks} {position} selections before your next pick."
        )
    if needy_teams >= 3:
        score -= min(20, needy_teams * 4)
        analysis["reasons"].append(
            f"{needy_teams} opponents show meaningful {position} demand."
        )
    if tier_remaining <= 2:
        score -= 30
        analysis["reasons"].append(
            f"Only {tier_remaining} Tier-{tier} {position} players remain."
        )
    elif tier_remaining <= 4:
        score -= 15
        analysis["reasons"].append(
            f"The current Tier-{tier} {position} group is nearly depleted."
        )
    if need_score.get(position, 0) >= 75:
        score -= 10
        analysis["reasons"].append(
            f"{position} remains a major roster need."
        )

    score = max(0, min(100, score))
    analysis["survival_probability"] = score

    if score <= 35:
        analysis["decision"] = "DRAFT NOW"
        analysis["risk_level"] = "HIGH"
    elif score <= 65:
        analysis["decision"] = "LEAN DRAFT NOW"
        analysis["risk_level"] = "MEDIUM"
    else:
        analysis["decision"] = "WAIT MAY BE SAFE"
        analysis["risk_level"] = "LOW"

    if not analysis["reasons"]:
        analysis["reasons"].append(
            "Opponent demand and tier pressure are currently limited."
        )

    return analysis


'''
        text = text.replace(marker, helper + marker, 1)

    if "    draft_now_wait = build_draft_now_wait_analysis(" not in text:
        marker = '''    if team_recommendation and pick_forecast.get("next_pick"):\n'''
        require(text, marker, "opponent explanation block")
        block = '''    draft_now_wait = build_draft_now_wait_analysis(
        team_recommendation,
        top_recommendations,
        pick_forecast,
        tier_counts,
        need_score,
    )

'''
        text = text.replace(marker, block + marker, 1)

    if "        draft_now_wait=draft_now_wait,\n" not in text:
        marker = "        pick_forecast=pick_forecast,\n"
        require(text, marker, "pick_forecast template argument")
        text = text.replace(
            marker,
            marker + "        draft_now_wait=draft_now_wait,\n",
            1,
        )

    return text


def patch_template(text):
    if "Draft Now vs. Wait" not in text:
        anchor = '<section class="card">\n<h2>🤖 Opponent Pressure Index</h2>'
        require(text, anchor, "Opponent Pressure Index panel")
        panel = '''<section class="card">
<h2>⏱️ Draft Now vs. Wait</h2>
{% if team_recommendation %}
<div class="highlight">
<div class="recommendation-label">{{ draft_now_wait.decision }}</div>
<h2>{{ team_recommendation[1] }}</h2>
<p><strong>Risk of being gone:</strong> {{ draft_now_wait.risk_level }}</p>
<p><strong>Estimated chance available at next pick:</strong> {{ draft_now_wait.survival_probability }}%</p>
{% if draft_now_wait.next_pick %}<p><strong>Your next pick:</strong> {{ draft_now_wait.next_pick }} · <strong>Selections before then:</strong> {{ draft_now_wait.picks_until_next }}</p>{% endif %}
<strong>Decision factors:</strong>
<ul>{% for reason in draft_now_wait.reasons %}<li>{{ reason }}</li>{% endfor %}</ul>
</div>
{% else %}<p class="muted">No player is currently available for a draft-now analysis.</p>{% endif %}
<p class="muted">The availability percentage is a transparent heuristic based on projected opponent picks, positional demand, overall rank, and tier depth. It is not a statistical guarantee.</p>
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

    shutil.copy2(APP, APP.with_suffix(".py.before-draft-now-wait"))
    shutil.copy2(
        TEMPLATE,
        TEMPLATE.with_suffix(".html.before-draft-now-wait"),
    )
    APP.write_text(new_app, encoding="utf-8")
    TEMPLATE.write_text(new_template, encoding="utf-8")

    print("Draft Now vs. Wait analyzer installed successfully.")
    print("Backups created with .before-draft-now-wait suffixes.")


if __name__ == "__main__":
    main()
