from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"
TEMPLATE = ROOT / "templates" / "draftboard.html"


def require(path, token, label):
    if token not in path:
        raise RuntimeError(f"Could not find {label}. No files were changed.")


def patch_app(text):
    if "def get_player_tier(" not in text:
        marker = "def fetch_available_players(cur):\n"
        require(text, marker, "fetch_available_players()")
        helper = '''def get_player_tier(overall_rank):
    """Group overall ranks into draft-value tiers."""
    if overall_rank <= 12:
        return 1
    if overall_rank <= 24:
        return 2
    if overall_rank <= 50:
        return 3
    if overall_rank <= 100:
        return 4
    return 5


def build_pick_forecast(available_players, scarcity):
    """Estimate availability at the user's next Sleeper pick."""
    forecast = {
        "current_pick": 0,
        "next_pick": None,
        "picks_until_next": None,
        "projected_gone": {position: 0 for position in ["QB", "RB", "WR", "TE"]},
        "projected_remaining": dict(scarcity),
    }

    try:
        draft = get_draft(SLEEPER_DRAFT_ID)
        users = get_users(SLEEPER_LEAGUE_ID) or []
        rosters = get_rosters(SLEEPER_LEAGUE_ID) or []
        picks = get_draft_picks(SLEEPER_DRAFT_ID) or []
        forecast["current_pick"] = len(picks)

        owner_ids = {
            str(user.get("user_id"))
            for user in users
            if user.get("is_owner") is True
        }
        my_roster_ids = {
            roster.get("roster_id")
            for roster in rosters
            if str(roster.get("owner_id")) in owner_ids
        }

        slot_to_roster = draft.get("slot_to_roster_id") or {}
        my_slot = next(
            (
                int(slot)
                for slot, roster_id in slot_to_roster.items()
                if roster_id in my_roster_ids
            ),
            None,
        )
        teams = int((draft.get("settings") or {}).get("teams") or 0)
        rounds = int((draft.get("settings") or {}).get("rounds") or 0)

        if my_slot and teams and rounds:
            own_picks = []
            for round_number in range(1, rounds + 1):
                if draft.get("type") == "snake" and round_number % 2 == 0:
                    slot_in_round = teams - my_slot + 1
                else:
                    slot_in_round = my_slot
                own_picks.append((round_number - 1) * teams + slot_in_round)

            next_pick = next(
                (pick for pick in own_picks if pick > forecast["current_pick"]),
                None,
            )
            forecast["next_pick"] = next_pick

            if next_pick is not None:
                picks_until_next = max(0, next_pick - forecast["current_pick"] - 1)
                forecast["picks_until_next"] = picks_until_next

                projected_players = available_players[:picks_until_next]
                for player in projected_players:
                    position = player[2]
                    if position in forecast["projected_gone"]:
                        forecast["projected_gone"][position] += 1

                forecast["projected_remaining"] = {
                    position: max(
                        0,
                        scarcity.get(position, 0)
                        - forecast["projected_gone"].get(position, 0),
                    )
                    for position in ["QB", "RB", "WR", "TE"]
                }
    except Exception as exc:
        forecast["error"] = str(exc)

    return forecast


'''
        text = text.replace(marker, helper + marker, 1)

    if "    tier_counts = {}\n" not in text:
        marker = "    best_available = available_players[0] if available_players else None\n"
        require(text, marker, "best_available calculation")
        block = '''    tier_counts = {}
    for position in ["QB", "RB", "WR", "TE"]:
        tier_counts[position] = {
            tier: sum(
                1
                for player in available_players
                if player[2] == position
                and get_player_tier(player[0]) == tier
            )
            for tier in [1, 2, 3, 4, 5]
        }

'''
        text = text.replace(marker, block + marker, 1)

    old_alert = '''    elite_te_remaining = len([
        p
        for p in available_players
        if p[2] == "TE"
        and p[0] <= 100
    ])

    tier_alert = None

    if elite_te_remaining <= 5:

        tier_alert = (
            f"Only {elite_te_remaining} top tight ends remain."
        )
'''
    if old_alert in text:
        new_alert = '''    tier_alert = None
    tier_alert_position = None
    tier_alert_tier = None
    tier_alert_remaining = None

    tier_risks = []
    for position in needed_positions:
        leader = next(
            (player for player in available_players if player[2] == position),
            None,
        )
        if leader:
            leader_tier = get_player_tier(leader[0])
            remaining_in_tier = tier_counts[position][leader_tier]
            if remaining_in_tier <= 3:
                tier_risks.append(
                    (remaining_in_tier, leader_tier, position)
                )

    if tier_risks:
        (
            tier_alert_remaining,
            tier_alert_tier,
            tier_alert_position,
        ) = min(tier_risks)
        tier_alert = (
            f"Only {tier_alert_remaining} Tier-{tier_alert_tier} "
            f"{tier_alert_position} players remain."
        )
'''
        text = text.replace(old_alert, new_alert, 1)

    if "    pick_forecast = build_pick_forecast(" not in text:
        marker = "    return render_template(\n        \"draftboard.html\",\n"
        require(text, marker, "draftboard render_template()")
        block = '''    recommended_tier = (
        get_player_tier(team_recommendation[0])
        if team_recommendation
        else None
    )
    recommended_tier_remaining = (
        tier_counts[team_recommendation[2]][recommended_tier]
        if team_recommendation and recommended_tier
        else 0
    )
    pick_forecast = build_pick_forecast(available_players, scarcity)

'''
        text = text.replace(marker, block + marker, 1)

    if "        tier_counts=tier_counts,\n" not in text:
        marker = "        tier_alert=tier_alert,\n"
        require(text, marker, "tier_alert template argument")
        args = '''        tier_alert=tier_alert,
        tier_counts=tier_counts,
        tier_alert_position=tier_alert_position,
        tier_alert_tier=tier_alert_tier,
        tier_alert_remaining=tier_alert_remaining,
        recommended_tier=recommended_tier,
        recommended_tier_remaining=recommended_tier_remaining,
        pick_forecast=pick_forecast,
'''
        text = text.replace(marker, args, 1)

    return text


def patch_template(text):
    if "Tier Intelligence" not in text:
        anchor = '<section class="card"><h2>🏆 My Team</h2>'
        require(text, anchor, "My Team card in draftboard.html")
        cards = '''<section class="card">
<h2>🧱 Tier Intelligence</h2>
{% if team_recommendation and recommended_tier %}
<p><strong>{{ team_recommendation[2] }} tier:</strong> Tier {{ recommended_tier }}</p>
<p><strong>Players left in tier:</strong> {{ recommended_tier_remaining }}</p>
{% endif %}
<div class="table-wrap"><table><thead><tr><th>Position</th><th>Tier 1</th><th>Tier 2</th><th>Tier 3</th><th>Tier 4</th><th>Tier 5</th></tr></thead><tbody>
{% for position in ["QB", "RB", "WR", "TE"] %}<tr><td><strong>{{ position }}</strong></td>{% for tier in [1,2,3,4,5] %}<td>{{ tier_counts[position][tier] }}</td>{% endfor %}</tr>{% endfor %}
</tbody></table></div>
{% if tier_alert %}<div class="tier-alert">🚨 {{ tier_alert }}</div>{% endif %}
</section>

<section class="card">
<h2>🔭 Next-Pick Forecast</h2>
{% if pick_forecast.next_pick %}
<p><strong>Current overall pick:</strong> {{ pick_forecast.current_pick }}</p>
<p><strong>Your next pick:</strong> {{ pick_forecast.next_pick }}</p>
<p><strong>Selections before your pick:</strong> {{ pick_forecast.picks_until_next }}</p>
<div class="roster-grid">{% for position in ["QB", "RB", "WR", "TE"] %}<div class="slot"><strong>{{ position }}</strong><br>Projected gone: {{ pick_forecast.projected_gone[position] }}<br>Projected remaining: {{ pick_forecast.projected_remaining[position] }}</div>{% endfor %}</div>
<p class="muted">Forecast assumes the highest-ranked available players are selected before your next turn.</p>
{% elif pick_forecast.error %}<p class="muted">Forecast unavailable: {{ pick_forecast.error }}</p>
{% else %}<p class="muted">Next-pick forecast will appear after Sleeper publishes a usable draft order.</p>{% endif %}
</section>

'''
        text = text.replace(anchor, cards + anchor, 1)
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

    shutil.copy2(APP, APP.with_suffix(".py.before-tier-engine"))
    shutil.copy2(TEMPLATE, TEMPLATE.with_suffix(".html.before-tier-engine"))
    APP.write_text(new_app, encoding="utf-8")
    TEMPLATE.write_text(new_template, encoding="utf-8")

    compile(new_app, str(APP), "exec")
    print("Tier engine and pick forecast installed successfully.")
    print("Backups: app.py.before-tier-engine and draftboard.html.before-tier-engine")


if __name__ == "__main__":
    main()
