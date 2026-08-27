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
    if "def build_opponent_forecast(" not in text:
        marker = "def fetch_available_players(cur):\n"
        require(text, marker, "fetch_available_players()")
        helper = '''def build_opponent_forecast(available_players, scarcity):
    """Simulate picks before the user's next turn using opponent roster needs."""
    result = {
        "current_pick": 0,
        "next_pick": None,
        "picks_until_next": None,
        "teams_before_next_pick": [],
        "position_pressure": {
            position: 0 for position in ["QB", "RB", "WR", "TE"]
        },
        "teams_needing_position": {
            position: 0 for position in ["QB", "RB", "WR", "TE"]
        },
        "projected_gone": {
            position: 0 for position in ["QB", "RB", "WR", "TE"]
        },
        "projected_remaining": dict(scarcity),
        "projected_picks": [],
    }

    try:
        draft = get_draft(SLEEPER_DRAFT_ID)
        users = get_users(SLEEPER_LEAGUE_ID) or []
        rosters = get_rosters(SLEEPER_LEAGUE_ID) or []
        picks = get_draft_picks(SLEEPER_DRAFT_ID) or []
        result["current_pick"] = len(picks)

        users_by_id = {
            str(user.get("user_id")): user for user in users
        }
        team_by_roster = {}
        my_roster_ids = set()
        for sleeper_roster in rosters:
            roster_id = sleeper_roster.get("roster_id")
            owner_id = str(sleeper_roster.get("owner_id") or "")
            user = users_by_id.get(owner_id, {})
            metadata = user.get("metadata") or {}
            team_by_roster[roster_id] = (
                metadata.get("team_name")
                or user.get("display_name")
                or f"Roster {roster_id}"
            )
            if user.get("is_owner") is True:
                my_roster_ids.add(roster_id)

        slot_to_roster = {
            int(slot): roster_id
            for slot, roster_id in (draft.get("slot_to_roster_id") or {}).items()
        }
        roster_to_slot = {
            roster_id: slot for slot, roster_id in slot_to_roster.items()
        }
        teams = int((draft.get("settings") or {}).get("teams") or 0)
        rounds = int((draft.get("settings") or {}).get("rounds") or 0)
        my_roster_id = next(iter(my_roster_ids), None)
        my_slot = roster_to_slot.get(my_roster_id)

        if not (teams and rounds and my_slot):
            return result

        own_pick_numbers = []
        for round_number in range(1, rounds + 1):
            if draft.get("type") == "snake" and round_number % 2 == 0:
                slot_in_round = teams - my_slot + 1
            else:
                slot_in_round = my_slot
            own_pick_numbers.append(
                (round_number - 1) * teams + slot_in_round
            )

        result["next_pick"] = next(
            (
                pick_number
                for pick_number in own_pick_numbers
                if pick_number > result["current_pick"]
            ),
            None,
        )
        if result["next_pick"] is None:
            return result

        result["picks_until_next"] = max(
            0,
            result["next_pick"] - result["current_pick"] - 1,
        )

        roster_counts = {
            roster_id: {
                position: 0 for position in ["QB", "RB", "WR", "TE"]
            }
            for roster_id in roster_to_slot
        }
        drafted_names = set()
        for pick in picks:
            roster_id = pick.get("roster_id")
            metadata = pick.get("metadata") or {}
            position = metadata.get("position")
            if roster_id in roster_counts and position in roster_counts[roster_id]:
                roster_counts[roster_id][position] += 1
            first_name = (metadata.get("first_name") or "").strip()
            last_name = (metadata.get("last_name") or "").strip()
            full_name = " ".join(
                part for part in [first_name, last_name] if part
            ).strip()
            if full_name:
                drafted_names.add(full_name.lower())

        simulated_pool = [
            player
            for player in available_players
            if player[1].lower() not in drafted_names
            and player[2] in ROSTER_TARGETS
        ]

        future_pick_numbers = range(
            result["current_pick"] + 1,
            result["next_pick"],
        )
        teams_seen = set()

        for overall_pick in future_pick_numbers:
            round_number = ((overall_pick - 1) // teams) + 1
            position_in_round = ((overall_pick - 1) % teams) + 1
            if draft.get("type") == "snake" and round_number % 2 == 0:
                draft_slot = teams - position_in_round + 1
            else:
                draft_slot = position_in_round

            roster_id = slot_to_roster.get(draft_slot)
            if roster_id is None or not simulated_pool:
                continue

            team_name = team_by_roster.get(roster_id, f"Roster {roster_id}")
            if roster_id not in teams_seen:
                result["teams_before_next_pick"].append(team_name)
                teams_seen.add(roster_id)

            counts = roster_counts.setdefault(
                roster_id,
                {position: 0 for position in ROSTER_TARGETS},
            )
            need_pressure = {
                position: int(
                    max(0, target - counts.get(position, 0))
                    / target
                    * 100
                ) if target else 0
                for position, target in ROSTER_TARGETS.items()
            }

            for position, pressure in need_pressure.items():
                if pressure >= 60:
                    result["teams_needing_position"][position] += 1

            candidate_window = simulated_pool[:40]
            best_player = max(
                candidate_window,
                key=lambda player: (
                    max(0, 101 - player[0])
                    + need_pressure.get(player[2], 0)
                    + (
                        35
                        if counts.get(player[2], 0) == 0
                        and player[2] in ["QB", "TE"]
                        else 0
                    )
                ),
            )
            simulated_pool.remove(best_player)
            position = best_player[2]
            counts[position] = counts.get(position, 0) + 1
            result["projected_gone"][position] += 1
            result["position_pressure"][position] += need_pressure.get(position, 0)
            result["projected_picks"].append(
                {
                    "overall_pick": overall_pick,
                    "team": team_name,
                    "player": best_player[1],
                    "position": position,
                    "rank": best_player[0],
                }
            )

        result["projected_remaining"] = {
            position: max(
                0,
                scarcity.get(position, 0)
                - result["projected_gone"].get(position, 0),
            )
            for position in ["QB", "RB", "WR", "TE"]
        }

        for position in result["position_pressure"]:
            projected = result["projected_gone"][position]
            needy_teams = result["teams_needing_position"][position]
            result["position_pressure"][position] = (
                projected * 25 + needy_teams * 10
            )

    except Exception as exc:
        result["error"] = str(exc)

    return result


'''
        text = text.replace(marker, helper + marker, 1)

    # Replace the basic forecast call with opponent-aware simulation.
    if "pick_forecast = build_opponent_forecast(" not in text:
        old = "    pick_forecast = build_pick_forecast(available_players, scarcity)\n"
        require(text, old, "the current pick forecast call")
        text = text.replace(
            old,
            "    pick_forecast = build_opponent_forecast(available_players, scarcity)\n",
            1,
        )

    # Add opponent pressure to recommendation explanations.
    if "Opponent demand before the next pick is elevated" not in text:
        marker = "    return render_template(\n        \"draftboard.html\",\n"
        require(text, marker, "draftboard render_template()")
        explanation = '''    if team_recommendation and pick_forecast.get("next_pick"):\n        recommended_position = team_recommendation[2]\n        projected_position_picks = pick_forecast["projected_gone"].get(\n            recommended_position, 0\n        )\n        needy_opponents = pick_forecast["teams_needing_position"].get(\n            recommended_position, 0\n        )\n        if projected_position_picks > 0:\n            recommendation_reasons.append(\n                f"Opponent model projects {projected_position_picks} "\n                f"{recommended_position} selection(s) before your next pick."\n            )\n        if needy_opponents >= 2:\n            recommendation_reasons.append(\n                f"Opponent demand before the next pick is elevated: "\n                f"{needy_opponents} teams still need {recommended_position} depth."\n            )\n\n'''
        text = text.replace(marker, explanation + marker, 1)

    return text


def patch_template(text):
    if "Opponent Pressure Index" not in text:
        anchor = '<section class="card">\n<h2>🔭 Next-Pick Forecast</h2>'
        require(text, anchor, "the Next-Pick Forecast panel")
        panel = '''<section class="card">\n<h2>🤖 Opponent Pressure Index</h2>\n{% if pick_forecast.next_pick %}\n<p><strong>Teams drafting before your next pick:</strong> {{ pick_forecast.teams_before_next_pick|length }}</p>\n{% if pick_forecast.teams_before_next_pick %}<p class="muted">{{ pick_forecast.teams_before_next_pick|join(", ") }}</p>{% endif %}\n<div class="roster-grid">{% for position in ["QB", "RB", "WR", "TE"] %}<div class="slot"><strong>{{ position }}</strong><br>Pressure index: {{ pick_forecast.position_pressure[position] }}<br>Teams needing depth: {{ pick_forecast.teams_needing_position[position] }}<br>Projected picks: {{ pick_forecast.projected_gone[position] }}</div>{% endfor %}</div>\n{% else %}<p class="muted">Opponent pressure will appear when Sleeper exposes the next usable draft turn.</p>{% endif %}\n</section>\n\n'''
        text = text.replace(anchor, panel + anchor, 1)

    if "Projected Opponent Picks" not in text:
        marker = '<p class="muted">Forecast assumes the highest-ranked available players are selected before your next turn.</p>'
        if marker in text:
            replacement = '''{% if pick_forecast.projected_picks %}<h3>Projected Opponent Picks</h3><div class="table-wrap"><table><thead><tr><th>Pick</th><th>Team</th><th>Player</th><th>Position</th><th>Rank</th></tr></thead><tbody>{% for pick in pick_forecast.projected_picks %}<tr><td>{{ pick.overall_pick }}</td><td>{{ pick.team }}</td><td>{{ pick.player }}</td><td>{{ pick.position }}</td><td>{{ pick.rank }}</td></tr>{% endfor %}</tbody></table></div>{% endif %}\n<p class="muted">Forecast simulates opponent selections using roster targets, positional need, and overall rank. It is a planning estimate, not a prediction guarantee.</p>'''
            text = text.replace(marker, replacement, 1)
        else:
            raise RuntimeError(
                "Could not find the forecast note in draftboard.html. "
                "No project files were changed."
            )

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

    shutil.copy2(APP, APP.with_suffix(".py.before-opponent-model"))
    shutil.copy2(
        TEMPLATE,
        TEMPLATE.with_suffix(".html.before-opponent-model"),
    )
    APP.write_text(new_app, encoding="utf-8")
    TEMPLATE.write_text(new_template, encoding="utf-8")

    print("Opponent roster model and pressure forecast installed.")
    print("Backups created with .before-opponent-model suffixes.")


if __name__ == "__main__":
    main()
